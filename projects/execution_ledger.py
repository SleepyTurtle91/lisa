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
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class ProjectExecutionLedger:
    SCHEMA_VERSION = 1
    LEDGER_NAME = "ledger.jsonl"
    KEY_NAME = ".ledger.key"
    HEAD_NAME = ".ledger.head"

    def __init__(self, state_dir=None):
        self._state_dir_input = Path(
            state_dir or (Path.home() / ".lisa" / "executions")
        ).expanduser().absolute()
        self._state_dir = self._state_dir_input.resolve(strict=False)
        self._ledger_path = self._state_dir / self.LEDGER_NAME
        self._key_path = self._state_dir / self.KEY_NAME
        self._head_path = self._state_dir / self.HEAD_NAME

    @staticmethod
    def _canonical(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _sha256(value):
        return hashlib.sha256(value).hexdigest()

    def _assert_state_dir_safe(self):
        cursor = self._state_dir_input
        while cursor != cursor.parent:
            if cursor.is_symlink():
                raise ValueError("Execution state path must not contain symlinks.")
            cursor = cursor.parent

    def _ensure_state_dir(self):
        self._assert_state_dir_safe()
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
            if os.name == "posix" and info.st_mode & 0o077:
                raise ValueError("Ledger key permissions are too broad; expected owner-only access.")
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

    def _write_head(self, key, sequence, event_hash):
        if self._head_path.is_symlink():
            raise ValueError("Ledger head path is unsafe.")
        body = {"schema_version": self.SCHEMA_VERSION, "sequence": sequence, "event_hash": event_hash}
        head = {**body, "mac": hmac.new(key, self._canonical(body), hashlib.sha256).hexdigest()}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=str(self._state_dir), prefix=".ledger-head.",
                suffix=".tmp", delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(self._canonical(head) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(str(temporary), str(self._head_path))
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def _verify_head(self, key, events, previous):
        if self._head_path.is_symlink() or not self._head_path.is_file():
            raise ValueError("Authenticated ledger head checkpoint is missing or unsafe.")
        head = json.loads(self._head_path.read_text(encoding="utf-8"))
        if not isinstance(head, dict):
            raise ValueError("Authenticated ledger head checkpoint is malformed.")
        body = {key: head.get(key) for key in ("schema_version", "sequence", "event_hash")}
        expected_mac = hmac.new(key, self._canonical(body), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(str(head.get("mac", "")), expected_mac):
            raise ValueError("Ledger head checkpoint authentication failed.")
        if body["schema_version"] != self.SCHEMA_VERSION:
            raise ValueError("Unsupported ledger head checkpoint schema.")
        if body["sequence"] != len(events) or body["event_hash"] != previous:
            raise ValueError("Ledger contents do not match the authenticated head checkpoint.")

    def verify(self):
        """Verify sequence, hash chain, HMAC, and authenticated head checkpoint."""
        try:
            self._assert_state_dir_safe()
            artifacts = (self._ledger_path.exists(), self._key_path.exists(), self._head_path.exists())
            if not any(artifacts):
                return {"success": True, "status": "not_initialized", "event_count": 0, "events": []}
            if not all(artifacts):
                raise ValueError("Ledger, key, and authenticated head checkpoint must all exist together.")
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
            self._verify_head(key, events, previous)
            return {
                "success": True, "status": "verified", "event_count": len(events),
                "head_hash": previous, "events": verified,
            }
        except Exception as exc:
            return {"success": False, "status": "failed", "event_count": 0, "events": [], "error": str(exc)}

    def _acquire_writer_lock(self):
        """Acquire a process-released OS lock; the lock file itself may persist."""
        lock_path = self._state_dir / ".ledger.lock"
        if lock_path.is_symlink():
            raise ValueError("Ledger lock path is unsafe.")
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(str(lock_path), flags, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("Ledger lock must be a regular file.")
            if os.name == "posix":
                if info.st_mode & 0o077:
                    raise ValueError("Ledger lock permissions are too broad.")
                import fcntl
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise ValueError("Ledger is busy; another writer holds the OS lock.") from exc
            elif os.name == "nt":
                import msvcrt
                if info.st_size == 0:
                    os.write(descriptor, b"\\0")
                    os.fsync(descriptor)
                os.lseek(descriptor, 0, os.SEEK_SET)
                try:
                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise ValueError("Ledger is busy; another writer holds the OS lock.") from exc
            else:
                raise ValueError("This platform does not provide a supported ledger writer lock.")
            return descriptor
        except Exception:
            os.close(descriptor)
            raise

    @staticmethod
    def _release_writer_lock(descriptor):
        try:
            if os.name == "posix":
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            elif os.name == "nt":
                import msvcrt
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(descriptor)

    def append(self, event_type, execution_id, details=None):
        """Append one authenticated event with process-safe locking and tail recovery."""
        self._ensure_state_dir()
        lock_fd = self._acquire_writer_lock()
        try:
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

            descriptor = os.open(
                str(self._ledger_path),
                os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            original_size = os.fstat(descriptor).st_size
            try:
                offset = 0
                try:
                    while offset < len(encoded):
                        written = os.write(descriptor, encoded[offset:])
                        if written <= 0:
                            raise OSError("Ledger append made no forward progress.")
                        offset += written
                    os.fsync(descriptor)
                except Exception:
                    try:
                        os.ftruncate(descriptor, original_size)
                        os.fsync(descriptor)
                    except Exception as recovery_error:
                        raise RuntimeError(
                            "Ledger append failed and the incomplete tail could not be removed; "
                            f"operator recovery is required: {recovery_error}"
                        )
                    raise
            finally:
                os.close(descriptor)

            self._write_head(key, event["sequence"], event["event_hash"])
            return event
        finally:
            self._release_writer_lock(lock_fd)

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
