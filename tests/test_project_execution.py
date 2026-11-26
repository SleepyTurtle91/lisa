import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.projects import ProjectExecutor, ProjectOperation, ProjectRegistry, ProjectRequest
from lisa.projects.adaptation_planner import ProjectAdaptationPlanner
from lisa.projects.adaptation_request import ProjectAdaptationRequest
from lisa.projects.execution import ExecutionChange, ProjectExecutionRequest
from lisa.projects.execution_executor import ProjectExecutionExecutor
from lisa.projects.execution_lifecycle import ProjectExecutionLifecycle
from lisa.projects.execution_recovery import ProjectExecutionRecovery
from lisa.projects.execution_history import ProjectExecutionHistory


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


    def _simulate_interrupted_apply(self, changes, interrupt_path):
        request = self.request(changes)
        original_atomic_write = self.executor._atomic_write

        def interrupt_after_target_replace(path, data, mode=None):
            result = original_atomic_write(path, data, mode=mode)
            if Path(path) == interrupt_path:
                raise SystemExit("simulated process interruption")
            return result

        with mock.patch.object(self.executor, "_atomic_write", side_effect=interrupt_after_target_replace):
            with self.assertRaises(SystemExit):
                self.executor.execute(request)
        return "exec_" + self.executor.approval_digest(self.plan, changes, self.target)[:20]

    def test_interrupted_multi_file_apply_is_listed_and_explicitly_rolled_back(self):
        existing = self.target / "app" / "Main.kt"
        original = existing.read_bytes()
        changes = [
            ExecutionChange("app/Main.kt", "class Main { val changed = true }\\n", hashlib.sha256(original).hexdigest()),
            ExecutionChange("app/New.kt", "class New {}\\n"),
        ]
        execution_id = self._simulate_interrupted_apply(changes, existing)
        created = self.target / "app" / "New.kt"
        self.assertNotEqual(existing.read_bytes(), original)
        self.assertFalse(created.exists())

        recovery = ProjectExecutionRecovery(self.registry, state_dir=self.state_dir)
        pending = recovery.list_pending()
        self.assertEqual([item["execution_id"] for item in pending], [execution_id])
        digest = recovery.preview_digest(execution_id)
        refused = recovery.recover(execution_id, "RECOVER wrong")
        self.assertFalse(refused["success"])
        self.assertNotEqual(existing.read_bytes(), original)

        result = recovery.recover(execution_id, f"RECOVER {digest}")
        self.assertTrue(result["success"], result.get("error"))
        self.assertEqual(existing.read_bytes(), original)
        self.assertFalse(created.exists())
        self.assertEqual(result["restored_files"], ("app/Main.kt", "app/New.kt"))
        self.assertEqual(recovery.list_pending(), [])

        verified = ProjectExecutionHistory(self.registry, state_dir=self.state_dir).verify(execution_id)
        self.assertTrue(verified["success"], verified.get("error"))
        self.assertEqual(verified["record"]["lifecycle_status"], "rolled_back")
        self.assertEqual(verified["record"]["ledger_status"], "locally_authenticated")

    def test_interrupted_apply_refuses_unknown_later_file_without_partial_recovery(self):
        existing = self.target / "app" / "Main.kt"
        original = existing.read_bytes()
        changes = [
            ExecutionChange("app/Main.kt", "class Main { val changed = true }\\n", hashlib.sha256(original).hexdigest()),
            ExecutionChange("app/New.kt", "class New {}\\n"),
        ]
        execution_id = self._simulate_interrupted_apply(changes, existing)
        created = self.target / "app" / "New.kt"
        created.write_text("independent later change", encoding="utf-8")

        recovery = ProjectExecutionRecovery(self.registry, state_dir=self.state_dir)
        digest = recovery.preview_digest(execution_id)
        result = recovery.recover(execution_id, f"RECOVER {digest}")
        self.assertFalse(result["success"])
        self.assertIn("unknown version", result["error"])
        self.assertNotEqual(existing.read_bytes(), original)
        self.assertEqual(created.read_text(encoding="utf-8"), "independent later change")

    def test_successful_apply_keeps_completed_journal_and_history_consistent(self):
        execution = self._apply_for_lifecycle([
            ExecutionChange("app/Completed.kt", "class Completed {}\\n")
        ])
        journal_path = Path(execution.audit_path).parent / "execution.journal.json"
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        self.assertEqual(journal["status"], "completed")
        self.assertTrue(journal["files"][0]["applied"])
        history = ProjectExecutionHistory(self.registry, state_dir=self.state_dir)
        verified = history.verify(execution.execution_id)
        self.assertTrue(verified["success"], verified.get("error"))
        self.assertEqual(verified["record"]["lifecycle_status"], "applied")


    def test_recovery_can_resume_after_a_second_interruption(self):
        existing = self.target / "app" / "Main.kt"
        original = existing.read_bytes()
        changes = [
            ExecutionChange("app/Main.kt", "class Main { val changed = true }\\n", hashlib.sha256(original).hexdigest()),
            ExecutionChange("app/New.kt", "class New {}\\n"),
        ]
        execution_id = self._simulate_interrupted_apply(changes, existing)
        recovery = ProjectExecutionRecovery(self.registry, state_dir=self.state_dir)
        digest = recovery.preview_digest(execution_id)
        original_atomic_write = ProjectExecutionExecutor._atomic_write

        def interrupt_after_restore(path, data, mode=None):
            result = original_atomic_write(path, data, mode=mode)
            if Path(path) == existing:
                raise SystemExit("simulated interruption during recovery")
            return result

        with mock.patch.object(ProjectExecutionExecutor, "_atomic_write", side_effect=interrupt_after_restore):
            with self.assertRaises(SystemExit):
                recovery.recover(execution_id, f"RECOVER {digest}")

        self.assertEqual(existing.read_bytes(), original)
        self.assertIn(execution_id, [item["execution_id"] for item in recovery.list_pending()])
        retry_digest = recovery.preview_digest(execution_id)
        result = recovery.recover(execution_id, f"RECOVER {retry_digest}")
        self.assertTrue(result["success"], result.get("error"))
        self.assertEqual(existing.read_bytes(), original)
        self.assertFalse((self.target / "app" / "New.kt").exists())
        self.assertEqual(recovery.list_pending(), [])


    def test_recovery_removes_stale_lock_only_after_owner_pid_is_gone(self):
        existing = self.target / "app" / "Main.kt"
        original = existing.read_bytes()
        changes = [
            ExecutionChange("app/Main.kt", "class Main { val changed = true }\\n", hashlib.sha256(original).hexdigest())
        ]
        execution_id = self._simulate_interrupted_apply(changes, existing)
        recovery = ProjectExecutionRecovery(self.registry, state_dir=self.state_dir)
        digest = recovery.preview_digest(execution_id)
        lock = self.state_dir / execution_id / ".recovery.lock"
        lock.write_text("42424242", encoding="ascii")
        with mock.patch("os.kill", side_effect=ProcessLookupError):
            result = recovery.recover(execution_id, f"RECOVER {digest}")
        self.assertTrue(result["success"], result.get("error"))
        self.assertFalse(lock.exists())
        self.assertEqual(existing.read_bytes(), original)

    def test_recovery_refuses_permission_only_changes(self):
        existing = self.target / "app" / "Main.kt"
        original = existing.read_bytes()
        original_mode = existing.stat().st_mode & 0o777
        changes = [ExecutionChange(
            "app/Main.kt", "class Main { val changed = true }\\n",
            hashlib.sha256(original).hexdigest(),
        )]
        execution_id = self._simulate_interrupted_apply(changes, existing)
        existing.chmod(0o600 if original_mode != 0o600 else 0o644)

        recovery = ProjectExecutionRecovery(self.registry, state_dir=self.state_dir)
        digest = recovery.preview_digest(execution_id)
        result = recovery.recover(execution_id, f"RECOVER {digest}")
        self.assertFalse(result["success"])
        self.assertIn("permissions", result["error"].lower())
        self.assertEqual(existing.read_bytes(), changes[0].content.encode("utf-8"))

    def test_executor_rejects_symlinked_execution_state_root(self):
        real_state = self.state_dir
        real_state.mkdir()
        linked_state = self.state_dir.parent / "linked-lisa-state"
        linked_state.symlink_to(real_state, target_is_directory=True)
        executor = ProjectExecutionExecutor(self.registry, state_dir=linked_state)
        change = ExecutionChange("app/SymlinkState.kt", "class Safe {}\\n")
        digest = executor.approval_digest(self.plan, [change], self.target)
        result = executor.execute(ProjectExecutionRequest(
            plan=self.plan,
            changes=(change,),
            operator_confirmation=f"APPLY {digest}",
        ))
        self.assertFalse(result.success)
        self.assertIn("symlink", result.error.lower())
        self.assertFalse((self.target / "app" / "SymlinkState.kt").exists())

    def test_recovery_retry_after_ledger_event_commit_is_idempotent(self):
        existing = self.target / "app" / "Main.kt"
        original = existing.read_bytes()
        changes = [ExecutionChange(
            "app/Main.kt", "class Main { val changed = true }\\n",
            hashlib.sha256(original).hexdigest(),
        )]
        execution_id = self._simulate_interrupted_apply(changes, existing)
        recovery = ProjectExecutionRecovery(self.registry, state_dir=self.state_dir)
        digest = recovery.preview_digest(execution_id)
        from lisa.projects.execution_ledger import ProjectExecutionLedger
        append = ProjectExecutionLedger.append

        def append_then_interrupt(ledger, *args, **kwargs):
            append(ledger, *args, **kwargs)
            raise OSError("simulated interruption after durable ledger append")

        with mock.patch.object(ProjectExecutionLedger, "append", new=append_then_interrupt):
            first = recovery.recover(execution_id, f"RECOVER {digest}")
        self.assertFalse(first["success"])
        self.assertEqual(existing.read_bytes(), original)
        self.assertIn(execution_id, [item["execution_id"] for item in recovery.list_pending()])

        retry_digest = recovery.preview_digest(execution_id)
        second = recovery.recover(execution_id, f"RECOVER {retry_digest}")
        self.assertTrue(second["success"], second.get("error"))
        verified = ProjectExecutionHistory(self.registry, state_dir=self.state_dir).verify(execution_id)
        self.assertTrue(verified["success"], verified.get("error"))
        recovered_events = [
            event for event in ProjectExecutionLedger(self.state_dir).verify()["events"]
            if event.get("execution_id") == execution_id
            and event.get("event_type") == "execution_recovered"
        ]
        self.assertEqual(len(recovered_events), 1)

    def test_recovery_refuses_live_lock_owner(self):
        existing = self.target / "app" / "Main.kt"
        original = existing.read_bytes()
        changes = [
            ExecutionChange("app/Main.kt", "class Main { val changed = true }\\n", hashlib.sha256(original).hexdigest())
        ]
        execution_id = self._simulate_interrupted_apply(changes, existing)
        recovery = ProjectExecutionRecovery(self.registry, state_dir=self.state_dir)
        digest = recovery.preview_digest(execution_id)
        lock = self.state_dir / execution_id / ".recovery.lock"
        lock.write_text("42424242", encoding="ascii")
        with mock.patch("os.kill", return_value=None):
            result = recovery.recover(execution_id, f"RECOVER {digest}")
        self.assertFalse(result["success"])
        self.assertIn("active in process", result["error"])
        self.assertTrue(lock.exists())
        self.assertNotEqual(existing.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
