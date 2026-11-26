"""Tamper-evident, recoverable HMAC-authenticated CPI execution ledger.

The local key and authenticated head detect ordinary ledger edits while they
remain intact. They are not an external trust anchor.
"""
import hashlib
import hmac
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class ProjectExecutionLedger:
    SCHEMA_VERSION = 1
    LEDGER_NAME = "ledger.jsonl"
    KEY_NAME = ".ledger.key"
    HEAD_NAME = ".ledger.head"
    PENDING_NAME = ".ledger.pending"
    LOCK_NAME = ".ledger.lock"
    ZERO_HASH = "0" * 64

    def __init__(self, state_dir=None):
        self._state_dir_input = Path(
            state_dir or (Path.home() / ".lisa" / "executions")
        ).expanduser().absolute()
        self._state_dir = self._state_dir_input.resolve(strict=False)
        self._ledger_path = self._state_dir / self.LEDGER_NAME
        self._key_path = self._state_dir / self.KEY_NAME
        self._head_path = self._state_dir / self.HEAD_NAME
        self._pending_path = self._state_dir / self.PENDING_NAME

    @staticmethod
    def _canonical(value):
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

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

    def _fsync_directory(self):
        if os.name != "posix":
            return
        descriptor = os.open(str(self._state_dir), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _atomic_write(self, path, content, prefix):
        if path.is_symlink():
            raise ValueError(f"Ledger state path is unsafe: {path.name}")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=str(self._state_dir), prefix=prefix,
                suffix=".tmp", delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(str(temporary), str(path))
            self._fsync_directory()
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def _load_key(self, create=False):
        if self._key_path.is_symlink():
            raise ValueError("Ledger key path is unsafe.")
        if self._key_path.exists():
            info = self._key_path.stat()
            if not self._key_path.is_file() or info.st_size != 32:
                raise ValueError("Ledger key is malformed.")
            if os.name == "posix" and info.st_mode & 0o077:
                raise ValueError(
                    "Ledger key permissions are too broad; expected owner-only access."
                )
            return self._key_path.read_bytes()
        if not create:
            raise ValueError("Ledger key is missing; refusing to trust the ledger.")
        if self._ledger_path.exists() or self._head_path.exists():
            raise ValueError("Ledger state exists without its key; refusing key regeneration.")
        key = secrets.token_bytes(32)
        descriptor = os.open(
            str(self._key_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        try:
            view = memoryview(key)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("Unable to persist ledger key.")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        self._fsync_directory()
        return key

    def _initialize_empty_state(self):
        """Complete only an empty first-use initialization; never reset history."""
        key = self._load_key(create=True)
        if self._ledger_path.is_symlink() or self._head_path.is_symlink():
            raise ValueError("Ledger state path is unsafe.")
        if not self._ledger_path.exists():
            if self._head_path.exists():
                head = self._read_head(key)
                if head["sequence"] != 0 or head["event_hash"] != self.ZERO_HASH:
                    raise ValueError("Ledger file is missing despite a non-empty authenticated head.")
            descriptor = os.open(
                str(self._ledger_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self._fsync_directory()
        if not self._ledger_path.is_file():
            raise ValueError("Ledger path is not a regular file.")
        if self._ledger_path.stat().st_size != 0 and not self._head_path.exists():
            raise ValueError("Non-empty ledger is missing its authenticated head checkpoint.")
        if not self._head_path.exists():
            self._write_head(key, 0, self.ZERO_HASH)
        return key

    def _read_events(self, raw=None):
        if self._ledger_path.is_symlink():
            raise ValueError("Ledger path is unsafe.")
        if raw is None:
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
                raise ValueError(
                    f"Ledger record {line_number} is malformed: {exc}"
                ) from exc
            if not isinstance(item, dict):
                raise ValueError(f"Ledger record {line_number} is not an object.")
            events.append(item)
        return events

    @classmethod
    def _event_body(cls, event):
        return {
            key: value for key, value in event.items()
            if key not in ("mac", "event_hash")
        }

    def _verify_events(self, key, events):
        previous = self.ZERO_HASH
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
        return previous, verified

    def _write_head(self, key, sequence, event_hash):
        body = {
            "schema_version": self.SCHEMA_VERSION,
            "sequence": sequence,
            "event_hash": event_hash,
        }
        head = {
            **body,
            "mac": hmac.new(key, self._canonical(body), hashlib.sha256).hexdigest(),
        }
        self._atomic_write(
            self._head_path, self._canonical(head) + b"\n", ".ledger-head."
        )

    def _read_head(self, key):
        if self._head_path.is_symlink() or not self._head_path.is_file():
            raise ValueError("Authenticated ledger head checkpoint is missing or unsafe.")
        head = json.loads(self._head_path.read_text(encoding="utf-8"))
        if not isinstance(head, dict):
            raise ValueError("Authenticated ledger head checkpoint is malformed.")
        body = {
            field: head.get(field)
            for field in ("schema_version", "sequence", "event_hash")
        }
        expected_mac = hmac.new(
            key, self._canonical(body), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(str(head.get("mac", "")), expected_mac):
            raise ValueError("Ledger head checkpoint authentication failed.")
        if body["schema_version"] != self.SCHEMA_VERSION:
            raise ValueError("Unsupported ledger head checkpoint schema.")
        if not isinstance(body["sequence"], int) or body["sequence"] < 0:
            raise ValueError("Ledger head sequence is malformed.")
        if not isinstance(body["event_hash"], str):
            raise ValueError("Ledger head hash is malformed.")
        return body

    def _verify_head(self, key, events, previous):
        head = self._read_head(key)
        if head["sequence"] != len(events) or head["event_hash"] != previous:
            raise ValueError(
                "Ledger contents do not match the authenticated head checkpoint."
            )

    def _read_pending(self, key):
        if self._pending_path.is_symlink():
            raise ValueError("Pending ledger transaction path is unsafe.")
        if not self._pending_path.exists():
            return None
        if not self._pending_path.is_file():
            raise ValueError("Pending ledger transaction is not a regular file.")
        pending = json.loads(self._pending_path.read_text(encoding="utf-8"))
        if not isinstance(pending, dict):
            raise ValueError("Pending ledger transaction is malformed.")
        body = {name: value for name, value in pending.items() if name != "mac"}
        expected = hmac.new(key, self._canonical(body), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(str(pending.get("mac", "")), expected):
            raise ValueError("Pending ledger transaction authentication failed.")
        if body.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("Unsupported pending ledger transaction schema.")
        event = body.get("event")
        if not isinstance(event, dict):
            raise ValueError("Pending ledger event is malformed.")
        return body

    def _write_pending(self, key, event, previous_bytes, previous_sequence, previous_hash):
        body = {
            "schema_version": self.SCHEMA_VERSION,
            "previous_size": len(previous_bytes),
            "previous_ledger_sha256": self._sha256(previous_bytes),
            "previous_sequence": previous_sequence,
            "previous_hash": previous_hash,
            "event": event,
        }
        pending = {
            **body,
            "mac": hmac.new(key, self._canonical(body), hashlib.sha256).hexdigest(),
        }
        self._atomic_write(
            self._pending_path, self._canonical(pending) + b"\n", ".ledger-pending."
        )

    def _append_bytes(self, encoded):
        descriptor = os.open(
            str(self._ledger_path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600
        )
        try:
            view = memoryview(encoded)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("Unable to append execution ledger event.")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _remove_stale_lock_if_dead(self, lock_path):
        """Remove a lock only when its recorded owner PID is demonstrably gone."""
        if lock_path.is_symlink():
            raise ValueError("Ledger lock path is unsafe.")
        try:
            info = lock_path.lstat()
        except FileNotFoundError:
            return
        if not lock_path.is_file():
            raise ValueError("Ledger lock is not a regular file; inspect it manually.")
        raw_pid = lock_path.read_text(encoding="ascii").strip()
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError) as exc:
            raise ValueError("Ledger lock owner is unreadable; inspect .ledger.lock manually.") from exc
        if pid <= 0:
            raise ValueError("Ledger lock owner PID is invalid; inspect .ledger.lock manually.")
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            current = lock_path.lstat()
            if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
                raise ValueError("Ledger lock changed during stale-lock inspection; retry.")
            lock_path.unlink()
            self._fsync_directory()
        except PermissionError as exc:
            raise ValueError("Cannot confirm whether the ledger lock owner is alive; refusing to remove it.") from exc
        except OSError as exc:
            raise ValueError("Cannot confirm whether the ledger lock owner is alive; refusing to remove it.") from exc
        else:
            raise ValueError(f"Ledger is locked by active process {pid}; refusing concurrent access.")

    def _acquire_lock(self):
        lock_path = self._state_dir / self.LOCK_NAME
        if lock_path.is_symlink():
            raise ValueError("Ledger lock path is unsafe.")
        try:
            descriptor = os.open(
                str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
        except FileExistsError:
            self._remove_stale_lock_if_dead(lock_path)
            try:
                descriptor = os.open(
                    str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
            except FileExistsError as exc:
                raise ValueError("Ledger is busy; another process acquired the lock.") from exc
        try:
            data = str(os.getpid()).encode("ascii")
            view = memoryview(data)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("Unable to persist ledger lock.")
                view = view[written:]
            os.fsync(descriptor)
            self._fsync_directory()
        except Exception:
            os.close(descriptor)
            lock_path.unlink(missing_ok=True)
            raise
        return descriptor, lock_path

    def _release_lock(self, descriptor, lock_path):
        try:
            opened = os.fstat(descriptor)
            current = lock_path.lstat()
            if (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino):
                lock_path.unlink()
                self._fsync_directory()
        except FileNotFoundError:
            pass
        finally:
            os.close(descriptor)

    def _remove_pending(self):
        if self._pending_path.is_symlink():
            raise ValueError("Pending ledger transaction path is unsafe.")
        self._pending_path.unlink(missing_ok=True)
        self._fsync_directory()

    def _recover_pending_locked(self, key, pending):
        if self._ledger_path.is_symlink():
            raise ValueError("Ledger path is unsafe.")
        raw = self._ledger_path.read_bytes() if self._ledger_path.exists() else b""
        previous_size = pending.get("previous_size")
        if not isinstance(previous_size, int) or previous_size < 0:
            raise ValueError("Pending ledger transaction has an invalid prior size.")
        if len(raw) < previous_size:
            raise ValueError("Ledger is shorter than the authenticated pre-append snapshot.")
        prefix = raw[:previous_size]
        if self._sha256(prefix) != pending.get("previous_ledger_sha256"):
            raise ValueError("Ledger pre-append bytes do not match the pending transaction.")
        prior_events = self._read_events(prefix)
        prior_hash, _ = self._verify_events(key, prior_events)
        if len(prior_events) != pending.get("previous_sequence"):
            raise ValueError("Pending transaction prior sequence does not match the ledger.")
        if prior_hash != pending.get("previous_hash"):
            raise ValueError("Pending transaction prior hash does not match the ledger.")
        event = pending["event"]
        if event.get("sequence") != len(prior_events) + 1:
            raise ValueError("Pending event sequence is invalid.")
        if event.get("previous_hash") != prior_hash:
            raise ValueError("Pending event does not extend the authenticated ledger.")
        _, verified_event = self._verify_events(key, prior_events + [event])
        if len(verified_event) != len(prior_events) + 1:
            raise ValueError("Pending event verification failed.")
        encoded = self._canonical(event) + b"\n"
        suffix = raw[previous_size:]
        if suffix not in (b"", encoded) and not encoded.startswith(suffix):
            raise ValueError("Ledger has unexpected bytes after the pending transaction boundary.")

        head = None
        if self._head_path.exists():
            head = self._read_head(key)
        old_head = {
            "sequence": len(prior_events),
            "event_hash": prior_hash,
        }
        new_head = {
            "sequence": event["sequence"],
            "event_hash": event["event_hash"],
        }
        if head is None or {
            "sequence": head["sequence"], "event_hash": head["event_hash"]
        } not in (old_head, new_head):
            raise ValueError("Authenticated head does not match either side of the pending transaction.")

        if suffix != encoded:
            with self._ledger_path.open("r+b") as handle:
                handle.truncate(previous_size)
                handle.flush()
                os.fsync(handle.fileno())
            self._append_bytes(encoded)
        self._write_head(key, event["sequence"], event["event_hash"])
        self._remove_pending()
        return event

    def preview_recovery_digest(self):
        """Return the digest an operator must confirm to recover a pending append."""
        try:
            self._assert_state_dir_safe()
            if self._pending_path.is_symlink():
                raise ValueError("Pending ledger transaction path is unsafe.")
            if not self._pending_path.exists():
                return None
            key = self._load_key(create=False)
            pending = self._read_pending(key)
            return self._sha256(self._canonical(pending))
        except Exception:
            raise

    def recover(self, operator_confirmation):
        """Complete one authenticated interrupted append after exact operator approval."""
        self._ensure_state_dir()
        if self._pending_path.is_symlink():
            return {"success": False, "status": "failed", "error": "Pending ledger transaction path is unsafe."}
        if not self._pending_path.exists():
            return {"success": True, "status": "no_pending_transaction"}
        try:
            descriptor, lock_path = self._acquire_lock()
        except Exception as exc:
            return {"success": False, "status": "failed", "error": str(exc)}
        try:
            key = self._load_key(create=False)
            pending = self._read_pending(key)
            if pending is None:
                return {"success": True, "status": "no_pending_transaction"}
            digest = self._sha256(self._canonical(pending))
            if operator_confirmation != f"RECOVER {digest}":
                raise ValueError(
                    "Explicit recovery approval mismatch. Confirm with: RECOVER <recovery-digest>."
                )
            event = self._recover_pending_locked(key, pending)
            return {
                "success": True,
                "status": "recovered",
                "sequence": event["sequence"],
                "execution_id": event["execution_id"],
            }
        except Exception as exc:
            return {"success": False, "status": "failed", "error": str(exc)}
        finally:
            self._release_lock(descriptor, lock_path)

    def verify(self):
        """Verify sequence, hash chain, HMAC, and authenticated head checkpoint."""
        try:
            self._assert_state_dir_safe()
            if self._pending_path.is_symlink():
                raise ValueError("Pending ledger transaction path is unsafe.")
            if self._pending_path.exists():
                raise ValueError(
                    "A pending ledger append requires explicit recovery; run 'lisa project ledger recover'."
                )
            artifacts = (
                self._ledger_path.exists(),
                self._key_path.exists(),
                self._head_path.exists(),
            )
            if not any(artifacts):
                return {
                    "success": True, "status": "not_initialized",
                    "event_count": 0, "events": [],
                }
            if not all(artifacts):
                raise ValueError(
                    "Ledger, key, and authenticated head checkpoint must all exist together."
                )
            key = self._load_key(create=False)
            events = self._read_events()
            previous, verified = self._verify_events(key, events)
            self._verify_head(key, events, previous)
            return {
                "success": True, "status": "verified", "event_count": len(events),
                "head_hash": previous, "events": verified,
            }
        except Exception as exc:
            return {
                "success": False, "status": "failed", "event_count": 0,
                "events": [], "error": str(exc),
            }

    def append(self, event_type, execution_id, details=None):
        """Append one authenticated event using a recoverable two-phase journal."""
        self._ensure_state_dir()
        descriptor, lock_path = self._acquire_lock()
        try:
            if self._pending_path.exists():
                raise ValueError(
                    "A prior ledger append requires explicit recovery before another append."
                )
            key = self._initialize_empty_state()
            current = self.verify()
            if not current["success"]:
                raise ValueError(f"Cannot append to an invalid ledger: {current['error']}")
            previous_bytes = self._ledger_path.read_bytes()
            previous = current.get("head_hash", self.ZERO_HASH)
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
            encoded = self._canonical(event) + b"\n"
            try:
                self._write_pending(
                    key, event, previous_bytes, current["event_count"], previous
                )
            except Exception as exc:
                try:
                    self._remove_pending()
                except Exception as cleanup_error:
                    raise RuntimeError(
                        "Unable to clean up an interrupted pending-ledger write: "
                        + str(cleanup_error)
                    ) from exc
                raise
            try:
                self._append_bytes(encoded)
                self._write_head(key, event["sequence"], event["event_hash"])
                self._remove_pending()
            except Exception as exc:
                # If this process is still alive, restore the exact pre-append
                # state before returning failure. A hard crash leaves the
                # authenticated pending record for explicit recovery.
                try:
                    raw = self._ledger_path.read_bytes()
                    if (
                        len(raw) >= len(previous_bytes)
                        and raw[:len(previous_bytes)] == previous_bytes
                    ):
                        suffix = raw[len(previous_bytes):]
                        if suffix == b"" or encoded.startswith(suffix):
                            with self._ledger_path.open("r+b") as handle:
                                handle.truncate(len(previous_bytes))
                                handle.flush()
                                os.fsync(handle.fileno())
                            self._write_head(key, current["event_count"], previous)
                            self._remove_pending()
                except Exception as cleanup_error:
                    raise RuntimeError(
                        "Ledger append failed and automatic cleanup was incomplete; "
                        "inspect and recover the pending transaction before retrying: "
                        + str(cleanup_error)
                    ) from exc
                raise
            return event
        finally:
            self._release_lock(descriptor, lock_path)

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
