"""Tamper-evident, HMAC-authenticated append-only CPI execution ledger.

The ledger detects edits, deletions, reordering, and insertion when the local
ledger key remains intact. It is not an external trust anchor: an administrator
with access to both the ledger and key can rewrite both.
"""
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path


class ProjectExecutionLedger:
    SCHEMA_VERSION = 1
    LEDGER_NAME = "ledger.jsonl"
    KEY_NAME = ".ledger.key"

    def __init__(self, state_dir=None):
        self._state_dir = Path(
            state_dir or (Path.home() / ".lisa" / "executions")
        ).expanduser().resolve(strict=False)
        self._ledger_path = self._state_dir / self.LEDGER_NAME
        self._key_path = self._state_dir / self.KEY_NAME

    @staticmethod
    def _canonical(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _sha256(value):
        return hashlib.sha256(value).hexdigest()

    def _ensure_state_dir(self):
        if self._state_dir.is_symlink():
            raise ValueError("Execution state directory must not be a symlink.")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        if not self._state_dir.is_dir():
            raise ValueError("Execution state path is not a directory.")

    def _load_key(self, create=False):
        if self._key_path.is_symlink():
            raise ValueError("Ledger key path is unsafe.")
        if self._key_path.exists():
            info = self._key_path.stat()
            if not self._key_path.is_file() or info.st_size != 32:
                raise ValueError("Ledger key is malformed.")
            return self._key_path.read_bytes()
        if not create:
            raise ValueError("Ledger key is missing; refusing to trust the ledger.")
        if self._ledger_path.exists():
            raise ValueError("Ledger exists without its key; refusing key regeneration.")
        key = secrets.token_bytes(32)
        descriptor = os.open(str(self._key_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, key)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return key

    def _read_events(self):
        if self._ledger_path.is_symlink():
            raise ValueError("Ledger path is unsafe.")
        if not self._ledger_path.exists():
            return []
        if not self._ledger_path.is_file():
            raise ValueError("Ledger path is not a regular file.")
        raw = self._ledger_path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise ValueError("Ledger has an incomplete trailing record.")
        events = []
        for line_number, line in enumerate(raw.splitlines(), 1):
            try:
                item = json.loads(line.decode("utf-8"))
            except Exception as exc:
                raise ValueError(f"Ledger record {line_number} is malformed: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"Ledger record {line_number} is not an object.")
            events.append(item)
        return events

    @classmethod
    def _event_body(cls, event):
        return {key: value for key, value in event.items() if key not in ("mac", "event_hash")}

    def verify(self):
        """Verify sequence, hash chain, and HMAC without changing local state."""
        try:
            if not self._ledger_path.exists() and not self._key_path.exists():
                return {"success": True, "status": "not_initialized", "event_count": 0, "events": []}
            key = self._load_key(create=False)
            events = self._read_events()
            previous = "0" * 64
            verified = []
            for index, event in enumerate(events, 1):
                if event.get("schema_version") != self.SCHEMA_VERSION:
                    raise ValueError(f"Unsupported ledger schema at sequence {index}.")
                if event.get("sequence") != index:
                    raise ValueError(f"Ledger sequence gap or reordering at sequence {index}.")
                if event.get("previous_hash") != previous:
                    raise ValueError(f"Ledger hash-chain mismatch at sequence {index}.")
                body = self._event_body(event)
                mac = hmac.new(key, self._canonical(body), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(str(event.get("mac", "")), mac):
                    raise ValueError(f"Ledger authentication failed at sequence {index}.")
                event_hash = self._sha256(self._canonical({**body, "mac": mac}))
                if event.get("event_hash") != event_hash:
                    raise ValueError(f"Ledger event hash mismatch at sequence {index}.")
                previous = event_hash
                verified.append(event)
            return {
                "success": True, "status": "verified", "event_count": len(events),
                "head_hash": previous, "events": verified,
            }
        except Exception as exc:
            return {"success": False, "status": "failed", "event_count": 0, "events": [], "error": str(exc)}

    def append(self, event_type, execution_id, details=None):
        """Append one authenticated event; concurrent writers fail closed."""
        self._ensure_state_dir()
        lock_path = self._state_dir / ".ledger.lock"
        if lock_path.is_symlink():
            raise ValueError("Ledger lock path is unsafe.")
        try:
            lock_fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ValueError("Ledger is busy or has a stale lock; inspect .ledger.lock before retrying.") from exc
        try:
            os.write(lock_fd, str(os.getpid()).encode("ascii"))
            os.fsync(lock_fd)
            current = self.verify()
            if not current["success"]:
                raise ValueError(f"Cannot append to an invalid ledger: {current['error']}")
            key = self._load_key(create=True)
            previous = current.get("head_hash", "0" * 64)
            body = {
                "schema_version": self.SCHEMA_VERSION,
                "sequence": current["event_count"] + 1,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "event_type": str(event_type),
                "execution_id": str(execution_id),
                "details": details or {},
                "previous_hash": previous,
            }
            mac = hmac.new(key, self._canonical(body), hashlib.sha256).hexdigest()
            event = {**body, "mac": mac}
            event["event_hash"] = self._sha256(self._canonical(event))
            encoded = self._canonical(event) + b"\\n"
            descriptor = os.open(str(self._ledger_path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                written = os.write(descriptor, encoded)
                if written != len(encoded):
                    raise OSError("Short write while appending execution ledger.")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return event
        finally:
            os.close(lock_fd)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def migrate_legacy(self):
        """Anchor current snapshots of pre-ledger records as explicitly legacy imports.

        This does not authenticate their historical origin or chronology. It only
        records the exact snapshot observed at migration time.
        """
        self._ensure_state_dir()
        verification = self.verify()
        if not verification["success"]:
            return {"success": False, "error": verification["error"], "imported": 0}
        known = {
            event.get("execution_id")
            for event in verification.get("events", [])
            if event.get("event_type") in ("execution_applied", "legacy_import")
        }
        imported = []
        for directory in sorted(self._state_dir.iterdir()):
            if directory.is_symlink() or not directory.is_dir() or not directory.name.startswith("exec_"):
                continue
            audit_path = directory / "audit.json"
            if audit_path.is_symlink() or not audit_path.is_file() or directory.name in known:
                continue
            audit_bytes = audit_path.read_bytes()
            try:
                audit = json.loads(audit_bytes.decode("utf-8"))
            except Exception:
                continue
            if not isinstance(audit, dict) or audit.get("execution_id") != directory.name:
                continue
            event = self.append("legacy_import", directory.name, {
                "audit_sha256": self._sha256(audit_bytes),
                "source_created_at": audit.get("created_at"),
                "trust": "snapshot_at_migration_time_only",
            })
            imported.append({"execution_id": directory.name, "sequence": event["sequence"]})
        return {"success": True, "imported": len(imported), "records": imported}
