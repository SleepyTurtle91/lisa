"""Fail-closed, approval-bound and rollback-capable target file execution."""
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from lisa.projects.adaptation import AdaptationPlanStatus
from lisa.projects.execution import ProjectExecutionResult


class ProjectExecutionExecutor:
    """Apply an exact, operator-approved set of files to one registered target.

    CPI-06 deliberately does not run shell commands or tests. It records that
    validation is required and leaves test execution to the target project's
    normal, operator-reviewed workflow.
    """

    MAX_FILES = 100
    MAX_FILE_BYTES = 1024 * 1024
    MAX_TOTAL_BYTES = 5 * 1024 * 1024

    PROTECTED_PARTS = {
        ".git", ".lisa", ".env", ".ssh", "secrets", "credentials",
        "node_modules", "__pycache__",
    }

    def __init__(self, registry, state_dir=None):
        self._registry = registry
        self._state_dir = Path(state_dir or (Path.home() / ".lisa" / "executions")).expanduser().resolve(strict=False)

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
    def _ensure_private_directory(path, exist_ok=True):
        """Create a private state directory without changing shared directories."""
        path = Path(path)
        existed = path.exists() or path.is_symlink()
        if path.is_symlink():
            raise ValueError("Execution state directory must not be a symlink.")
        path.mkdir(parents=True, exist_ok=exist_ok, mode=0o700)
        if path.is_symlink() or not path.is_dir():
            raise ValueError("Execution state path must be a real directory.")
        if os.name == "posix":
            if existed:
                info = path.stat()
                mode = stat.S_IMODE(info.st_mode)
                if info.st_uid != os.geteuid():
                    raise ValueError(
                        "Existing execution state directory is not owned by the current user."
                    )
                if mode & 0o077 or mode & 0o700 != 0o700:
                    raise ValueError(
                        "Existing execution state directory is not private; "
                        "restrict its permissions to owner-only (0700) before retrying."
                    )
            else:
                os.chmod(path, 0o700)
        return path

    @staticmethod
    def _mount_identity(path):
        """Map a Linux path to its device and path within the mounted filesystem."""
        mountinfo = Path("/proc/self/mountinfo")
        if not mountinfo.is_file():
            return None
        resolved = os.path.realpath(str(path))
        best = None
        try:
            lines = mountinfo.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None

        def unescape(value):
            return re.sub(
                r"\\([0-7]{3})",
                lambda match: chr(int(match.group(1), 8)),
                value,
            )

        for line in lines:
            fields = line.split()
            if len(fields) < 6:
                continue
            device = fields[2]
            mount_root = unescape(fields[3])
            mount_point = unescape(fields[4])
            try:
                if os.path.commonpath((resolved, mount_point)) != mount_point:
                    continue
            except ValueError:
                continue
            relative = os.path.relpath(resolved, mount_point)
            filesystem_path = os.path.normpath(os.path.join(mount_root, relative))
            candidate = (len(mount_point), device, PurePosixPath(filesystem_path))
            if best is None or candidate[0] > best[0]:
                best = candidate
        if best is None:
            return None
        return best[1], best[2]

    @classmethod
    def _filesystem_roots_overlap(cls, source_root, target_root):
        """Detect identical, nested, and Linux bind-mounted aliases of project roots."""
        try:
            if os.path.samefile(source_root, target_root):
                return True
        except OSError:
            pass
        source_identity = cls._mount_identity(source_root)
        target_identity = cls._mount_identity(target_root)
        if source_identity is None or target_identity is None:
            if sys.platform.startswith("linux"):
                raise ValueError(
                    "Unable to verify Linux mount identities; refusing filesystem alias checks."
                )
            return False
        source_device, source_path = source_identity
        target_device, target_path = target_identity
        if source_device != target_device:
            return False
        return (
            source_path == target_path
            or source_path in target_path.parents
            or target_path in source_path.parents
        )

    @staticmethod
    def _write_private_file(path, content):
        """Create a new owner-readable/writable backup without a permissive window."""
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
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
            source_root = Path(source.root_path).resolve(strict=True)
            target_root = Path(target.root_path).resolve(strict=True)
            if (
                source_root == target_root
                or source_root in target_root.parents
                or target_root in source_root.parents
                or self._filesystem_roots_overlap(source_root, target_root)
            ):
                raise ValueError("Source and target project roots must not overlap or alias the same filesystem tree.")
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
                raise ValueError("This approval digest has already been executed; refusing replay.")
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
                or self._filesystem_roots_overlap(state_root, source_root)
            ):
                raise ValueError("Execution backups/audit must be stored outside the source project.")
            if self._filesystem_roots_overlap(state_root, target_root):
                raise ValueError("Execution backups/audit must not alias the target project.")

            self._ensure_private_directory(self._state_dir)
            self._ensure_private_directory(execution_dir, exist_ok=False)
            backup_dir = execution_dir / "backups"
            applied = []
            try:
                self._ensure_private_directory(backup_dir, exist_ok=False)
                backup_manifest = []
                for change, relative, destination, current, mode in scoped:
                    if current is not None:
                        backup_path = backup_dir.joinpath(*relative.parts)
                        backup_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                        self._write_private_file(backup_path, current)
                        backup_manifest.append({
                            "path": relative.as_posix(),
                            "backup": backup_path.relative_to(execution_dir).as_posix(),
                            "sha256": self._sha256(current),
                            "mode": stat.S_IMODE(mode),
                        })
                    else:
                        backup_manifest.append({
                            "path": relative.as_posix(), "backup": None,
                            "sha256": None, "mode": None,
                        })

                for change, relative, destination, current, mode in scoped:
                    self._assert_no_symlink(target_root, relative)
                    if destination.exists():
                        latest = destination.read_bytes()
                        if current is None or self._sha256(latest) != self._sha256(current):
                            raise ValueError(f"Target changed during execution; refusing write: {relative.as_posix()}")
                    elif current is not None:
                        raise ValueError(f"Target file disappeared during execution; refusing write: {relative.as_posix()}")
                    content = change.content.encode("utf-8")
                    self._atomic_write(destination, content, mode=mode)
                    applied.append((destination, current, mode))
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
                            "path": relative.as_posix(),
                            "before_sha256": self._sha256(current) if current is not None else None,
                            "after_sha256": self._sha256(change.content.encode("utf-8")),
                        }
                        for change, relative, destination, current, mode in scoped
                    ],
                    "backups": backup_manifest,
                    "validation": {
                        "status": "required_not_run",
                        "note": "CPI-06 does not execute project commands. Run the target project's approved regression suite before accepting this adaptation.",
                    },
                }
                audit_path = execution_dir / "audit.json"
                self._atomic_write(
                    audit_path,
                    (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                    mode=0o600,
                )
            except Exception:
                rollback_errors = []
                for destination, current, mode in reversed(applied):
                    try:
                        if current is None:
                            destination.unlink(missing_ok=True)
                        else:
                            self._atomic_write(destination, current, mode=mode)
                    except Exception as rollback_error:
                        rollback_errors.append(str(rollback_error))
                if rollback_errors:
                    raise RuntimeError("Execution failed and rollback was incomplete; recovery data retained: " + "; ".join(rollback_errors))
                try:
                    shutil.rmtree(execution_dir)
                except Exception as cleanup_error:
                    raise RuntimeError(
                        "Execution failed and rollback completed, but the replay marker could not be cleared; "
                        f"operator cleanup is required: {cleanup_error}"
                    )
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
