import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lisa.projects import ProjectExecutor, ProjectOperation, ProjectRegistry, ProjectRequest
from lisa.projects.adaptation_planner import ProjectAdaptationPlanner
from lisa.projects.adaptation_request import ProjectAdaptationRequest
from lisa.projects.execution import ExecutionChange, ProjectExecutionRequest
from lisa.projects.execution_executor import ProjectExecutionExecutor
from lisa.projects.execution_history import ProjectExecutionHistory
from lisa.projects.execution_lifecycle import ProjectExecutionLifecycle


class TestProjectExecutionHistory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "source"
        self.target = root / "target"
        self.source.mkdir()
        self.target.mkdir()
        (self.source / "README.md").write_text("# Inventory stocktake capability", encoding="utf-8")
        (self.source / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
        (self.target / "README.md").write_text(
            "# Architecture\nCore must not depend on Feature. Money must use BigDecimal.",
            encoding="utf-8",
        )
        (self.target / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
        (self.target / "app").mkdir()
        original_inventory = "class Inventory { val version = 1 }\n"
        (self.target / "app" / "Inventory.kt").write_text(original_inventory, encoding="utf-8")
        self.registry = ProjectRegistry()
        manager = ProjectExecutor(self.registry)
        self.source_id = manager.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(self.source)
        )).manifest.project_id
        self.target_id = manager.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(self.target)
        )).manifest.project_id
        plan = ProjectAdaptationPlanner(self.registry).execute(ProjectAdaptationRequest(
            source_project_id=self.source_id, target_project_id=self.target_id,
            capability_query="inventory stocktake",
        )).plan
        self.plan = plan\n        self.state = root / "executions"
        self.executor = ProjectExecutionExecutor(self.registry, state_dir=self.state)
        change = ExecutionChange(
            "app/Inventory.kt", "class Inventory {}\n",
            hashlib.sha256(original_inventory.encode("utf-8")).hexdigest(),
        )
        digest = self.executor.approval_digest(plan, [change], self.target)
        self.execution = self.executor.execute(ProjectExecutionRequest(
            plan, (change,), f"APPLY {digest}"
        ))
        self.assertTrue(self.execution.success, self.execution.error)
        self.history = ProjectExecutionHistory(self.registry, state_dir=self.state)

    def test_history_lists_project_pair_and_lifecycle(self):
        records = self.history.list_history()
        self.assertEqual(len(records), 1)
        item = records[0]
        self.assertEqual(item["source_project_name"], "source")
        self.assertEqual(item["target_project_name"], "target")
        self.assertEqual(item["lifecycle_status"], "applied")
        self.assertEqual(item["file_count"], 1)
        self.assertEqual(item["integrity_status"], "consistent")
        self.assertEqual(item["ledger_status"], "locally_authenticated")

    def test_project_filter_matches_source_or_target(self):
        self.assertEqual(len(self.history.list_history(self.source_id)), 1)
        self.assertEqual(len(self.history.list_history(self.target_id)), 1)
        self.assertEqual(self.history.list_history("prj_missing"), [])

    def test_target_file_divergence_fails_verification(self):
        destination = self.target / "app" / "Inventory.kt"
        destination.write_text("changed after application", encoding="utf-8")
        result = self.history.verify(self.execution.execution_id)
        self.assertFalse(result["success"])
        self.assertIn("no longer matches the applied version", result["error"])

    def test_audit_manifest_tampering_fails_verification(self):
        audit_path = Path(self.execution.audit_path)
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["changed_files"][0]["after_sha256"] = "0" * 64
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        result = self.history.verify(self.execution.execution_id)
        self.assertFalse(result["success"])
        self.assertIn("changed since its latest trusted-ledger event", result["error"])

    def test_backup_tampering_fails_verification(self):
        backup = Path(self.execution.backup_directory) / "app" / "Inventory.kt"
        backup.write_text("tampered", encoding="utf-8")
        result = self.history.verify(self.execution.execution_id)
        self.assertFalse(result["success"])
        self.assertIn("Backup integrity check failed", result["error"])

    def test_malformed_audit_remains_visible_in_history(self):
        audit = Path(self.execution.audit_path)
        audit.write_text("{broken", encoding="utf-8")
        records = self.history.list_history()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["integrity_status"], "failed")

    def test_lifecycle_refuses_audit_changed_since_prior_ledger_snapshot(self):
        from lisa.projects.execution_ledger import ProjectExecutionLedger

        audit_path = Path(self.execution.audit_path)
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["created_at"] = "2026-01-01T00:00:00+00:00"
        audit_path.write_text(json.dumps(audit), encoding="utf-8")

        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state)
        with self.assertRaisesRegex(ValueError, "changed since its latest authenticated ledger snapshot"):
            lifecycle.preview_rollback_digest(self.execution.execution_id)

        ledger = ProjectExecutionLedger(self.state).verify()
        self.assertTrue(ledger["success"], ledger.get("error"))
        self.assertEqual(ledger["event_count"], 1)

    def test_legacy_snapshot_status_survives_later_validation_event(self):
        from lisa.projects.execution_ledger import ProjectExecutionLedger

        audit_bytes = Path(self.execution.audit_path).read_bytes()
        ledger = ProjectExecutionLedger(self.state)
        ledger.append("legacy_import", self.execution.execution_id, {
            "audit_sha256": hashlib.sha256(audit_bytes).hexdigest(),
            "trust": "snapshot_at_migration_time_only",
        })

        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state)
        digest = lifecycle.preview_validation_digest(
            self.execution.execution_id, "passed", "pytest -q", "migration check passed"
        )
        result = lifecycle.record_validation(
            self.execution.execution_id, "passed", "pytest -q",
            "migration check passed", f"RECORD {digest}",
        )
        self.assertTrue(result["success"], result.get("error"))

        verified = self.history.verify(self.execution.execution_id)
        self.assertTrue(verified["success"], verified.get("error"))
        self.assertEqual(verified["record"]["ledger_status"], "legacy_snapshot")

    def test_history_listing_verifies_ledger_once_and_reuses_event_index(self):
        from unittest.mock import patch
        from lisa.projects.execution_ledger import ProjectExecutionLedger

        change = ExecutionChange("app/Second.kt", "class Second {}\\n")
        digest = self.executor.approval_digest(self.plan, [change], self.target)
        second = self.executor.execute(ProjectExecutionRequest(
            self.plan, (change,), f"APPLY {digest}"
        ))
        self.assertTrue(second.success, second.error)

        original_verify = ProjectExecutionLedger.verify
        calls = 0

        def counted_verify(ledger):
            nonlocal calls
            calls += 1
            return original_verify(ledger)

        with patch.object(ProjectExecutionLedger, "verify", new=counted_verify):
            records = self.history.list_history()

        self.assertEqual(len(records), 2)
        self.assertEqual(calls, 1)

    def test_validation_evidence_hash_is_verified(self):
        report = self.target / "report.txt"
        report.write_text("all tests passed", encoding="utf-8")
        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state)
        digest = lifecycle.preview_validation_digest(
            self.execution.execution_id, "passed", "pytest -q", "all passed", "report.txt"
        )
        result = lifecycle.record_validation(
            self.execution.execution_id, "passed", "pytest -q", "all passed",
            f"RECORD {digest}", "report.txt",
        )
        self.assertTrue(result["success"], result.get("error"))
        verified = self.history.verify(self.execution.execution_id)
        self.assertTrue(verified["success"], verified.get("error"))
        self.assertEqual(verified["record"]["validation_integrity"], "verified")
        report.write_text("edited report", encoding="utf-8")
        tampered = self.history.verify(self.execution.execution_id)
        self.assertFalse(tampered["success"])
        self.assertIn("Validation evidence file hash", tampered["error"])

    def test_validation_record_tampering_fails_verification(self):
        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state)
        digest = lifecycle.preview_validation_digest(
            self.execution.execution_id, "passed", "pytest", "all passed"
        )
        result = lifecycle.record_validation(
            self.execution.execution_id, "passed", "pytest", "all passed", f"RECORD {digest}"
        )
        self.assertTrue(result["success"], result.get("error"))
        record_path = self.state / self.execution.execution_id / "validation.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["summary"] = "changed after approval"
        record_path.write_text(json.dumps(record), encoding="utf-8")
        verified = self.history.verify(self.execution.execution_id)
        self.assertFalse(verified["success"])
        self.assertIn("Validation record digest", verified["error"])

    def test_rollback_digest_and_restoration_manifest_are_verified(self):
        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state)
        digest = lifecycle.preview_rollback_digest(self.execution.execution_id)
        result = lifecycle.rollback(self.execution.execution_id, f"ROLLBACK {digest}")
        self.assertTrue(result["success"], result.get("error"))
        verified = self.history.verify(self.execution.execution_id)
        self.assertTrue(verified["success"], verified.get("error"))
        self.assertEqual(verified["record"]["lifecycle_status"], "rolled_back")


    def test_ledger_event_tampering_fails_execution_verification(self):
        ledger_path = self.state / "ledger.jsonl"
        event = json.loads(ledger_path.read_text(encoding="utf-8"))
        event["execution_id"] = "exec_forged"
        ledger_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        result = self.history.verify(self.execution.execution_id)
        self.assertFalse(result["success"])
        self.assertIn("Ledger authentication failed", result["error"])

    def test_legacy_execution_is_explicitly_unanchored_until_migrated(self):
        (self.state / "ledger.jsonl").unlink()
        (self.state / ".ledger.key").unlink()
        (self.state / ".ledger.head").unlink()
        unanchored = self.history.verify(self.execution.execution_id)
        self.assertTrue(unanchored["success"], unanchored.get("error"))
        self.assertEqual(unanchored["record"]["ledger_status"], "legacy_unanchored")

        from lisa.projects.execution_ledger import ProjectExecutionLedger
        migrated = ProjectExecutionLedger(self.state).migrate_legacy()
        self.assertTrue(migrated["success"], migrated.get("error"))
        self.assertEqual(migrated["imported"], 1)
        verified = self.history.verify(self.execution.execution_id)
        self.assertTrue(verified["success"], verified.get("error"))
        self.assertEqual(verified["record"]["ledger_status"], "legacy_snapshot")


if __name__ == "__main__":
    unittest.main()
