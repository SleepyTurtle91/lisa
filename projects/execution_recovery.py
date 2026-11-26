"""Explicit recovery for interrupted, journaled CPI executions.

Recovery always rolls an incomplete apply back to its exact pre-execution state.
It never completes an interrupted apply or overwrites an unknown later version.
"""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from lisa.projects.execution_executor import ProjectExecutionExecutor
from lisa.projects.execution_ledger import ProjectExecutionLedger


class ProjectExecutionRecovery:
    JOURNAL_NAME = "execution.journal.json"
    LOCK_NAME = ".recovery.lock"
    SHA256_LENGTH = 64

    def __init__(self, registry, state_dir=None):
        self._registry = registry
        self._state_dir_input = Path(
            state_dir or (Path.home() / ".lisa" / "executions")
        ).expanduser().absolute()
        self._state_dir = self._state_dir_input.resolve(strict=False)

    @staticmethod
    def _canonical(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def _digest(cls, value):
        return hashlib.sha256(value).hexdigest()

    @classmethod
    def _journal_digest(cls, journal):
        return cls._digest(cls._canonical(journal))

    @staticmethod
    def _fsync_directory(directory):
        if os.name != "posix":
            return
        descriptor = os.open(str(directory), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @classmethod
    def _atomic_write(cls, path, content):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=str(path.parent), prefix=f".{path.name}.",
                suffix=".lisa-tmp", delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(str(temporary), str(path))
            cls._fsync_directory(path.parent)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def _assert_state_safe(self):
        cursor = self._state_dir_input
        while cursor != cursor.parent:
            if cursor.is_symlink():
                raise ValueError("Execution state path must not contain symlinks.")
            cursor = cursor.parent
        if self._state_dir.exists() and (self._state_dir.is_symlink() or not self._state_dir.is_dir()):
            raise ValueError("Execution state directory is unsafe.")

    def _execution_dir(self, execution_id):
        if not isinstance(execution_id, str) or not execution_id.startswith("exec_"):
            raise ValueError("A valid execution ID is required.")
        if any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in execution_id):
            raise ValueError("Execution ID contains invalid characters.")
        directory = self._state_dir / execution_id
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Execution journal was not found or is unsafe.")
        return directory

    def _load_journal(self, execution_id):
        directory = self._execution_dir(execution_id)
        path = directory / self.JOURNAL_NAME
        if path.is_symlink() or not path.is_file():
            raise ValueError("Execution journal is missing or unsafe.")
        journal = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(journal, dict) or journal.get("schema_version") != 1:
            raise ValueError("Execution journal schema is invalid.")
        if journal.get("execution_id") != execution_id:
            raise ValueError("Execution journal identity does not match its directory.")
        if journal.get("status") not in ("applying", "recovery_required", "recovery_in_progress", "finalizing"):
            raise ValueError("Execution does not have an interrupted apply requiring recovery.")
        approval = journal.get("approval_digest")
        if not isinstance(approval, str) or len(approval) != self.SHA256_LENGTH:
            raise ValueError("Execution journal approval digest is malformed.")
        if execution_id != "exec_" + approval[:20]:
            raise ValueError("Execution journal ID does not match its approval digest.")
        files = journal.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("Execution journal file manifest is missing.")
        return directory, path, journal

    def list_pending(self):
        """Return incomplete execution journals without modifying them."""
        self._assert_state_safe()
        if not self._state_dir.exists():
            return []
        pending = []
        for directory in self._state_dir.iterdir():
            if directory.is_symlink() or not directory.is_dir() or not directory.name.startswith("exec_"):
                continue
            journal_path = directory / self.JOURNAL_NAME
            if journal_path.is_symlink() or not journal_path.is_file():
                continue
            try:
                journal = json.loads(journal_path.read_text(encoding="utf-8"))
                if isinstance(journal, dict) and journal.get("status") in (
                    "applying", "recovery_required", "recovery_in_progress", "finalizing"
                ):
                    pending.append({
                        "execution_id": directory.name,
                        "status": journal["status"],
                        "created_at": journal.get("created_at"),
                        "file_count": len(journal.get("files", [])) if isinstance(journal.get("files"), list) else 0,
                    })
            except Exception:
                pending.append({
                    "execution_id": directory.name,
                    "status": "journal_invalid",
                    "created_at": None,
                    "file_count": 0,
                })
        pending.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return pending

    def preview_digest(self, execution_id):
        """Return a confirmation digest after validating the recovery manifest."""
        self._assert_state_safe()
        directory, _, journal = self._load_journal(execution_id)
        self._validate_manifest(directory, journal)
        return self._journal_digest(journal)

    def _validate_manifest(self, directory, journal):
        target = self._registry.get(journal.get("target_project_id"))
        if target is None:
            raise ValueError("The target project is no longer registered; recovery is refused.")
        target_root = Path(target.root_path).resolve(strict=True)
        recorded_root = Path(journal.get("target_root", "")).resolve(strict=True)
        if not target_root.is_dir() or target_root != recorded_root:
            raise ValueError("Registered target root no longer matches the execution journal.")

        seen = set()
        for item in journal["files"]:
            if not isinstance(item, dict):
                raise ValueError("Execution journal contains an invalid file entry.")
            relative = ProjectExecutionExecutor._validated_relative_path(item.get("path"))
            key = relative.as_posix()
            if key in seen:
                raise ValueError("Execution journal contains duplicate file paths.")
            seen.add(key)
            before_hash = item.get("before_sha256")
            after_hash = item.get("after_sha256")
            if before_hash is not None and (
                not isinstance(before_hash, str) or len(before_hash) != self.SHA256_LENGTH
            ):
                raise ValueError(f"Invalid pre-execution hash for {key}.")
            if not isinstance(after_hash, str) or len(after_hash) != self.SHA256_LENGTH:
                raise ValueError(f"Invalid post-execution hash for {key}.")
            destination = ProjectExecutionExecutor._assert_no_symlink(target_root, relative)
            if destination.exists() and not destination.is_file():
                raise ValueError(f"Target path is not a regular file: {key}")
            if not destination.parent.is_dir():
                raise ValueError(f"Target parent directory is missing: {relative.parent.as_posix()}")
            backup_rel = item.get("backup")
            if before_hash is None:
                if backup_rel is not None or item.get("backup_sha256") is not None:
                    raise ValueError(f"Unexpected backup for newly created file: {key}")
            else:
                backup = Path(backup_rel or "")
                if backup.is_absolute() or not backup.parts or ".." in backup.parts:
                    raise ValueError(f"Unsafe backup path for {key}.")
                backup_path = directory / backup
                cursor = directory
                for part in backup.parts:
                    cursor = cursor / part
                    if cursor.is_symlink():
                        raise ValueError(f"Backup path contains a symlink: {key}")
                if directory.resolve() not in backup_path.resolve().parents or not backup_path.is_file():
                    raise ValueError(f"Backup is missing or unsafe: {key}")
                backup_bytes = backup_path.read_bytes()
                if self._digest(backup_bytes) != before_hash or item.get("backup_sha256") != before_hash:
                    raise ValueError(f"Backup integrity check failed: {key}")
        return target_root

    def _remove_stale_lock_if_dead(self, lock):
        if lock.is_symlink():
            raise ValueError("Recovery lock path is unsafe.")
        try:
            info = lock.lstat()
        except FileNotFoundError:
            return
        if not lock.is_file():
            raise ValueError("Recovery lock is not a regular file; inspect it manually.")
        try:
            pid = int(lock.read_text(encoding="ascii").strip())
        except (OSError, ValueError) as exc:
            raise ValueError("Recovery lock owner is unreadable; inspect it manually.") from exc
        if pid <= 0:
            raise ValueError("Recovery lock owner PID is invalid; inspect it manually.")
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            current = lock.lstat()
            if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
                raise ValueError("Recovery lock changed during stale-lock inspection; retry.")
            lock.unlink()
            self._fsync_directory(lock.parent)
        except (PermissionError, OSError) as exc:
            raise ValueError("Cannot confirm whether recovery lock owner is alive; refusing removal.") from exc
        else:
            raise ValueError(f"Execution recovery is active in process {pid}; refusing concurrent recovery.")

    def _acquire_lock(self, directory):
        lock = directory / self.LOCK_NAME
        if lock.is_symlink():
            raise ValueError("Recovery lock path is unsafe.")
        try:
            descriptor = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            self._remove_stale_lock_if_dead(lock)
            try:
                descriptor = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError as exc:
                raise ValueError("Execution recovery is already running; refusing concurrent recovery.") from exc
        try:
            data = str(os.getpid()).encode("ascii")
            os.write(descriptor, data)
            os.fsync(descriptor)
            self._fsync_directory(directory)
        except Exception:
            os.close(descriptor)
            lock.unlink(missing_ok=True)
            raise
        return descriptor, lock

    def _release_lock(self, descriptor, lock):
        try:
            opened = os.fstat(descriptor)
            current = lock.lstat()
            if (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino):
                lock.unlink()
                self._fsync_directory(lock.parent)
        except FileNotFoundError:
            pass
        finally:
            os.close(descriptor)

    @staticmethod
    def _rollback_digest(execution_id, audit):
        payload = {
            key: audit.get(key)
            for key in ("approval_digest", "target_root", "changed_files", "backups")
        }
        payload["execution_id"] = execution_id
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def recover(self, execution_id, operator_confirmation):
        """Rollback an interrupted apply after exact, manifest-bound approval."""
        self._assert_state_safe()
        directory, journal_path, journal = self._load_journal(execution_id)
        descriptor, lock = self._acquire_lock(directory)
        try:
            # Reload after acquiring the per-execution lock; the preview may be stale.
            directory, journal_path, journal = self._load_journal(execution_id)
            digest = self._journal_digest(journal)
            if operator_confirmation != f"RECOVER {digest}":
                raise ValueError(f"Explicit recovery approval mismatch. Confirm with: RECOVER {digest}")
            target_root = self._validate_manifest(directory, journal)

            # Preflight every target before the first write. Unknown later versions
            # block the entire recovery rather than allowing a partial blind rollback.
            scoped = []
            for item in journal["files"]:
                relative = ProjectExecutionExecutor._validated_relative_path(item["path"])
                destination = ProjectExecutionExecutor._assert_no_symlink(target_root, relative)
                current = destination.read_bytes() if destination.is_file() else None
                current_hash = self._digest(current) if current is not None else None
                before_hash = item["before_sha256"]
                after_hash = item["after_sha256"]
                if current_hash not in (before_hash, after_hash):
                    raise ValueError(
                        f"Target has an unknown version; refusing recovery: {relative.as_posix()}"
                    )
                backup_bytes = None
                if before_hash is not None:
                    backup_bytes = (directory / item["backup"]).read_bytes()
                scoped.append((relative, destination, current_hash, before_hash, after_hash, backup_bytes, item.get("mode")))

            journal["status"] = "recovery_in_progress"
            journal["recovery_digest"] = digest
            journal["recovery_started_at"] = datetime.now(timezone.utc).isoformat()
            self._atomic_write(
                journal_path, (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode("utf-8")
            )

            restored = []
            for relative, destination, _, before_hash, after_hash, backup_bytes, mode in reversed(scoped):
                ProjectExecutionExecutor._assert_no_symlink(target_root, relative)
                current = destination.read_bytes() if destination.is_file() else None
                current_hash = self._digest(current) if current is not None else None
                if current_hash == before_hash:
                    restored.append(relative.as_posix())
                elif current_hash == after_hash:
                    if before_hash is None:
                        destination.unlink()
                        self._fsync_directory(destination.parent)
                    else:
                        ProjectExecutionExecutor._atomic_write(destination, backup_bytes, mode=mode)
                    restored.append(relative.as_posix())
                else:
                    raise ValueError(
                        f"Target changed during recovery; refusing overwrite: {relative.as_posix()}"
                    )
                journal["recovered_files"] = sorted(set(journal.get("recovered_files", [])) | {relative.as_posix()})
                self._atomic_write(
                    journal_path, (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode("utf-8")
                )

            audit_path = directory / "audit.json"
            if audit_path.is_symlink():
                raise ValueError("Execution audit path is unsafe.")
            if audit_path.exists():
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                if not isinstance(audit, dict) or audit.get("execution_id") != execution_id:
                    raise ValueError("Existing execution audit is malformed or has the wrong identity.")
            else:
                audit = {
                    "schema_version": 1,
                    "execution_id": execution_id,
                    "plan_id": journal.get("plan_id"),
                    "source_project_id": journal.get("source_project_id"),
                    "target_project_id": journal.get("target_project_id"),
                    "target_root": journal.get("target_root"),
                    "approval_digest": journal["approval_digest"],
                    "approved_confirmation": f"APPLY {journal['approval_digest']}",
                    "created_at": journal.get("created_at"),
                    "changed_files": [
                        {
                            "path": item["path"],
                            "before_sha256": item["before_sha256"],
                            "after_sha256": item["after_sha256"],
                        }
                        for item in journal["files"]
                    ],
                    "backups": [
                        {
                            "path": item["path"],
                            "backup": item["backup"],
                            "sha256": item["backup_sha256"],
                            "mode": item.get("mode"),
                        }
                        for item in journal["files"]
                    ],
                    "validation": {"status": "required_not_run"},
                }
            audit["lifecycle"] = {
                "status": "rolled_back",
                "rollback_digest": self._rollback_digest(execution_id, audit),
                "rolled_back_at": datetime.now(timezone.utc).isoformat(),
                "restored_files": sorted(item["path"] for item in journal["files"]),
                "recovery_digest": digest,
            }
            self._atomic_write(
                audit_path, (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode("utf-8")
            )

            ledger_warning = None
            try:
                ProjectExecutionLedger(self._state_dir).append(
                    "execution_recovered", execution_id,
                    {
                        "audit_sha256": self._digest(audit_path.read_bytes()),
                        "rollback_digest": audit["lifecycle"]["rollback_digest"],
                        "recovery_digest": digest,
                    },
                )
            except Exception as exc:
                ledger_warning = str(exc)

            journal["status"] = "recovered_rolled_back"
            journal["recovered_at"] = datetime.now(timezone.utc).isoformat()
            journal["ledger_warning"] = ledger_warning
            self._atomic_write(
                journal_path, (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode("utf-8")
            )
            return {
                "success": True,
                "execution_id": execution_id,
                "restored_files": tuple(sorted(item["path"] for item in journal["files"])),
                "ledger_warning": ledger_warning,
            }
        except Exception as exc:
            return {"success": False, "execution_id": execution_id, "error": str(exc)}
        finally:
            self._release_lock(descriptor, lock)
