"""Recovery and operator-reported validation for governed executions."""
import errno
import hashlib
import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from lisa.projects.execution_executor import ProjectExecutionExecutor


class ProjectExecutionLifecycle:
    """Rollback and record validation without executing target project code."""

    MAX_EVIDENCE_BYTES = 10 * 1024 * 1024

    def __init__(self, registry, state_dir=None):
        self._registry = registry
        self._state_dir = Path(state_dir or (Path.home() / ".lisa" / "executions")).expanduser().resolve(strict=False)

    @staticmethod
    def _sha256(content):
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _atomic_write(path, content):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=str(path.parent), prefix=f".{path.name}.", suffix=".lisa-tmp", delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(str(temp_path), str(path))
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def _load_execution(self, execution_id):
        if not isinstance(execution_id, str) or not execution_id.startswith("exec_") or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in execution_id):
            raise ValueError("A valid execution ID is required.")
        execution_dir = self._state_dir / execution_id
        if execution_dir.is_symlink() or not execution_dir.is_dir():
            raise ValueError("Execution record was not found or is unsafe.")
        audit_path = execution_dir / "audit.json"
        if audit_path.is_symlink() or not audit_path.is_file():
            raise ValueError("Execution audit record is missing or unsafe.")
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if audit.get("schema_version") != 1 or audit.get("execution_id") != execution_id:
            raise ValueError("Execution audit identity or schema is invalid.")
        return execution_dir, audit_path, audit

    def _registered_target_root(self, audit):
        target = self._registry.get(audit.get("target_project_id"))
        if target is None:
            raise ValueError("The target project is no longer registered; recovery is refused.")
        root = Path(target.root_path).resolve(strict=True)
        recorded = Path(audit.get("target_root", "")).resolve(strict=True)
        if not root.is_dir() or root != recorded:
            raise ValueError("The registered target root no longer matches the execution audit.")
        return root

    @staticmethod
    def _current_regular_file_hash(path, relative):
        """Return None only for a genuinely absent path; reject non-regular objects."""
        try:
            path_info = path.lstat()
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(path_info.st_mode):
            raise ValueError(
                f"Rollback path is a symlink or non-regular object: {relative.as_posix()}"
            )

        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        try:
            descriptor = os.open(str(path), flags)
        except FileNotFoundError:
            return None
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.EISDIR):
                raise ValueError(
                    f"Rollback path is a symlink or non-regular object: {relative.as_posix()}"
                ) from exc
            raise
        with os.fdopen(descriptor, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(
                    f"Rollback path is not a regular file: {relative.as_posix()}"
                )
            return hashlib.sha256(handle.read()).hexdigest()

    @staticmethod
    def _rollback_digest(execution_id, audit):
        payload = {key: audit.get(key) for key in ("approval_digest", "target_root", "changed_files", "backups")}
        payload["execution_id"] = execution_id
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _validation_digest(execution_id, audit, status, command, summary, evidence):
        payload = {
            "execution_id": execution_id, "approval_digest": audit.get("approval_digest"),
            "target_project_id": audit.get("target_project_id"), "status": status,
            "command": command, "summary": summary, "evidence": evidence,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def preview_rollback_digest(self, execution_id):
        _, _, audit = self._load_execution(execution_id)
        return self._rollback_digest(execution_id, audit)

    def _validation_evidence(self, target_root, evidence_path):
        if evidence_path is None:
            return None
        relative = ProjectExecutionExecutor._validated_relative_path(evidence_path)
        path = ProjectExecutionExecutor._assert_no_symlink(target_root, relative)
        if not path.is_file():
            raise ValueError("Validation evidence file must exist inside the target project.")
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > self.MAX_EVIDENCE_BYTES:
            raise ValueError("Validation evidence must be a regular file no larger than 10 MiB.")
        return {"path": relative.as_posix(), "sha256": self._sha256(path.read_bytes()), "bytes": info.st_size}

    def preview_validation_digest(self, execution_id, status, command, summary, evidence_path=None):
        _, _, audit = self._load_execution(execution_id)
        root = self._registered_target_root(audit)
        evidence = self._validation_evidence(root, evidence_path)
        return self._validation_digest(execution_id, audit, status, command.strip(), summary.strip(), evidence)

    def rollback(self, execution_id, operator_confirmation):
        try:
            execution_dir, audit_path, audit = self._load_execution(execution_id)
            root = self._registered_target_root(audit)
            state = audit.get("lifecycle", {}).get("status", "applied")
            if state not in ("applied", "rollback_in_progress"):
                raise ValueError(f"Execution cannot be rolled back from lifecycle state: {state}")
            digest = self._rollback_digest(execution_id, audit)
            if operator_confirmation != f"ROLLBACK {digest}":
                raise ValueError(f"Explicit rollback approval mismatch. Confirm with: ROLLBACK {digest}")

            changed = audit.get("changed_files", [])
            backups = {item["path"]: item for item in audit.get("backups", [])}
            if (
                not changed
                or len(backups) != len(audit.get("backups", []))
                or len({item.get("path") for item in changed}) != len(changed)
                or set(backups) != {item.get("path") for item in changed}
            ):
                raise ValueError("Audit changed-file and backup manifests do not match.")
            scoped = []
            for item in changed:
                relative = ProjectExecutionExecutor._validated_relative_path(item.get("path"))
                destination = ProjectExecutionExecutor._assert_no_symlink(root, relative)
                backup = backups[relative.as_posix()]
                before_hash, after_hash = item.get("before_sha256"), item.get("after_sha256")
                if not after_hash:
                    raise ValueError(f"Audit is missing the post-change hash: {relative.as_posix()}")
                current_hash = self._current_regular_file_hash(destination, relative)
                if current_hash not in (after_hash, before_hash):
                    raise ValueError(f"Target file changed since execution; refusing rollback: {relative.as_posix()}")
                backup_bytes, backup_mode = None, None
                if before_hash is not None:
                    backup_rel = Path(backup.get("backup", ""))
                    if backup_rel.is_absolute() or ".." in backup_rel.parts or not backup_rel.parts:
                        raise ValueError("Backup manifest contains an unsafe path.")
                    backup_path = execution_dir / backup_rel
                    current_backup_path = execution_dir
                    for part in backup_rel.parts:
                        current_backup_path = current_backup_path / part
                        if current_backup_path.is_symlink():
                            raise ValueError("Backup path contains a symlink.")
                    if execution_dir.resolve() not in backup_path.resolve().parents or backup_path.is_symlink() or not backup_path.is_file():
                        raise ValueError(f"Backup is missing or unsafe: {relative.as_posix()}")
                    backup_bytes = backup_path.read_bytes()
                    backup_mode = backup.get("mode")
                    if self._sha256(backup_bytes) != before_hash or backup.get("sha256") != before_hash:
                        raise ValueError(f"Backup integrity check failed: {relative.as_posix()}")
                elif backup.get("backup") is not None:
                    raise ValueError(f"Unexpected backup for newly created file: {relative.as_posix()}")
                scoped.append((relative, destination, current_hash, before_hash, after_hash, backup_bytes, backup_mode))

            audit.setdefault("lifecycle", {})["status"] = "rollback_in_progress"
            audit["lifecycle"]["rollback_started_at"] = datetime.now(timezone.utc).isoformat()
            audit["lifecycle"]["rollback_digest"] = digest
            self._atomic_write(audit_path, (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode())

            restored = []
            for relative, destination, current_hash, before_hash, after_hash, backup_bytes, backup_mode in reversed(scoped):
                ProjectExecutionExecutor._assert_no_symlink(root, relative)
                latest_hash = self._current_regular_file_hash(destination, relative)
                if latest_hash not in (after_hash, before_hash):
                    raise ValueError(f"Target file changed during rollback; refusing write: {relative.as_posix()}")
                if latest_hash == before_hash:
                    if backup_mode is None or not isinstance(backup_mode, int) or backup_mode < 0 or backup_mode > 0o7777:
                        raise ValueError(f"Backup permission mode is invalid: {relative.as_posix()}")
                    os.chmod(destination, backup_mode)
                    if stat.S_IMODE(destination.stat().st_mode) != backup_mode:
                        raise ValueError(f"Original permission mode could not be restored: {relative.as_posix()}")
                    restored.append(relative.as_posix())
                    continue
                if before_hash is None:
                    if destination.exists():
                        destination.unlink()
                else:
                    ProjectExecutionExecutor._atomic_write(destination, backup_bytes, mode=backup_mode)
                restored.append(relative.as_posix())

            audit["lifecycle"]["status"] = "rolled_back"
            audit["lifecycle"]["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
            audit["lifecycle"]["restored_files"] = list(restored)
            self._atomic_write(audit_path, (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode())
            return {"success": True, "execution_id": execution_id, "restored_files": tuple(restored)}
        except Exception as exc:
            return {"success": False, "execution_id": execution_id, "error": str(exc)}

    def record_validation(self, execution_id, status, command, summary, operator_confirmation, evidence_path=None):
        try:
            execution_dir, audit_path, audit = self._load_execution(execution_id)
            root = self._registered_target_root(audit)
            if audit.get("lifecycle", {}).get("status", "applied") != "applied":
                raise ValueError("Validation can only be recorded for an applied, not rolled-back, execution.")
            if status not in ("passed", "failed"):
                raise ValueError("Validation status must be 'passed' or 'failed'.")
            if not isinstance(command, str) or not command.strip() or len(command) > 2000:
                raise ValueError("A concise test command/description (1–2000 characters) is required.")
            if not isinstance(summary, str) or not summary.strip() or len(summary) > 5000:
                raise ValueError("A concise test summary (1–5000 characters) is required.")
            if audit.get("validation", {}).get("status") in ("operator_reported_passed", "operator_reported_failed"):
                raise ValueError("Validation evidence has already been recorded for this execution.")

            for item in audit.get("changed_files", []):
                relative = ProjectExecutionExecutor._validated_relative_path(item["path"])
                path = ProjectExecutionExecutor._assert_no_symlink(root, relative)
                actual = self._sha256(path.read_bytes()) if path.is_file() else None
                if actual != item.get("after_sha256"):
                    raise ValueError(f"Executed target file changed before validation capture: {relative.as_posix()}")

            evidence = self._validation_evidence(root, evidence_path)
            digest = self._validation_digest(execution_id, audit, status, command.strip(), summary.strip(), evidence)
            if operator_confirmation != f"RECORD {digest}":
                raise ValueError(f"Explicit validation-record approval mismatch. Confirm with: RECORD {digest}")

            record = {
                "schema_version": 1, "execution_id": execution_id,
                "target_project_id": audit["target_project_id"], "target_root": str(root),
                "status": "operator_reported_passed" if status == "passed" else "operator_reported_failed",
                "command": command.strip(), "summary": summary.strip(), "evidence": evidence,
                "evidence_digest": digest, "recorded_at": datetime.now(timezone.utc).isoformat(),
                "verification_method": "operator_attestation; L.I.S.A. did not execute the command or independently verify the result",
            }
            validation_path = execution_dir / "validation.json"
            if validation_path.is_symlink():
                raise ValueError("Validation record path is unsafe.")
            if validation_path.exists():
                existing = json.loads(validation_path.read_text(encoding="utf-8"))
                if existing.get("evidence_digest") != digest:
                    raise ValueError("A different validation record already exists; refusing overwrite.")
                record = existing
            else:
                self._atomic_write(validation_path, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
            audit["validation"] = {
                "status": record["status"], "record_path": "validation.json",
                "evidence_digest": digest, "recorded_at": record["recorded_at"],
            }
            self._atomic_write(audit_path, (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode())
            return {"success": True, "execution_id": execution_id, "validation_path": str(validation_path), "status": record["status"]}
        except Exception as exc:
            return {"success": False, "execution_id": execution_id, "error": str(exc)}
