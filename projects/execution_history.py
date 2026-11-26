"""Read-only execution history and integrity inspection for CPI-06 records."""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from lisa.projects.execution_executor import ProjectExecutionExecutor
from lisa.projects.execution_ledger import ProjectExecutionLedger


class ProjectExecutionHistory:
    """Inspect execution journals without changing records or project files.

    Integrity checks are consistency and content-hash checks, not signatures:
    a local actor able to rewrite every record and hash can still forge history.
    """

    SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
    EXECUTION_RE = re.compile(r"^exec_[A-Za-z0-9_-]+$")

    def __init__(self, registry, state_dir=None):
        self._registry = registry
        self._state_dir = Path(
            state_dir or (Path.home() / ".lisa" / "executions")
        ).expanduser().resolve(strict=False)

    @staticmethod
    def _sha256(content):
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _canonical_digest(payload):
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def _validation_digest(cls, execution_id, audit, record):
        evidence = record.get("evidence")
        payload = {
            "execution_id": execution_id,
            "approval_digest": audit.get("approval_digest"),
            "target_project_id": audit.get("target_project_id"),
            "status": "passed" if record.get("status") == "operator_reported_passed" else "failed",
            "command": record.get("command"),
            "summary": record.get("summary"),
            "evidence": evidence,
        }
        return cls._canonical_digest(payload)

    @staticmethod
    def _unique_paths(items, key):
        paths = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get(key), str):
                raise ValueError("Execution manifest contains an invalid entry.")
            paths.append(item[key])
        if len(paths) != len(set(paths)):
            raise ValueError("Execution manifest contains duplicate paths.")
        return paths

    def _safe_execution_dir(self, execution_id):
        if not isinstance(execution_id, str) or not self.EXECUTION_RE.fullmatch(execution_id):
            raise ValueError("A valid execution ID is required.")
        directory = self._state_dir / execution_id
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Execution record was not found or is unsafe.")
        return directory

    def _verify_one(self, execution_id):
        directory = self._safe_execution_dir(execution_id)
        audit_path = directory / "audit.json"
        if audit_path.is_symlink() or not audit_path.is_file():
            raise ValueError("Execution audit record is missing or unsafe.")
        audit_bytes = audit_path.read_bytes()
        audit = json.loads(audit_bytes.decode("utf-8"))
        ledger = ProjectExecutionLedger(self._state_dir).verify()
        if not ledger["success"]:
            raise ValueError("Execution ledger verification failed: " + ledger["error"])
        matching_events = [
            event for event in ledger.get("events", [])
            if event.get("execution_id") == execution_id
        ]
        latest_event = matching_events[-1] if matching_events else None
        journal_path = directory / "execution.journal.json"
        journal_status = None
        if journal_path.exists():
            if journal_path.is_symlink() or not journal_path.is_file():
                raise ValueError("Execution journal is unsafe.")
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            if not isinstance(journal, dict) or journal.get("execution_id") != execution_id:
                raise ValueError("Execution journal identity is invalid.")
            journal_status = journal.get("status")
        ledger_status = "legacy_unanchored"
        if latest_event is not None:
            recorded_hash = (latest_event.get("details") or {}).get("audit_sha256")
            actual_hash = self._sha256(audit_bytes)
            if recorded_hash != actual_hash:
                raise ValueError("Execution audit has changed since its latest trusted-ledger event.")
            ledger_status = (
                "legacy_snapshot" if latest_event.get("event_type") == "legacy_import"
                else "locally_authenticated"
            )
        elif journal_status in ("applying", "recovery_required", "recovery_in_progress", "finalizing"):
            ledger_status = "execution_pending_recovery"
        if not isinstance(audit, dict) or audit.get("schema_version") != 1:
            raise ValueError("Unsupported or malformed execution audit schema.")
        if audit.get("execution_id") != execution_id:
            raise ValueError("Execution audit identity does not match its directory.")
        approval = audit.get("approval_digest")
        if not isinstance(approval, str) or not self.SHA256_RE.fullmatch(approval):
            raise ValueError("Execution approval digest is missing or malformed.")
        if execution_id != "exec_" + approval[:20]:
            raise ValueError("Execution ID does not match its approval digest.")

        changed = audit.get("changed_files")
        backups = audit.get("backups")
        if not isinstance(changed, list) or not changed:
            raise ValueError("Changed-file manifest is missing or malformed.")
        if not isinstance(backups, list):
            raise ValueError("Backup manifest is missing or malformed.")
        changed_paths = self._unique_paths(changed, "path")
        backup_paths = self._unique_paths(backups, "path")
        if set(changed_paths) != set(backup_paths):
            raise ValueError("Changed-file and backup manifests do not match.")

        backup_by_path = {item["path"]: item for item in backups}
        backup_results = []
        for item in changed:
            relative = ProjectExecutionExecutor._validated_relative_path(item["path"])
            before_hash, after_hash = item.get("before_sha256"), item.get("after_sha256")
            if after_hash is None or not self.SHA256_RE.fullmatch(str(after_hash)):
                raise ValueError(f"Invalid post-execution hash for {relative.as_posix()}.")
            if before_hash is not None and not self.SHA256_RE.fullmatch(str(before_hash)):
                raise ValueError(f"Invalid pre-execution hash for {relative.as_posix()}.")
            backup = backup_by_path[relative.as_posix()]
            if before_hash is None:
                if backup.get("backup") is not None or backup.get("sha256") is not None:
                    raise ValueError(f"Unexpected backup for newly created file: {relative.as_posix()}")
                backup_results.append({"path": relative.as_posix(), "status": "not_required"})
                continue
            backup_rel = Path(backup.get("backup") or "")
            if backup_rel.is_absolute() or not backup_rel.parts or ".." in backup_rel.parts:
                raise ValueError(f"Unsafe backup path for {relative.as_posix()}.")
            backup_path = directory / backup_rel
            cursor = directory
            for part in backup_rel.parts:
                cursor = cursor / part
                if cursor.is_symlink():
                    raise ValueError(f"Backup path contains a symlink: {relative.as_posix()}")
            if directory.resolve() not in backup_path.resolve().parents or not backup_path.is_file():
                raise ValueError(f"Backup is missing or unsafe: {relative.as_posix()}")
            digest = self._sha256(backup_path.read_bytes())
            if digest != before_hash or backup.get("sha256") != before_hash:
                raise ValueError(f"Backup integrity check failed: {relative.as_posix()}")
            backup_results.append({"path": relative.as_posix(), "status": "verified"})

        target_id = audit.get("target_project_id")
        target = self._registry.get(target_id)
        target_status = "unregistered"
        target_root = None
        if target is not None:
            target_root = Path(target.root_path).resolve(strict=False)
            recorded_root = Path(audit.get("target_root", "")).resolve(strict=False)
            if target_root != recorded_root:
                raise ValueError("Registered target root does not match the execution audit.")
            target_status = "registered"

        lifecycle = audit.get("lifecycle") or {}
        if not isinstance(lifecycle, dict):
            raise ValueError("Lifecycle metadata is malformed.")
        lifecycle_status = lifecycle.get("status", "applied")
        if lifecycle_status == "applying" and journal_status not in (
            "applying", "recovery_required", "recovery_in_progress", "finalizing"
        ):
            raise ValueError("Interrupted execution audit has no matching recoverable journal.")
        if lifecycle_status not in ("applying", "applied", "rollback_in_progress", "rolled_back"):
            raise ValueError("Unknown execution lifecycle state.")

        target_file_integrity = "not_checked_target_unregistered"
        if target_root is not None:
            states = []
            for item in changed:
                relative = ProjectExecutionExecutor._validated_relative_path(item["path"])
                destination = ProjectExecutionExecutor._assert_no_symlink(target_root, relative)
                actual = self._sha256(destination.read_bytes()) if destination.is_file() else None
                before_hash = item.get("before_sha256")
                after_hash = item.get("after_sha256")
                if lifecycle_status == "applying" and actual not in (before_hash, after_hash):
                    raise ValueError(f"Target file has an unknown version during interrupted application: {relative.as_posix()}")
                if lifecycle_status == "applied" and actual != after_hash:
                    raise ValueError(f"Target file no longer matches the applied version: {relative.as_posix()}")
                if lifecycle_status == "rolled_back" and actual != before_hash:
                    raise ValueError(f"Target file does not match the recorded rollback state: {relative.as_posix()}")
                if lifecycle_status == "rollback_in_progress" and actual not in (before_hash, after_hash):
                    raise ValueError(f"Target file has an unknown version during rollback: {relative.as_posix()}")
                states.append(actual)
            target_file_integrity = "verified"

        if lifecycle_status == "rolled_back":
            expected = self._canonical_digest({
                "approval_digest": approval,
                "target_root": audit.get("target_root"),
                "changed_files": changed,
                "backups": backups,
                "execution_id": execution_id,
            })
            if lifecycle.get("rollback_digest") != expected:
                raise ValueError("Rollback digest does not match the execution manifest.")
            restored = lifecycle.get("restored_files")
            if not isinstance(restored, list) or set(restored) != set(changed_paths):
                raise ValueError("Rollback restoration manifest is incomplete or inconsistent.")

        validation = audit.get("validation") or {}
        validation_status = validation.get("status", "required_not_run")
        validation_result = "not_recorded"
        validation_path = directory / "validation.json"
        if validation_status in ("operator_reported_passed", "operator_reported_failed"):
            if validation_path.is_symlink() or not validation_path.is_file():
                raise ValueError("Validation record referenced by the audit is missing or unsafe.")
            record = json.loads(validation_path.read_text(encoding="utf-8"))
            if not isinstance(record, dict) or record.get("execution_id") != execution_id:
                raise ValueError("Validation record identity is invalid.")
            if record.get("status") != validation_status:
                raise ValueError("Validation record status does not match the audit.")
            if record.get("status") not in ("operator_reported_passed", "operator_reported_failed"):
                raise ValueError("Validation record contains an unknown status.")
            digest = self._validation_digest(execution_id, audit, record)
            if record.get("evidence_digest") != digest or validation.get("evidence_digest") != digest:
                raise ValueError("Validation record digest does not match its contents.")
            evidence = record.get("evidence")
            if evidence is not None:
                if not isinstance(evidence, dict):
                    raise ValueError("Validation evidence metadata is malformed.")
                if target_root is None:
                    validation_result = "evidence_unverifiable_target_unregistered"
                else:
                    relative = ProjectExecutionExecutor._validated_relative_path(evidence.get("path"))
                    evidence_file = ProjectExecutionExecutor._assert_no_symlink(target_root, relative)
                    if not evidence_file.is_file():
                        raise ValueError("Validation evidence file is missing.")
                    data = evidence_file.read_bytes()
                    if len(data) != evidence.get("bytes") or self._sha256(data) != evidence.get("sha256"):
                        raise ValueError("Validation evidence file hash does not match its record.")
                    validation_result = "verified"
            else:
                validation_result = "record_verified_no_report"
        elif validation_status != "required_not_run":
            raise ValueError("Unknown validation status.")

        source = self._registry.get(audit.get("source_project_id"))
        return {
            "execution_id": execution_id,
            "created_at": audit.get("created_at"),
            "source_project_id": audit.get("source_project_id"),
            "source_project_name": source.name if source else audit.get("source_project_id", "unknown"),
            "target_project_id": target_id,
            "target_project_name": target.name if target else target_id or "unknown",
            "target_status": target_status,
            "plan_id": audit.get("plan_id"),
            "approval_digest": approval,
            "file_count": len(changed),
            "files": changed_paths,
            "lifecycle_status": lifecycle_status,
            "execution_journal_status": journal_status,
            "validation_status": validation_status,
            "validation_integrity": validation_result,
            "backup_integrity": "verified",
            "backup_results": backup_results,
            "target_file_integrity": target_file_integrity,
            "integrity_status": "consistent",
            "ledger_status": ledger_status,
            "ledger_event_count": len(matching_events),
            "integrity_notes": [
                "Audit structure, execution identity, manifests, and available backup/evidence hashes are consistent.",
                "Ledger HMAC and authenticated head checks detect changes while the separate local key and head checkpoint remain intact.",
                "The local ledger and key are not an external trust anchor; an administrator able to replace both can forge history.",
            ] + (["This execution predates the ledger and has not been imported."] if ledger_status == "legacy_unanchored" else [] )
              + (["This execution was interrupted; target files may be in a mixed before/after state until explicitly recovered."] if ledger_status == "execution_pending_recovery" else [] )
              + (["This execution was imported as a snapshot; its pre-migration history is not authenticated."] if ledger_status == "legacy_snapshot" else [] ),
        }

    def verify(self, execution_id):
        """Return a read-only integrity report for one execution."""
        try:
            return {"success": True, "record": self._verify_one(execution_id)}
        except Exception as exc:
            return {"success": False, "execution_id": execution_id, "integrity_status": "failed", "error": str(exc)}

    def list_history(self, project_id=None):
        """List newest execution records first; malformed entries remain visible."""
        if not self._state_dir.exists():
            return []
        if self._state_dir.is_symlink() or not self._state_dir.is_dir():
            raise ValueError("Execution history directory is unsafe.")
        records = []
        for directory in self._state_dir.iterdir():
            if directory.is_symlink() or not directory.is_dir() or not self.EXECUTION_RE.fullmatch(directory.name):
                continue
            result = self.verify(directory.name)
            if result["success"]:
                record = result["record"]
            else:
                record = {
                    "execution_id": directory.name,
                    "created_at": None,
                    "source_project_id": None,
                    "source_project_name": "unknown",
                    "target_project_id": None,
                    "target_project_name": "unknown",
                    "file_count": 0,
                    "lifecycle_status": "unknown",
                    "validation_status": "unknown",
                    "integrity_status": "failed",
                    "integrity_error": result["error"],
                }
                audit_path = directory / "audit.json"
                try:
                    if audit_path.is_file() and not audit_path.is_symlink():
                        raw = json.loads(audit_path.read_text(encoding="utf-8"))
                        record["created_at"] = raw.get("created_at")
                        record["source_project_id"] = raw.get("source_project_id")
                        record["target_project_id"] = raw.get("target_project_id")
                        source = self._registry.get(record["source_project_id"])
                        target = self._registry.get(record["target_project_id"])
                        record["source_project_name"] = source.name if source else record["source_project_id"] or "unknown"
                        record["target_project_name"] = target.name if target else record["target_project_id"] or "unknown"
                        record["file_count"] = len(raw.get("changed_files", [])) if isinstance(raw.get("changed_files"), list) else 0
                        lifecycle = raw.get("lifecycle") if isinstance(raw.get("lifecycle"), dict) else {}
                        validation = raw.get("validation") if isinstance(raw.get("validation"), dict) else {}
                        record["lifecycle_status"] = lifecycle.get("status", "applied")
                        record["validation_status"] = validation.get("status", "required_not_run")
                    else:
                        record["integrity_error"] = "Audit record missing or unsafe."
                except Exception:
                    pass
            if project_id and project_id not in (record.get("source_project_id"), record.get("target_project_id")):
                continue
            records.append(record)
        records.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return records
