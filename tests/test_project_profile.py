import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from dataclasses import is_dataclass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.projects import (
    ProjectExecutor, ProjectOperation, ProjectProfileExecutor,
    ProjectProfileRequest, ProjectRequest, ProjectRegistry,
)


class TestProjectProfile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.project = self.root / "sample_android"
        self.project.mkdir()
        (self.project / "README.md").write_text(
            "# Sample\nA demo project.\nAPI_KEY=should-not-leak",
            encoding="utf-8",
        )
        (self.project / "ARCHITECTURE.md").write_text(
            "# Architecture\nModules are isolated.", encoding="utf-8"
        )
        (self.project / "settings.gradle.kts").write_text(
            'include(":app")\n', encoding="utf-8"
        )
        app = self.project / "app"
        (app / "src" / "main" / "kotlin").mkdir(parents=True)
        (app / "build.gradle.kts").write_text(
            'plugins { id("com.android.application") }', encoding="utf-8"
        )
        (app / "src" / "main" / "kotlin" / "Main.kt").write_text(
            "class Main {}", encoding="utf-8"
        )
        (app / "src" / "main" / "AndroidManifest.xml").write_text(
            "<manifest />", encoding="utf-8"
        )
        (self.project / ".env").write_text("SECRET=value", encoding="utf-8")
        ignored = self.project / "build" / "generated"
        ignored.mkdir(parents=True)
        (ignored / "Generated.kt").write_text("class Generated {}", encoding="utf-8")

        self.registry = ProjectRegistry()
        registered = ProjectExecutor(registry=self.registry).execute(
            ProjectRequest(operation=ProjectOperation.REGISTER, path=str(self.project))
        )
        self.assertTrue(registered.success, registered.error)
        self.project_id = registered.manifest.project_id
        self.executor = ProjectProfileExecutor(registry=self.registry)

    def test_profile_captures_documents_descriptors_and_structure(self):
        result = self.executor.execute(ProjectProfileRequest(project_id=self.project_id))
        self.assertTrue(result.success, result.error)
        profile = result.profile
        evidence_paths = {item.relative_path for item in profile.evidence}
        self.assertIn("README.md", evidence_paths)
        self.assertIn("ARCHITECTURE.md", evidence_paths)
        self.assertIn("settings.gradle.kts", evidence_paths)
        self.assertIn("app/build.gradle.kts", evidence_paths)
        self.assertIn("app", profile.top_level_directories)
        self.assertEqual(profile.source_file_count, 1)
        self.assertIn("kotlin", profile.technologies)
        self.assertIn("android", profile.technologies)
        readme = next(item for item in profile.evidence if item.relative_path == "README.md")
        self.assertTrue(readme.redactions_applied)
        self.assertNotIn("should-not-leak", readme.excerpt)
        self.assertNotIn(".env", evidence_paths)
        self.assertNotIn("build/generated/Generated.kt", profile.source_files_sample)

    def test_profile_evidence_is_hashed_and_bounded(self):
        result = self.executor.execute(ProjectProfileRequest(
            project_id=self.project_id, max_bytes_per_file=1024
        ))
        self.assertTrue(result.success, result.error)
        readme = next(item for item in result.profile.evidence if item.relative_path == "README.md")
        expected = hashlib.sha256(
            b"# Sample\nA demo project.\nAPI_KEY=should-not-leak"
        ).hexdigest()
        self.assertEqual(readme.sha256, expected)
        self.assertFalse(readme.truncated)
        self.assertLessEqual(readme.bytes_inspected, 1024)

    def test_profile_is_deterministic_and_read_only(self):
        before = {
            path.relative_to(self.project).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.project.rglob("*") if path.is_file()
        }
        first = self.executor.execute(ProjectProfileRequest(project_id=self.project_id))
        second = self.executor.execute(ProjectProfileRequest(project_id=self.project_id))
        after = {
            path.relative_to(self.project).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.project.rglob("*") if path.is_file()
        }
        self.assertTrue(first.success, first.error)
        self.assertTrue(second.success, second.error)
        self.assertEqual(first.profile, second.profile)
        self.assertEqual(before, after)

    def test_profile_contracts_are_frozen_dataclasses(self):
        from lisa.projects import ProjectEvidence, ProjectProfile, ProjectProfileResult
        from lisa.projects.profile_request import ProjectProfileRequest
        for contract in (ProjectEvidence, ProjectProfile, ProjectProfileRequest, ProjectProfileResult):
            with self.subTest(contract=contract.__name__):
                self.assertTrue(is_dataclass(contract))
                self.assertTrue(contract.__dataclass_params__.frozen)

    def test_profile_rejects_unknown_project_and_invalid_limits(self):
        missing = self.executor.execute(ProjectProfileRequest(project_id="prj_missing"))
        invalid = self.executor.execute(ProjectProfileRequest(
            project_id=self.project_id, max_bytes_per_file=100
        ))
        self.assertFalse(missing.success)
        self.assertFalse(invalid.success)


if __name__ == "__main__":
    unittest.main()
