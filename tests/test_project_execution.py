import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.projects import ProjectExecutor, ProjectOperation, ProjectRegistry, ProjectRequest
from lisa.projects.adaptation_planner import ProjectAdaptationPlanner
from lisa.projects.adaptation_request import ProjectAdaptationRequest
from lisa.projects.execution import ExecutionChange, ProjectExecutionRequest
from lisa.projects.execution_executor import ProjectExecutionExecutor
from lisa.projects.execution_lifecycle import ProjectExecutionLifecycle


class TestGovernedProjectExecution(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.registry = ProjectRegistry()
        register = ProjectExecutor(registry=self.registry)

        self.source = root / "source"
        self.source.mkdir()
        (self.source / "README.md").write_text(
            "# Inventory\nInventory supports stocktake and stock adjustments.",
            encoding="utf-8",
        )
        (self.source / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
        (self.source / "app").mkdir()
        (self.source / "app" / "Inventory.kt").write_text("class Inventory {}", encoding="utf-8")

        self.target = root / "target"
        self.target.mkdir()
        (self.target / "README.md").write_text(
            "# Architecture\nCore must not depend on Feature. Money must use BigDecimal.",
            encoding="utf-8",
        )
        (self.target / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
        (self.target / "app").mkdir()
        (self.target / "app" / "Main.kt").write_text("class Main {}", encoding="utf-8")

        self.source_id = register.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(self.source)
        )).manifest.project_id
        self.target_id = register.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(self.target)
        )).manifest.project_id
        self.plan = ProjectAdaptationPlanner(registry=self.registry).execute(
            ProjectAdaptationRequest(
                source_project_id=self.source_id,
                target_project_id=self.target_id,
                capability_query="inventory stocktake",
            )
        ).plan
        self.state_dir = root / "lisa-state"
        self.executor = ProjectExecutionExecutor(self.registry, state_dir=self.state_dir)

    def request(self, changes, confirmation=None):
        digest = self.executor.approval_digest(self.plan, changes, self.target)
        return ProjectExecutionRequest(
            plan=self.plan,
            changes=tuple(changes),
            operator_confirmation=confirmation if confirmation is not None else f"APPLY {digest}",
        )

    def test_exact_approval_applies_scoped_change_and_writes_backup_and_audit(self):
        change = ExecutionChange("app/Reuse.kt", "class Reuse {}\n")
        request = self.request([change])
        result = self.executor.execute(request)

        self.assertTrue(result.success, result.error)
        self.assertEqual(result.changed_files, ("app/Reuse.kt",))
        self.assertEqual((self.target / "app" / "Reuse.kt").read_text(), "class Reuse {}\n")
        audit = json.loads(Path(result.audit_path).read_text(encoding="utf-8"))
        self.assertEqual(audit["validation"]["status"], "required_not_run")
        self.assertEqual(audit["target_project_id"], self.target_id)
        self.assertTrue(Path(result.backup_directory).is_dir())

    def test_wrong_confirmation_does_not_modify_target(self):
        destination = self.target / "app" / "Reuse.kt"
        result = self.executor.execute(self.request(
            [ExecutionChange("app/Reuse.kt", "class Reuse {}\n")],
            confirmation="yes",
        ))
        self.assertFalse(result.success)
        self.assertFalse(destination.exists())

    def test_existing_file_requires_matching_precondition_and_is_backed_up(self):
        destination = self.target / "app" / "Main.kt"
        original = destination.read_bytes()
        expected = hashlib.sha256(original).hexdigest()
        result = self.executor.execute(self.request([
            ExecutionChange("app/Main.kt", "class Main { val safe = true }\n", expected)
        ]))
        self.assertTrue(result.success, result.error)
        backup = Path(result.backup_directory) / "app" / "Main.kt"
        self.assertEqual(backup.read_bytes(), original)
        self.assertNotEqual(destination.read_bytes(), original)

    def test_stale_hash_is_rejected(self):
        destination = self.target / "app" / "Main.kt"
        original = destination.read_bytes()
        result = self.executor.execute(self.request([
            ExecutionChange("app/Main.kt", "changed", "0" * 64)
        ]))
        self.assertFalse(result.success)
        self.assertEqual(destination.read_bytes(), original)

    def test_path_traversal_and_protected_paths_are_rejected(self):
        for path in ("../outside.txt", ".git/config", ".lisa/registry.json", "/tmp/outside.txt"):
            with self.subTest(path=path):
                result = self.executor.execute(self.request([ExecutionChange(path, "bad")]))
                self.assertFalse(result.success)

    def test_symlink_destination_is_rejected(self):
        outside = self.source / "outside.txt"
        outside.write_text("untouched", encoding="utf-8")
        link = self.target / "app" / "linked.txt"
        link.symlink_to(outside)
        result = self.executor.execute(self.request([ExecutionChange("app/linked.txt", "overwritten")]))
        self.assertFalse(result.success)
        self.assertEqual(outside.read_text(encoding="utf-8"), "untouched")

    def test_duplicate_paths_are_rejected(self):
        result = self.executor.execute(self.request([
            ExecutionChange("app/New.kt", "one"),
            ExecutionChange("app/New.kt", "two"),
        ]))
        self.assertFalse(result.success)
        self.assertFalse((self.target / "app" / "New.kt").exists())

    def test_execution_is_not_replayed(self):
        request = self.request([ExecutionChange("app/Once.kt", "class Once {}")])
        first = self.executor.execute(request)
        second = self.executor.execute(request)
        self.assertTrue(first.success, first.error)
        self.assertFalse(second.success)
        self.assertIn("already been executed", second.error)

    def test_execution_does_not_run_project_commands(self):
        result = self.executor.execute(self.request([
            ExecutionChange("app/NeedsTests.kt", "class NeedsTests {}")
        ]))
        self.assertTrue(result.success, result.error)
        audit = json.loads(Path(result.audit_path).read_text(encoding="utf-8"))
        self.assertEqual(audit["validation"]["status"], "required_not_run")
        self.assertTrue(result.validation_required)


    def test_changed_source_evidence_invalidates_plan(self):
        (self.source / "README.md").write_text(
            "# Inventory\nThe original capability description has changed.",
            encoding="utf-8",
        )
        result = self.executor.execute(self.request([
            ExecutionChange("app/Stale.kt", "class Stale {}")
        ]))
        self.assertFalse(result.success)
        self.assertIn("evidence changed since planning", result.error)
        self.assertFalse((self.target / "app" / "Stale.kt").exists())

    def test_changed_target_constraints_invalidate_plan(self):
        (self.target / "README.md").write_text(
            "# Changed architecture\nCore may depend on Feature.",
            encoding="utf-8",
        )
        result = self.executor.execute(self.request([
            ExecutionChange("app/Stale.kt", "class Stale {}")
        ]))
        self.assertFalse(result.success)
        self.assertIn("evidence changed since planning", result.error)
        self.assertFalse((self.target / "app" / "Stale.kt").exists())


    def _apply_for_lifecycle(self, changes):
        result = self.executor.execute(self.request(changes))
        self.assertTrue(result.success, result.error)
        return result

    def test_rollback_restores_existing_file_and_removes_created_file(self):
        existing = self.target / "app" / "Main.kt"
        original = existing.read_bytes()
        mode = existing.stat().st_mode & 0o777
        changes = [
            ExecutionChange("app/Main.kt", "class Main { val changed = true }\n", hashlib.sha256(original).hexdigest()),
            ExecutionChange("app/New.kt", "class New {}\n"),
        ]
        execution = self._apply_for_lifecycle(changes)
        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state_dir)
        digest = lifecycle.preview_rollback_digest(execution.execution_id)
        result = lifecycle.rollback(execution.execution_id, f"ROLLBACK {digest}")
        self.assertTrue(result["success"], result.get("error"))
        self.assertEqual(existing.read_bytes(), original)
        self.assertEqual(existing.stat().st_mode & 0o777, mode)
        self.assertFalse((self.target / "app" / "New.kt").exists())
        audit = json.loads(Path(execution.audit_path).read_text(encoding="utf-8"))
        self.assertEqual(audit["lifecycle"]["status"], "rolled_back")

    def test_rollback_rejects_non_regular_object_at_created_file_path(self):
        execution = self._apply_for_lifecycle([
            ExecutionChange("app/Created.kt", "class Created {}\n")
        ])
        destination = self.target / "app" / "Created.kt"
        destination.unlink()
        destination.mkdir()

        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state_dir)
        digest = lifecycle.preview_rollback_digest(execution.execution_id)
        result = lifecycle.rollback(execution.execution_id, f"ROLLBACK {digest}")

        self.assertFalse(result["success"])
        self.assertIn("non-regular", result["error"])
        self.assertTrue(destination.is_dir())
        audit = json.loads(Path(execution.audit_path).read_text(encoding="utf-8"))
        self.assertEqual(audit["lifecycle"]["status"], "rollback_in_progress")

    def test_rollback_rechecks_target_after_preflight_before_restore(self):
        execution = self._apply_for_lifecycle([
            ExecutionChange("app/Raced.kt", "class Raced {}\n")
        ])
        destination = self.target / "app" / "Raced.kt"
        audit_path = Path(execution.audit_path)
        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state_dir)
        digest = lifecycle.preview_rollback_digest(execution.execution_id)
        original_atomic_write = lifecycle._atomic_write
        changed = False

        def mutate_after_rollback_journal(path, content):
            nonlocal changed
            result = original_atomic_write(path, content)
            if Path(path) == audit_path and not changed:
                changed = True
                destination.write_text("independent concurrent edit", encoding="utf-8")
            return result

        from unittest.mock import patch
        with patch.object(lifecycle, "_atomic_write", side_effect=mutate_after_rollback_journal):
            result = lifecycle.rollback(execution.execution_id, f"ROLLBACK {digest}")

        self.assertFalse(result["success"])
        self.assertIn("changed during rollback", result["error"])
        self.assertEqual(destination.read_text(encoding="utf-8"), "independent concurrent edit")

    def test_rollback_restores_mode_when_original_bytes_are_already_present(self):
        destination = self.target / "app" / "Main.kt"
        original = destination.read_bytes()
        destination.chmod(0o600)
        original_mode = destination.stat().st_mode & 0o777
        expected = hashlib.sha256(original).hexdigest()
        execution = self._apply_for_lifecycle([
            ExecutionChange("app/Main.kt", "class Main { val changed = true }\n", expected)
        ])

        destination.write_bytes(original)
        destination.chmod(0o644)
        self.assertEqual(destination.read_bytes(), original)
        self.assertNotEqual(destination.stat().st_mode & 0o777, original_mode)

        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state_dir)
        digest = lifecycle.preview_rollback_digest(execution.execution_id)
        result = lifecycle.rollback(execution.execution_id, f"ROLLBACK {digest}")

        self.assertTrue(result["success"], result.get("error"))
        self.assertEqual(destination.read_bytes(), original)
        self.assertEqual(destination.stat().st_mode & 0o777, original_mode)

    def test_rollback_refuses_files_changed_after_execution(self):
        execution = self._apply_for_lifecycle([
            ExecutionChange("app/Changed.kt", "class Changed {}\n")
        ])
        destination = self.target / "app" / "Changed.kt"
        destination.write_text("someone else's change", encoding="utf-8")
        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state_dir)
        digest = lifecycle.preview_rollback_digest(execution.execution_id)
        result = lifecycle.rollback(execution.execution_id, f"ROLLBACK {digest}")
        self.assertFalse(result["success"])
        self.assertIn("changed since execution", result["error"])
        self.assertEqual(destination.read_text(encoding="utf-8"), "someone else's change")

    def test_validation_record_is_bound_and_explicitly_operator_reported(self):
        execution = self._apply_for_lifecycle([
            ExecutionChange("app/Validated.kt", "class Validated {}\n")
        ])
        (self.target / "reports").mkdir()
        report = self.target / "reports" / "test-results.txt"
        report.write_text("159 tests passed", encoding="utf-8")
        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state_dir)
        digest = lifecycle.preview_validation_digest(
            execution.execution_id, "passed", "./gradlew test",
            "159 tests passed", "reports/test-results.txt",
        )
        result = lifecycle.record_validation(
            execution.execution_id, "passed", "./gradlew test",
            "159 tests passed", f"RECORD {digest}", "reports/test-results.txt",
        )
        self.assertTrue(result["success"], result.get("error"))
        self.assertEqual(result["status"], "operator_reported_passed")
        record = json.loads(Path(result["validation_path"]).read_text(encoding="utf-8"))
        self.assertEqual(record["verification_method"].split(";")[0], "operator_attestation")
        self.assertEqual(record["evidence"]["sha256"], hashlib.sha256(report.read_bytes()).hexdigest())

    def test_validation_record_refuses_modified_target(self):
        execution = self._apply_for_lifecycle([
            ExecutionChange("app/Validated.kt", "class Validated {}\n")
        ])
        (self.target / "app" / "Validated.kt").write_text("modified after execution", encoding="utf-8")
        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state_dir)
        digest = lifecycle.preview_validation_digest(
            execution.execution_id, "passed", "pytest", "all passed"
        )
        result = lifecycle.record_validation(
            execution.execution_id, "passed", "pytest", "all passed", f"RECORD {digest}"
        )
        self.assertFalse(result["success"])
        self.assertIn("changed before validation capture", result["error"])

    def test_validation_cannot_be_recorded_after_rollback(self):
        execution = self._apply_for_lifecycle([
            ExecutionChange("app/Validated.kt", "class Validated {}\n")
        ])
        lifecycle = ProjectExecutionLifecycle(self.registry, state_dir=self.state_dir)
        rollback_digest = lifecycle.preview_rollback_digest(execution.execution_id)
        self.assertTrue(lifecycle.rollback(
            execution.execution_id, f"ROLLBACK {rollback_digest}"
        )["success"])
        digest = lifecycle.preview_validation_digest(
            execution.execution_id, "passed", "pytest", "all passed"
        )
        result = lifecycle.record_validation(
            execution.execution_id, "passed", "pytest", "all passed", f"RECORD {digest}"
        )
        self.assertFalse(result["success"])
        self.assertIn("not rolled-back", result["error"])


if __name__ == "__main__":
    unittest.main()
