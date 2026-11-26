import hashlib
import json
import os
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

    def test_overlapping_source_and_target_roots_are_rejected(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        nested_target = self.source / "nested-target"
        nested_target.mkdir()

        def registered_project(project_id):
            if project_id == self.source_id:
                return SimpleNamespace(root_path=str(self.source))
            if project_id == self.target_id:
                return SimpleNamespace(root_path=str(nested_target))
            return None

        with patch.object(self.registry, "get", side_effect=registered_project):
            result = self.executor.execute(self.request([
                ExecutionChange("app/Unsafe.kt", "class Unsafe {}")
            ]))

        self.assertFalse(result.success)
        self.assertIn("must not overlap", result.error)
        self.assertFalse((nested_target / "app" / "Unsafe.kt").exists())

    def test_bind_mount_aliases_of_source_and_target_are_rejected(self):
        from pathlib import Path
        from unittest.mock import patch

        def mount_identity(path):
            if Path(path) == self.source.resolve():
                return ("8:1", Path("/workspace/project"))
            return ("8:1", Path("/workspace/project/subproject"))

        with patch.object(ProjectExecutionExecutor, "_mount_identity", side_effect=mount_identity):
            result = self.executor.execute(self.request([
                ExecutionChange("app/BindMountEscape.kt", "class Unsafe {}")
            ]))

        self.assertFalse(result.success)
        self.assertIn("must not overlap or alias", result.error)
        self.assertFalse((self.target / "app" / "BindMountEscape.kt").exists())

    def test_same_filesystem_non_overlapping_roots_remain_allowed(self):
        from pathlib import Path
        from unittest.mock import patch

        def mount_identity(path):
            if Path(path) == self.source.resolve():
                return ("8:1", Path("/workspace/source"))
            return ("8:1", Path("/workspace/target"))

        with patch.object(ProjectExecutionExecutor, "_mount_identity", side_effect=mount_identity):
            self.assertFalse(ProjectExecutionExecutor._filesystem_roots_overlap(
                self.source.resolve(), self.target.resolve()
            ))

    def test_existing_shared_state_directory_is_not_chmodded(self):
        if os.name != "posix":
            self.skipTest("POSIX permission bits are not portable to Windows")

        shared_state = self.source.parent / "shared-state"
        shared_state.mkdir()
        shared_state.chmod(0o755)
        executor = ProjectExecutionExecutor(self.registry, state_dir=shared_state)
        result = executor.execute(self.request([
            ExecutionChange("app/SharedState.kt", "class SharedState {}")
        ]))

        self.assertFalse(result.success)
        self.assertIn("Existing execution state directory is not private", result.error)
        self.assertEqual(shared_state.stat().st_mode & 0o777, 0o755)


    def test_existing_execution_state_directory_must_be_owned_by_current_user(self):
        if os.name != "posix":
            self.skipTest("POSIX ownership is not portable to Windows")
        from types import SimpleNamespace
        from unittest.mock import patch

        shared_state = self.source.parent / "foreign-owned-state"
        shared_state.mkdir()
        shared_state.chmod(0o700)
        original_stat = Path.stat

        def foreign_owner(path, *args, **kwargs):
            info = original_stat(path, *args, **kwargs)
            if path == shared_state:
                return SimpleNamespace(st_mode=info.st_mode, st_uid=os.geteuid() + 1)
            return info

        with patch.object(Path, "stat", new=foreign_owner):
            with self.assertRaisesRegex(ValueError, "not owned by the current user"):
                ProjectExecutionExecutor._ensure_private_directory(shared_state)

    def test_linux_mount_identity_unavailable_fails_closed(self):
        import sys
        from unittest.mock import patch

        if not sys.platform.startswith("linux"):
            self.skipTest("Linux mount identity policy is Linux-specific")

        with patch.object(ProjectExecutionExecutor, "_mount_identity", return_value=None):
            result = self.executor.execute(self.request([
                ExecutionChange("app/UnknownMount.kt", "class UnknownMount {}")
            ]))

        self.assertFalse(result.success)
        self.assertIn("Unable to verify Linux mount identities", result.error)
        self.assertFalse((self.target / "app" / "UnknownMount.kt").exists())

    def test_execution_state_bind_mount_alias_of_project_root_is_rejected(self):
        from pathlib import Path
        from unittest.mock import patch

        aliased_state = self.source / "private-state-alias"
        executor = ProjectExecutionExecutor(self.registry, state_dir=aliased_state)

        def overlaps(first, second):
            if Path(first) == aliased_state.resolve():
                return True
            return False

        with patch.object(ProjectExecutionExecutor, "_filesystem_roots_overlap", side_effect=overlaps):
            result = executor.execute(self.request([
                ExecutionChange("app/StateAlias.kt", "class StateAlias {}")
            ]))

        self.assertFalse(result.success)
        self.assertIn("outside the source project", result.error)
        self.assertFalse((self.target / "app" / "StateAlias.kt").exists())

    def test_backup_state_and_files_are_private_on_posix(self):
        if os.name != "posix":
            self.skipTest("POSIX permission bits are not portable to Windows")

        destination = self.target / "app" / "Main.kt"
        original = destination.read_bytes()
        expected = hashlib.sha256(original).hexdigest()
        result = self.executor.execute(self.request([
            ExecutionChange("app/Main.kt", "class Main { val private = true }\n", expected)
        ]))
        self.assertTrue(result.success, result.error)

        backup_dir = Path(result.backup_directory)
        backup_file = backup_dir / "app" / "Main.kt"
        self.assertEqual(os.stat(self.state_dir).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(backup_dir.parent).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(backup_dir).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(backup_file).st_mode & 0o777, 0o600)

    def test_successful_rollback_clears_replay_marker_and_allows_retry(self):
        from unittest.mock import patch

        destination = self.target / "app" / "Main.kt"
        original = destination.read_bytes()
        change = ExecutionChange(
            "app/Main.kt",
            "class Main { val retry = true }\n",
            hashlib.sha256(original).hexdigest(),
        )
        request = self.request([change])
        digest = self.executor.approval_digest(self.plan, [change], self.target)
        execution_dir = self.state_dir / ("exec_" + digest[:20])
        atomic_write = ProjectExecutionExecutor._atomic_write
        audit_failed = False

        def fail_audit_once(path, content, mode=None):
            nonlocal audit_failed
            if Path(path).name == "audit.json" and not audit_failed:
                audit_failed = True
                raise OSError("simulated audit write failure")
            return atomic_write(path, content, mode=mode)

        with patch.object(ProjectExecutionExecutor, "_atomic_write", side_effect=fail_audit_once):
            failed = self.executor.execute(request)

        self.assertFalse(failed.success)
        self.assertIn("simulated audit write failure", failed.error)
        self.assertEqual(destination.read_bytes(), original)
        self.assertFalse(execution_dir.exists())

        retried = self.executor.execute(request)
        self.assertTrue(retried.success, retried.error)

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


if __name__ == "__main__":
    unittest.main()
