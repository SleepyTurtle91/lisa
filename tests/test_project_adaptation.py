import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.projects import ProjectExecutor, ProjectOperation, ProjectRegistry, ProjectRequest
from lisa.projects.adaptation import AdaptationPlanStatus
from lisa.projects.adaptation_planner import ProjectAdaptationPlanner
from lisa.projects.adaptation_request import ProjectAdaptationRequest


class TestProjectAdaptationPlanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.registry = ProjectRegistry()
        register = ProjectExecutor(registry=self.registry)

        self.source = root / "source"
        self.source.mkdir()
        (self.source / "README.md").write_text(
            "# Inventory\nInventory supports stocktake.",
            encoding="utf-8",
        )
        (self.source / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
        (self.source / "app").mkdir()
        (self.source / "app" / "Main.kt").write_text("class Main {}", encoding="utf-8")

        self.target = root / "target"
        self.target.mkdir()
        (self.target / "README.md").write_text(
            "# Architecture\nCore must not depend on Feature. Money must use BigDecimal.",
            encoding="utf-8",
        )
        (self.target / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
        (self.target / "app").mkdir()
        (self.target / "app" / "Target.kt").write_text("class Target {}", encoding="utf-8")

        self.source_id = register.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(self.source)
        )).manifest.project_id
        self.target_id = register.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(self.target)
        )).manifest.project_id
        self.planner = ProjectAdaptationPlanner(registry=self.registry)

    def test_creates_review_only_plan_with_target_constraints(self):
        request = ProjectAdaptationRequest(
            source_project_id=self.source_id,
            target_project_id=self.target_id,
            capability_query="inventory stocktake",
        )
        first = self.planner.execute(request)
        second = self.planner.execute(request)
        self.assertTrue(first.success, first.error)
        self.assertEqual(first.plan.status, AdaptationPlanStatus.READY_FOR_REVIEW)
        self.assertEqual(first.plan.plan_id, second.plan.plan_id)
        self.assertTrue(first.plan.authorization_required)
        self.assertFalse(first.plan.execution_authorized)
        self.assertIn("kotlin", first.plan.shared_technologies)
        self.assertEqual(first.plan.compatibility_status.value, "potential_reuse")
        self.assertTrue(any(item.relative_path == "README.md" for item in first.plan.source_evidence))
        self.assertTrue(any("Core must not depend on Feature" in c.excerpt for c in first.plan.target_constraints))
        self.assertEqual(len(first.plan.steps), 6)

    def test_missing_capability_blocks_plan(self):
        result = self.planner.execute(ProjectAdaptationRequest(
            source_project_id=self.source_id,
            target_project_id=self.target_id,
            capability_query="kitchen dispatch",
        ))
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.plan.status, AdaptationPlanStatus.BLOCKED)
        self.assertFalse(result.plan.execution_authorized)
        self.assertTrue(result.plan.blockers)

    def test_plan_is_blocked_without_target_constraints(self):
        target = Path(self.temp_dir.name) / "target_without_rules"
        target.mkdir()
        (target / "README.md").write_text("# Target\nA basic application.", encoding="utf-8")
        (target / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
        target_id = ProjectExecutor(registry=self.registry).execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(target)
        )).manifest.project_id
        result = self.planner.execute(ProjectAdaptationRequest(
            source_project_id=self.source_id,
            target_project_id=target_id,
            capability_query="inventory stocktake",
        ))
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.plan.status, AdaptationPlanStatus.BLOCKED)
        self.assertTrue(any("target architecture" in item.lower() for item in result.plan.blockers))

    def test_empty_query_is_rejected(self):
        result = self.planner.execute(ProjectAdaptationRequest(
            source_project_id=self.source_id,
            target_project_id=self.target_id,
            capability_query=" ",
        ))
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
