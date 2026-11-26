import tempfile
import unittest
import sys
from pathlib import Path
from dataclasses import is_dataclass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.projects import ProjectExecutor, ProjectOperation, ProjectRequest
from lisa.projects.registry import ProjectRegistry


class TestProjectRegistry(unittest.TestCase):
    def setUp(self):
        self.executor = ProjectExecutor()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def make_project(self, name, marker="README.md"):
        project = self.root / name
        project.mkdir()
        (project / marker).write_text(f"# {name}\n", encoding="utf-8")
        return project

    def register(self, path):
        return self.executor.execute(
            ProjectRequest(operation=ProjectOperation.REGISTER, path=str(path))
        )

    def test_project_contracts_are_frozen_dataclasses(self):
        from lisa.projects import ProjectContext, ProjectManifest, ProjectRequest, ProjectResult
        for contract in (ProjectContext, ProjectManifest, ProjectRequest, ProjectResult):
            with self.subTest(contract=contract.__name__):
                self.assertTrue(is_dataclass(contract))
                self.assertTrue(contract.__dataclass_params__.frozen)
                custom_methods = [
                    name for name in dir(contract)
                    if not name.startswith("__") and callable(getattr(contract, name))
                ]
                self.assertEqual(custom_methods, [])

    def test_registers_project_with_canonical_identity(self):
        project = self.make_project("flashpos", "settings.gradle.kts")
        result = self.register(project)
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.manifest.name, "flashpos")
        self.assertEqual(result.manifest.root_path, str(project.resolve()))
        self.assertIn("gradle", result.manifest.capabilities)
        self.assertIn("kotlin", result.manifest.capabilities)
        self.assertNotIn("java", result.manifest.capabilities)
        self.assertTrue(result.manifest.project_id.startswith("prj_"))

    def test_cmake_and_makefile_are_valid_project_markers(self):
        from lisa.projects.resolver import ProjectResolver

        for marker in ("CMakeLists.txt", "Makefile"):
            with self.subTest(marker=marker):
                project = self.root / marker.replace(".", "_")
                project.mkdir()
                (project / marker).write_text("# build descriptor\\n", encoding="utf-8")
                manifest = ProjectResolver().resolve(str(project))
                self.assertIn(marker, manifest.markers)

    def test_git_marker_does_not_become_a_technology(self):
        from lisa.projects.resolver import ProjectResolver

        project = self.root / "git_only"
        project.mkdir()
        (project / ".git").write_text("gitdir: metadata\\n", encoding="utf-8")
        manifest = ProjectResolver().resolve(str(project))
        self.assertIn(".git", manifest.markers)
        self.assertNotIn("git", manifest.capabilities)

    def test_registration_is_idempotent_for_same_project(self):
        project = self.make_project("extropos")
        first = self.register(project)
        second = self.register(project)
        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(first.manifest.project_id, second.manifest.project_id)
        listed = self.executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
        self.assertEqual(len(listed.manifests), 1)

    def test_rejects_missing_or_non_project_directories(self):
        missing = self.register(self.root / "missing")
        ordinary = self.root / "ordinary"
        ordinary.mkdir()
        unmarked = self.register(ordinary)
        self.assertFalse(missing.success)
        self.assertFalse(unmarked.success)
        self.assertIn("recognized project marker", unmarked.error)

    def test_projects_have_separate_contexts_and_only_one_active(self):
        first = self.register(self.make_project("source", "pyproject.toml"))
        second = self.register(self.make_project("target", "pubspec.yaml"))
        source_context = self.executor.execute(
            ProjectRequest(operation=ProjectOperation.ACTIVATE, project_id=first.manifest.project_id)
        ).context
        self.assertEqual(source_context.project_id, first.manifest.project_id)
        target_context = self.executor.execute(
            ProjectRequest(operation=ProjectOperation.ACTIVATE, project_id=second.manifest.project_id)
        ).context
        self.assertEqual(target_context.project_id, second.manifest.project_id)
        listed = self.executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
        self.assertEqual(listed.context, target_context)
        self.assertEqual(len(listed.manifests), 2)

    def test_unregistering_active_project_clears_active_context(self):
        registered = self.register(self.make_project("active"))
        project_id = registered.manifest.project_id
        activated = self.executor.execute(
            ProjectRequest(operation=ProjectOperation.ACTIVATE, project_id=project_id)
        )
        self.assertTrue(activated.success)
        removed = self.executor.execute(
            ProjectRequest(operation=ProjectOperation.UNREGISTER, project_id=project_id)
        )
        listed = self.executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
        self.assertTrue(removed.success)
        self.assertIsNone(listed.context)
        self.assertEqual(listed.manifests, ())

    def test_unknown_project_cannot_be_activated(self):
        result = self.executor.execute(
            ProjectRequest(operation=ProjectOperation.ACTIVATE, project_id="prj_unknown")
        )
        self.assertFalse(result.success)
        self.assertIn("not registered", result.error.lower())


    def test_registry_persists_projects_and_active_context(self):
        project = self.make_project("persisted", "pyproject.toml")
        registered = self.register(project)
        project_id = registered.manifest.project_id
        storage = self.root / "registry.json"
        persistent = ProjectExecutor(registry=ProjectRegistry(storage_path=storage))
        added = persistent.execute(
            ProjectRequest(operation=ProjectOperation.REGISTER, path=str(project))
        )
        self.assertTrue(added.success, added.error)
        activated = persistent.execute(
            ProjectRequest(operation=ProjectOperation.ACTIVATE, project_id=project_id)
        )
        self.assertTrue(activated.success, activated.error)

        reloaded = ProjectRegistry(storage_path=storage)
        self.assertEqual(reloaded.get(project_id).name, "persisted")
        self.assertEqual(reloaded.active_context().project_id, project_id)

    def test_corrupt_registry_fails_closed(self):
        storage = self.root / "corrupt.json"
        storage.write_text("{not valid json", encoding="utf-8")
        with self.assertRaises(ValueError):
            ProjectRegistry(storage_path=storage)

    def test_failed_persistence_rolls_back_registration(self):
        from lisa.projects.registry import ProjectRegistry
        blocker = self.root / "not-a-directory"
        blocker.write_text("file", encoding="utf-8")
        registry = ProjectRegistry(storage_path=blocker / "projects.json")
        project = self.make_project("rollback")
        manifest = self.register(project).manifest
        with self.assertRaises(OSError):
            registry.register(manifest)
        self.assertIsNone(registry.get(manifest.project_id))

    def test_failed_persistence_rolls_back_registration(self):
        blocker = self.root / "not-a-directory"
        blocker.write_text("file", encoding="utf-8")
        registry = ProjectRegistry(storage_path=blocker / "projects.json")
        project = self.make_project("rollback")
        manifest = self.register(project).manifest
        with self.assertRaises(OSError):
            registry.register(manifest)
        self.assertIsNone(registry.get(manifest.project_id))

    def test_activation_rejects_project_that_has_disappeared(self):
        project = self.make_project("vanishing")
        registered = self.register(project)
        (project / "README.md").unlink()
        project.rmdir()
        result = self.executor.execute(
            ProjectRequest(
                operation=ProjectOperation.ACTIVATE,
                project_id=registered.manifest.project_id,
            )
        )
        self.assertFalse(result.success)
        self.assertIn("no longer available", result.error)


if __name__ == "__main__":
    unittest.main()
