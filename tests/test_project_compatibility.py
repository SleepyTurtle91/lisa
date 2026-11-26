import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.projects import ProjectExecutor, ProjectOperation, ProjectRegistry, ProjectRequest
from lisa.projects.compatibility import CompatibilityStatus
from lisa.projects.compatibility_executor import ProjectCompatibilityExecutor
from lisa.projects.compatibility_request import ProjectCompatibilityRequest


class TestProjectCompatibility(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.registry = ProjectRegistry()
        self.register = ProjectExecutor(registry=self.registry)

        self.source = self.root / "source_pos"
        self.source.mkdir()
        (self.source / "README.md").write_text(
            "# Inventory\nInventory supports stocktake and offline-first operation.",
            encoding="utf-8",
        )
        (self.source / "settings.gradle.kts").write_text(
            'include(":app")\n', encoding="utf-8"
        )
        (self.source / "app").mkdir()
        (self.source / "app" / "Main.kt").write_text("class Main {}", encoding="utf-8")

        self.target = self.root / "target_pos"
        self.target.mkdir()
        (self.target / "README.md").write_text(
            "# Target\nArchitecture: Core must not depend on Feature. Financial values must use BigDecimal.",
            encoding="utf-8",
        )
        (self.target / "settings.gradle.kts").write_text(
            'include(":app")\n', encoding="utf-8"
        )
        (self.target / "app").mkdir()
        (self.target / "app" / "Target.kt").write_text("class Target {}", encoding="utf-8")

        self.source_id = self.register.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(self.source)
        )).manifest.project_id
        self.target_id = self.register.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(self.target)
        )).manifest.project_id
        self.executor = ProjectCompatibilityExecutor(registry=self.registry)

    def test_reports_shared_stack_and_preserves_target_constraints(self):
        result = self.executor.execute(ProjectCompatibilityRequest(
            source_project_id=self.source_id,
            target_project_id=self.target_id,
            capability_query="inventory stocktake",
        ))
        self.assertTrue(result.success, result.error)
        report = result.report
        self.assertEqual(report.status, CompatibilityStatus.POTENTIAL_REUSE)
        self.assertIn("kotlin", report.shared_technologies)
        self.assertTrue(report.source_capability_found)
        self.assertTrue(any(
            item.project_role == "target" and "Core must not depend on Feature" in item.excerpt
            for item in report.constraints
        ))
        self.assertTrue(any("BigDecimal" in item.excerpt for item in report.constraints))
        self.assertTrue(any("No files were copied" in item for item in report.notes))

    def test_missing_source_capability_forces_insufficient_evidence(self):
        result = self.executor.execute(ProjectCompatibilityRequest(
            source_project_id=self.source_id,
            target_project_id=self.target_id,
            capability_query="kitchen dispatch",
        ))
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.report.status, CompatibilityStatus.INSUFFICIENT_EVIDENCE)
        self.assertFalse(result.report.source_capability_found)

    def test_compatibility_contracts_are_frozen_dataclasses(self):
        from dataclasses import is_dataclass
        from lisa.projects.compatibility import ProjectCompatibilityReport, ProjectConstraint
        from lisa.projects.compatibility_result import ProjectCompatibilityResult
        for contract in (
            ProjectCompatibilityRequest, ProjectCompatibilityReport,
            ProjectConstraint, ProjectCompatibilityResult,
        ):
            with self.subTest(contract=contract.__name__):
                self.assertTrue(is_dataclass(contract))
                self.assertTrue(contract.__dataclass_params__.frozen)

    def test_unknown_project_and_same_project_are_rejected(self):
        unknown = self.executor.execute(ProjectCompatibilityRequest(
            source_project_id=self.source_id,
            target_project_id="prj_missing",
        ))
        same = self.executor.execute(ProjectCompatibilityRequest(
            source_project_id=self.source_id,
            target_project_id=self.source_id,
        ))
        self.assertFalse(unknown.success)
        self.assertFalse(same.success)


if __name__ == "__main__":
    unittest.main()
