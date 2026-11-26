import json
import tempfile
import unittest
from pathlib import Path

from lisa.projects.execution_ledger import ProjectExecutionLedger


class TestProjectExecutionLedger(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "executions"
        self.ledger = ProjectExecutionLedger(self.state)

    def test_appends_and_verifies_hash_chained_events(self):
        first = self.ledger.append("execution_applied", "exec_one", {"audit_sha256": "a" * 64})
        second = self.ledger.append("validation_recorded", "exec_one", {"audit_sha256": "b" * 64})
        result = self.ledger.verify()
        self.assertTrue(result["success"], result.get("error"))
        self.assertEqual(result["event_count"], 2)
        self.assertEqual(first["sequence"], 1)
        self.assertEqual(second["sequence"], 2)
        self.assertEqual(second["previous_hash"], first["event_hash"])

    def test_editing_event_is_detected(self):
        self.ledger.append("execution_applied", "exec_one", {"audit_sha256": "a" * 64})
        path = self.state / "ledger.jsonl"
        event = json.loads(path.read_text(encoding="utf-8"))
        event["execution_id"] = "exec_forged"
        path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        result = self.ledger.verify()
        self.assertFalse(result["success"])
        self.assertIn("authentication failed", result["error"])

    def test_missing_key_does_not_trigger_key_regeneration(self):
        self.ledger.append("execution_applied", "exec_one", {"audit_sha256": "a" * 64})
        (self.state / ".ledger.key").unlink()
        result = self.ledger.verify()
        self.assertFalse(result["success"])
        with self.assertRaisesRegex(ValueError, "must all exist together"):
            self.ledger.append("execution_applied", "exec_two", {})

    def test_legacy_migration_records_snapshot_not_historical_authenticity(self):
        execution = self.state / "exec_legacy"
        execution.mkdir(parents=True)
        audit = {
            "schema_version": 1,
            "execution_id": "exec_legacy",
            "created_at": "2026-11-01T00:00:00+00:00",
        }
        (execution / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
        result = self.ledger.migrate_legacy()
        self.assertTrue(result["success"], result.get("error"))
        self.assertEqual(result["imported"], 1)
        verified = self.ledger.verify()
        self.assertEqual(verified["events"][0]["event_type"], "legacy_import")
        self.assertEqual(
            verified["events"][0]["details"]["trust"],
            "snapshot_at_migration_time_only",
        )

    def test_malformed_trailing_record_fails_closed(self):
        self.ledger.append("execution_applied", "exec_one", {})
        with (self.state / "ledger.jsonl").open("ab") as handle:
            handle.write(b'{"partial":')
        result = self.ledger.verify()
        self.assertFalse(result["success"])
        self.assertIn("incomplete trailing record", result["error"])


    def test_tail_truncation_is_detected_by_authenticated_head(self):
        self.ledger.append("execution_applied", "exec_one", {})
        self.ledger.append("validation_recorded", "exec_one", {})
        path = self.state / "ledger.jsonl"
        first_line = path.read_bytes().splitlines(keepends=True)[0]
        path.write_bytes(first_line)
        result = self.ledger.verify()
        self.assertFalse(result["success"])
        self.assertIn("do not match the authenticated head", result["error"])

    def test_head_checkpoint_tampering_is_detected(self):
        self.ledger.append("execution_applied", "exec_one", {})
        path = self.state / ".ledger.head"
        head = json.loads(path.read_text(encoding="utf-8"))
        head["sequence"] = 99
        path.write_text(json.dumps(head) + "\n", encoding="utf-8")
        result = self.ledger.verify()
        self.assertFalse(result["success"])
        self.assertIn("head checkpoint authentication failed", result["error"])


if __name__ == "__main__":
    unittest.main()
