"""Fail-closed, approval-bound and rollback-capable target file execution."""
import hashlib
import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from lisa.projects.adaptation import AdaptationPlanStatus
from lisa.projects.execution import ProjectExecutionResult
from lisa.projects.execution_ledger import ProjectExecutionLedger


class ProjectExecutionExecutor:
    """Apply an exact, operator-approved set of files to one registered target.

    CPI-06 deliberately does not run shell commands or tests. It records that
    validation is required and leaves test execution to the target project's
    normal, operator-reviewed workflow.
    """

    MAX_FILES = 100
    MAX_FILE_BYTES = 1024 * 1024
    MAX_TOTAL_BYTES = 5 * 1024 * 1024
    JOURNAL_NAME = "execution.journal.json"

    PROTECTED_PARTS = {
        ".git", ".lisa", ".env", ".ssh", "secrets", "credentials",
        "node_modules", "__pycache__",
    }

    def __init__(self, registry, state_dir=None):
        self._registry = registry
        self._state_dir_input = Path(
            state_dir or (Path.home() / ".lisa" / "executions")
        ).expanduser().absolute()
        self._state_dir = self._state_dir_input.resolve(strict=False)

    def _assert_state_dir_safe(self):
        cursor = self._state_dir_input
        while cursor != cursor.parent:
            if cursor.is_symlink():
                raise ValueError("Execution state path must not contain symlinks.")
            cursor = cursor.parent
        if self._state_dir.exists() and not self._state_dir.is_dir():
            raise ValueError("Execution state path must be a directory.")

    @staticmethod
    def _sha256(content):
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def approval_digest(cls, plan, changes, target_root):
        """Return the digest the operator must explicitly confirm.

        The digest binds the plan identity, source evidence, canonical target,
        exact relative paths, expected pre-change hashes and proposed contents.
        """
        normalized = []
        for change in sorted(changes, key=lambda item: item.relative_path):
            content = change.content.encode("utf-8")
            normalized.append({
                "path": change.relative_path,
                "expected_sha256": change.expected_sha256,
                "content_sha256": cls._sha256(content),
            })
        payload = {
            "plan_id": plan.plan_id,
            "source_project_id": plan.source_project_id,
            "target_project_id": plan.target_project_id,
            "target_root": str(Path(target_root).resolve()),
            "source_evidence": sorted(
                (item.relative_path, getattr(item, "sha256", "")) for item in plan.source_evidence
            ),
            "target_constraints": sorted(
                (item.relative_path, getattr(item, "sha256", "")) for item in plan.target_constraints
            ),
            "changes": normalized,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return cls._sha256(encoded)

    @classmethod
    def _validated_relative_path(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Every change needs a non-empty relative path.")
        if "\\" in value:
            raise ValueError("Use POSIX-style relative paths; backslashes are not accepted.")
        relative = PurePosixPath(value)
        if relative.is_absolute() or not relative.parts:
            raise ValueError("Absolute paths are not allowed.")
        if any(part in ("", ".", "..") for part in relative.parts):
            raise ValueError("Path traversal and ambiguous path components are not allowed.")
        if any(
            part.casefold() in cls.PROTECTED_PARTS
            or part.casefold().startswith(".env.")
            for part in relative.parts
        ):
            raise ValueError(f"Protected path cannot be modified: {value}")
        return relative

    @staticmethod
    def _assert_no_symlink(root, relative):
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f"Symlink paths are not allowed: {relative.as_posix()}")
        resolved = current.resolve(strict=False)
        if resolved != root and root not in resolved.parents:
            raise ValueError(f"Path escapes the registered target: {relative.as_posix()}")
        return current

    @classmethod
    def _verify_plan_evidence(cls, root, evidence_items, label):
        for evidence in evidence_items:
            relative = cls._validated_relative_path(evidence.relative_path)
            path = cls._assert_no_symlink(root, relative)
            if not path.is_file():
                raise ValueError(f"{label} evidence file is missing: {relative.as_posix()}")
            actual = cls._sha256(path.read_bytes())
            if not evidence.sha256 or actual != evidence.sha256:
                raise ValueError(f"{label} evidence changed since planning: {relative.as_posix()}")

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
    def _mkdir_durable(cls, directory, root):
        """Create each backup directory and persist its entry in its parent."""
        directory = Path(directory)
        root = Path(root)
        relative = directory.relative_to(root)
        current = root
        for part in relative.parts:
            child = current / part
            if not child.exists():
                child.mkdir()
                cls._fsync_directory(current)
            elif child.is_symlink() or not child.is_dir():
                raise ValueError(f"Unsafe backup directory: {child}")
            current = child

    @staticmethod
    def _atomic_write(path, content, mode=None):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=str(path.parent), prefix=f".{path.name}.",
                suffix=".lisa-tmp", delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, stat.S_IMODE(mode) if mode is not None else 0o644)
            os.replace(str(temp_path), str(path))
            ProjectExecutionExecutor._fsync_directory(path.parent)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def execute(self, request):
        from lisa.projects.execution import ProjectExecutionRequest

        if not isinstance(request, ProjectExecutionRequest):
            return ProjectExecutionResult(success=False, error="A valid ProjectExecutionRequest is required.")
        plan = request.plan
        if getattr(plan, "status", None) != AdaptationPlanStatus.READY_FOR_REVIEW:
            return ProjectExecutionResult(success=False, error="Only a ready-for-review adaptation plan can be executed.")
        if getattr(plan, "execution_authorized", True) is not False:
            return ProjectExecutionResult(success=False, error="The plan authorization state is invalid.")
        if not getattr(plan, "authorization_required", False):
            return ProjectExecutionResult(success=False, error="The plan does not require explicit operator authorization.")
        if not request.changes:
            return ProjectExecutionResult(success=False, error="At least one explicitly scoped file change is required.")

        source = self._registry.get(plan.source_project_id)
        target = self._registry.get(plan.target_project_id)
        if source is None or target is None:
            return ProjectExecutionResult(success=False, error="Source and target must both remain registered.")
        try:
            self._assert_state_dir_safe()
            self._state_dir.mkdir(parents=True, exist_ok=True)
            self._fsync_directory(self._state_dir.parent)
            source_root = Path(source.root_path).resolve(strict=True)
            target_root = Path(target.root_path).resolve(strict=True)
            if source_root == target_root:
                raise ValueError("Source and target resolve to the same project root.")
            if not target_root.is_dir() or not source_root.is_dir():
                raise ValueError("Source and target project roots must be existing directories.")
            self._verify_plan_evidence(source_root, plan.source_evidence, "Source")
            self._verify_plan_evidence(target_root, plan.target_constraints, "Target")

            digest = self.approval_digest(plan, request.changes, target_root)
            if request.operator_confirmation != f"APPLY {digest}":
                raise ValueError("Explicit approval mismatch. Review the exact patch and confirm with: APPLY <approval-digest>.")
            execution_id = "exec_" + digest[:20]
            execution_dir = self._state_dir / execution_id
            if execution_dir.exists():
                if not (execution_dir / self.JOURNAL_NAME).exists():
                    raise ValueError("An incomplete pre-journal execution directory exists. No target writes occur before the journal is durable; inspect this state directory before retrying.")
                raise ValueError("This approval digest has already been executed or has a recoverable journal; refusing replay.")
            if len(request.changes) > self.MAX_FILES:
                raise ValueError(f"Execution scope exceeds the {self.MAX_FILES}-file limit.")

            scoped = []
            seen = set()
            total_bytes = 0
            for change in request.changes:
                if not isinstance(change.content, str):
                    raise ValueError("File contents must be UTF-8 text.")
                content_bytes = change.content.encode("utf-8")
                if len(content_bytes) > self.MAX_FILE_BYTES:
                    raise ValueError(f"File exceeds the {self.MAX_FILE_BYTES}-byte limit: {change.relative_path}")
                total_bytes += len(content_bytes)
                if total_bytes > self.MAX_TOTAL_BYTES:
                    raise ValueError(f"Execution payload exceeds the {self.MAX_TOTAL_BYTES}-byte limit.")
                relative = self._validated_relative_path(change.relative_path)
                key = relative.as_posix()
                if key in seen:
                    raise ValueError(f"Duplicate file scope: {key}")
                seen.add(key)
                destination = self._assert_no_symlink(target_root, relative)
                if not destination.parent.is_dir():
                    raise ValueError(f"Parent directory must already exist: {relative.parent.as_posix()}")
                if destination.exists():
                    info = destination.lstat()
                    if not stat.S_ISREG(info.st_mode):
                        raise ValueError(f"Only regular files may be replaced: {key}")
                    current = destination.read_bytes()
                    actual_hash = self._sha256(current)
                    if change.expected_sha256 is None or actual_hash != change.expected_sha256:
                        raise ValueError(f"Precondition failed for {key}: expected hash does not match current file.")
                    mode = info.st_mode
                else:
                    if change.expected_sha256 is not None:
                        raise ValueError(f"Precondition failed for {key}: expected existing file is missing.")
                    current = None
                    mode = None
                scoped.append((change, relative, destination, current, mode))

            state_root = self._state_dir.resolve(strict=False)
            if (
                state_root == target_root or target_root in state_root.parents
                or state_root in target_root.parents
            ):
                raise ValueError("Execution backups/audit must be stored outside the target project.")
            if (
                state_root == source_root or source_root in state_root.parents
                or state_root in source_root.parents
            ):
                raise ValueError("Execution backups/audit must be stored outside the source project.")

            execution_dir.mkdir(parents=False, exist_ok=False)
            self._fsync_directory(self._state_dir)
            backup_dir = execution_dir / "backups"
            backup_dir.mkdir(exist_ok=False)
            self._fsync_directory(execution_dir)

            backup_manifest = []
            journal_files = []
            for change, relative, destination, current, mode in scoped:
                if current is not None:
                    backup_path = backup_dir.joinpath(*relative.parts)
                    self._mkdir_durable(backup_path.parent, backup_dir)
                    with backup_path.open("xb") as handle:
                        handle.write(current)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.chmod(backup_path, 0o600)
                    self._fsync_directory(backup_path.parent)
                    backup_rel = backup_path.relative_to(execution_dir).as_posix()
                    before_hash = self._sha256(current)
                    backup_manifest.append({
                        "path": relative.as_posix(),
                        "backup": backup_rel,
                        "sha256": before_hash,
                        "mode": stat.S_IMODE(mode),
                    })
                else:
                    backup_rel = None
                    before_hash = None
                    backup_manifest.append({
                        "path": relative.as_posix(), "backup": None,
                        "sha256": None, "mode": None,
                    })
                journal_files.append({
                    "path": relative.as_posix(),
                    "before_sha256": before_hash,
                    "after_sha256": self._sha256(change.content.encode("utf-8")),
                    "backup": backup_rel,
                    "backup_sha256": before_hash,
                    "mode": stat.S_IMODE(mode) if mode is not None else None,
                    "applied": False,
                })

            audit = {
                "schema_version": 1,
                "execution_id": execution_id,
                "plan_id": plan.plan_id,
                "source_project_id": plan.source_project_id,
                "target_project_id": plan.target_project_id,
                "target_root": str(target_root),
                "approval_digest": digest,
                "approved_confirmation": f"APPLY {digest}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "changed_files": [
                    {
                        "path": item["path"],
                        "before_sha256": item["before_sha256"],
                        "after_sha256": item["after_sha256"],
                    }
                    for item in journal_files
                ],
                "backups": backup_manifest,
                "lifecycle": {"status": "applying"},
                "validation": {
                    "status": "required_not_run",
                    "note": "CPI-06 does not execute project commands. Run the target project's approved regression suite before accepting this adaptation.",
                },
            }
            journal = {
                "schema_version": 1,
                "execution_id": execution_id,
                "approval_digest": digest,
                "source_project_id": plan.source_project_id,
                "target_project_id": plan.target_project_id,
                "target_root": str(target_root),
                "plan_id": plan.plan_id,
                "created_at": audit["created_at"],
                "status": "applying",
                "files": journal_files,
                "recovered_files": [],
            }
            journal_path = execution_dir / self.JOURNAL_NAME
            audit_path = execution_dir / "audit.json"
            journal_bytes = (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode("utf-8")
            self._atomic_write(journal_path, journal_bytes)
            self._atomic_write(
                audit_path,
                (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            )

            applied = []
            ledger_attempted = False
            ledger_recorded = False
            try:
                for index, (change, relative, destination, current, mode) in enumerate(scoped):
                    self._assert_no_symlink(target_root, relative)
                    if destination.exists() and not destination.is_file():
                        raise ValueError(f"Target path is no longer a regular file: {relative.as_posix()}")
                    latest = destination.read_bytes() if destination.is_file() else None
                    latest_hash = self._sha256(latest) if latest is not None else None
                    before_hash = journal_files[index]["before_sha256"]
                    if latest_hash != before_hash:
                        raise ValueError(
                            f"Target changed during execution; refusing write: {relative.as_posix()}"
                        )
                    # Register the candidate before replace: if the replace succeeds
                    # but a subsequent fsync raises, the in-process rollback still sees it.
                    applied.append((relative, destination, current, mode, journal_files[index]["after_sha256"]))
                    self._atomic_write(destination, change.content.encode("utf-8"), mode=mode)
                    journal_files[index]["applied"] = True
                    journal_files[index]["applied_at"] = datetime.now(timezone.utc).isoformat()
                    journal["files"] = journal_files
                    self._atomic_write(
                        journal_path,
                        (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                    )

                audit["lifecycle"] = {"status": "applied"}
                self._atomic_write(
                    audit_path,
                    (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                )
                journal["status"] = "finalizing"
                journal["files"] = journal_files
                journal["finalizing_at"] = datetime.now(timezone.utc).isoformat()
                self._atomic_write(
                    journal_path,
                    (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                )
                audit_bytes = audit_path.read_bytes()
                ledger_attempted = True
                ProjectExecutionLedger(self._state_dir).append(
                    "execution_applied", execution_id,
                    {
                        "approval_digest": digest,
                        "audit_sha256": self._sha256(audit_bytes),
                        "target_project_id": plan.target_project_id,
                    },
                )
                ledger_recorded = True
                journal["status"] = "completed"
                journal["completed_at"] = datetime.now(timezone.utc).isoformat()
                self._atomic_write(
                    journal_path,
                    (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                )
            except Exception as execution_error:
                if ledger_recorded:
                    return ProjectExecutionResult(
                        success=True,
                        execution_id=execution_id,
                        changed_files=tuple(relative.as_posix() for _, relative, _, _, _ in scoped),
                        backup_directory=str(backup_dir),
                        audit_path=str(audit_path),
                        validation_required=True,
                        warning=(
                            "Target files and authenticated execution event are committed, "
                            "but the journal finalization write failed. The journal remains "
                            "in finalizing state: " + str(execution_error)
                        ),
                    )
                rollback_errors = []
                for relative, destination, current, mode, after_hash in reversed(applied):
                    try:
                        self._assert_no_symlink(target_root, relative)
                        if destination.exists() and not destination.is_file():
                            raise ValueError(f"Target path is no longer a regular file: {relative.as_posix()}")
                        latest = destination.read_bytes() if destination.is_file() else None
                        latest_hash = self._sha256(latest) if latest is not None else None
                        before_hash = self._sha256(current) if current is not None else None
                        if latest_hash == before_hash:
                            continue
                        if latest_hash != after_hash:
                            raise ValueError(
                                f"Target changed during automatic rollback; refusing overwrite: {relative.as_posix()}"
                            )
                        if current is None:
                            destination.unlink()
                            self._fsync_directory(destination.parent)
                        else:
                            self._atomic_write(destination, current, mode=mode)
                    except Exception as rollback_error:
                        rollback_errors.append(str(rollback_error))
                if rollback_errors:
                    journal["status"] = "recovery_required"
                    journal["rollback_errors"] = rollback_errors
                    try:
                        self._atomic_write(
                            journal_path,
                            (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                        )
                    except Exception:
                        pass
                    raise RuntimeError(
                        "Execution failed and automatic rollback was incomplete; "
                        "use 'lisa project recover' after inspecting the journal: "
                        + "; ".join(rollback_errors)
                    )
                if ledger_attempted:
                    journal["status"] = "recovery_required"
                    journal["rollback_errors"] = [
                        "Ledger append was attempted but did not complete cleanly; "
                        "verify/recover the ledger before finalizing this execution."
                    ]
                    self._atomic_write(
                        journal_path,
                        (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                    )
                elif execution_dir.exists():
                    import shutil
                    shutil.rmtree(execution_dir)
                    self._fsync_directory(self._state_dir)
                raise

            return ProjectExecutionResult(
                success=True,
                execution_id=execution_id,
                changed_files=tuple(relative.as_posix() for _, relative, _, _, _ in scoped),
                backup_directory=str(backup_dir),
                audit_path=str(audit_path),
                validation_required=True,
            )
        except Exception as exc:
            return ProjectExecutionResult(success=False, error=str(exc))
