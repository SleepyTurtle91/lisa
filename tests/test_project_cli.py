import tempfile
import unittest
import io
from contextlib import redirect_stdout
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.cli import main as lisa_main


class TestProjectCLI(unittest.TestCase):
    def _with_registry(self, root):
        original = lisa_main.PROJECT_REGISTRY_PATH
        lisa_main.PROJECT_REGISTRY_PATH = root / ".lisa" / "projects.json"
        return original

    def test_project_find_command_prints_evidence_backed_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "Inventory App"
            project.mkdir()
            (project / "README.md").write_text(
                "# Inventory\nInventory management supports stocktake.",
                encoding="utf-8",
            )
            original_path = self._with_registry(root)
            try:
                lisa_main.run_project_command(["add", str(project)])
                output = io.StringIO()
                with redirect_stdout(output):
                    lisa_main.run_project_command(["find", "inventory", "stocktake"])
                self.assertIn("Inventory App", output.getvalue())
                self.assertIn("README.md", output.getvalue())
            finally:
                lisa_main.PROJECT_REGISTRY_PATH = original_path

    def test_project_compare_command_prints_compatibility_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "Source"
            target = root / "Target"
            source.mkdir()
            target.mkdir()
            (source / "README.md").write_text(
                "# Inventory\nInventory supports stocktake.", encoding="utf-8"
            )
            (source / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
            (target / "README.md").write_text(
                "# Target\nCore must not depend on Feature. Use BigDecimal for money.",
                encoding="utf-8",
            )
            (target / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")

            original_path = self._with_registry(root)
            try:
                lisa_main.run_project_command(["add", str(source)])
                lisa_main.run_project_command(["add", str(target)])
                output = io.StringIO()
                with redirect_stdout(output):
                    lisa_main.run_project_command([
                        "compare", source.name, target.name, "inventory", "stocktake"
                    ])
                self.assertIn("potential_reuse", output.getvalue())
                self.assertIn("BigDecimal", output.getvalue())
                self.assertIn("No code was transferred", output.getvalue())
            finally:
                lisa_main.PROJECT_REGISTRY_PATH = original_path

    def test_project_plan_command_is_review_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "Source"
            target = root / "Target"
            source.mkdir()
            target.mkdir()
            (source / "README.md").write_text(
                "# Inventory\nInventory supports stocktake.", encoding="utf-8"
            )
            (source / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
            (target / "README.md").write_text(
                "# Target\nCore must not depend on Feature. Money must use BigDecimal.",
                encoding="utf-8",
            )
            (target / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")

            original_path = self._with_registry(root)
            try:
                lisa_main.run_project_command(["add", str(source)])
                lisa_main.run_project_command(["add", str(target)])
                output = io.StringIO()
                with redirect_stdout(output):
                    lisa_main.run_project_command([
                        "plan", source.name, target.name, "inventory", "stocktake"
                    ])
                self.assertIn("ready_for_review", output.getvalue())
                self.assertIn("Execution authorized: False", output.getvalue())
                self.assertIn("No code was copied", output.getvalue())
            finally:
                lisa_main.PROJECT_REGISTRY_PATH = original_path

    def test_add_use_and_list_commands_persist_project_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "Project With Spaces"
            project.mkdir()
            (project / "README.md").write_text("# CLI test project\n", encoding="utf-8")

            original_path = self._with_registry(root)
            try:
                lisa_main.run_project_command(["add", str(project)])
                registered = lisa_main._project_executor().execute(
                    lisa_main.ProjectRequest(operation=lisa_main.ProjectOperation.LIST)
                )
                self.assertEqual(len(registered.manifests), 1)

                lisa_main.run_project_command(["use", project.name])
                selected = lisa_main._project_executor().execute(
                    lisa_main.ProjectRequest(operation=lisa_main.ProjectOperation.LIST)
                )
                self.assertEqual(selected.context.root_path, str(project.resolve()))

                lisa_main.run_project_command(["list"])
            finally:
                lisa_main.PROJECT_REGISTRY_PATH = original_path


    def test_project_apply_requires_exact_operator_approval_and_creates_audit(self):
        import json
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "Source"
            target = root / "Target"
            source.mkdir()
            target.mkdir()
            (source / "README.md").write_text(
                "# Inventory\nInventory supports stocktake.", encoding="utf-8"
            )
            (source / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
            (target / "README.md").write_text(
                "# Target\nCore must not depend on Feature. Money must use BigDecimal.",
                encoding="utf-8",
            )
            (target / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
            (target / "app").mkdir()
            patch_file = root / "adaptation.json"
            patch_file.write_text(json.dumps({
                "changes": [{"path": "app/Inventory.kt", "content": "class Inventory {}\n"}]
            }), encoding="utf-8")

            original_path = self._with_registry(root)
            original_state_path = lisa_main.PROJECT_EXECUTION_STATE_PATH
            lisa_main.PROJECT_EXECUTION_STATE_PATH = root / "lisa-executions"
            try:
                lisa_main.run_project_command(["add", str(source)])
                lisa_main.run_project_command(["add", str(target)])
                def approve(prompt):
                    digest = prompt.split("APPLY ", 1)[1].split("'", 1)[0]
                    return f"APPLY {digest}"
                output = io.StringIO()
                with patch("builtins.input", side_effect=approve), redirect_stdout(output):
                    lisa_main.run_project_command([
                        "apply", source.name, target.name, "inventory", "stocktake",
                        "--patch", str(patch_file),
                    ])
                self.assertTrue((target / "app" / "Inventory.kt").exists())
                self.assertIn("Execution completed", output.getvalue())
                self.assertIn("VALIDATION REQUIRED", output.getvalue())
            finally:
                lisa_main.PROJECT_REGISTRY_PATH = original_path
                lisa_main.PROJECT_EXECUTION_STATE_PATH = original_state_path

    def test_project_apply_rejects_unconfirmed_patch(self):
        import json
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "Source"
            target = root / "Target"
            source.mkdir()
            target.mkdir()
            (source / "README.md").write_text(
                "# Inventory\nInventory supports stocktake.", encoding="utf-8"
            )
            (source / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
            (target / "README.md").write_text(
                "# Target\nCore must not depend on Feature. Money must use BigDecimal.",
                encoding="utf-8",
            )
            (target / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
            (target / "app").mkdir()
            patch_file = root / "adaptation.json"
            patch_file.write_text(json.dumps({
                "changes": [{"path": "app/Inventory.kt", "content": "class Inventory {}\n"}]
            }), encoding="utf-8")

            original_path = self._with_registry(root)
            original_state_path = lisa_main.PROJECT_EXECUTION_STATE_PATH
            lisa_main.PROJECT_EXECUTION_STATE_PATH = root / "lisa-executions"
            try:
                lisa_main.run_project_command(["add", str(source)])
                lisa_main.run_project_command(["add", str(target)])
                output = io.StringIO()
                with patch("builtins.input", return_value="no"), redirect_stdout(output):
                    lisa_main.run_project_command([
                        "apply", source.name, target.name, "inventory", "stocktake",
                        "--patch", str(patch_file),
                    ])
                self.assertFalse((target / "app" / "Inventory.kt").exists())
                self.assertIn("Execution refused or failed", output.getvalue())
            finally:
                lisa_main.PROJECT_REGISTRY_PATH = original_path
                lisa_main.PROJECT_EXECUTION_STATE_PATH = original_state_path


    def test_rollback_and_validate_cli_commands_record_lifecycle(self):
        import hashlib
        from unittest.mock import patch
        from lisa.projects import ProjectRegistry
        from lisa.projects.adaptation_planner import ProjectAdaptationPlanner
        from lisa.projects.adaptation_request import ProjectAdaptationRequest
        from lisa.projects.execution import ExecutionChange, ProjectExecutionRequest
        from lisa.projects.execution_executor import ProjectExecutionExecutor

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "Source"
            target = root / "Target"
            source.mkdir()
            target.mkdir()
            (source / "README.md").write_text(
                "# Inventory\nInventory supports stocktake.", encoding="utf-8"
            )
            (source / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
            (target / "README.md").write_text(
                "# Target\nCore must not depend on Feature. Money must use BigDecimal.",
                encoding="utf-8",
            )
            (target / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
            (target / "app").mkdir()

            original_registry = self._with_registry(root)
            original_state = lisa_main.PROJECT_EXECUTION_STATE_PATH
            lisa_main.PROJECT_EXECUTION_STATE_PATH = root / "executions"
            try:
                lisa_main.run_project_command(["add", str(source)])
                lisa_main.run_project_command(["add", str(target)])
                registry = ProjectRegistry(storage_path=lisa_main.PROJECT_REGISTRY_PATH)
                listing = registry.list_manifests()
                source_id = next(item.project_id for item in listing if item.name == "Source")
                target_id = next(item.project_id for item in listing if item.name == "Target")
                plan = ProjectAdaptationPlanner(registry).execute(ProjectAdaptationRequest(
                    source_project_id=source_id, target_project_id=target_id,
                    capability_query="inventory stocktake",
                )).plan
                executor = ProjectExecutionExecutor(registry, state_dir=lisa_main.PROJECT_EXECUTION_STATE_PATH)

                rollback_change = ExecutionChange("app/Rollback.kt", "class Rollback {}\n")
                rollback_digest = executor.approval_digest(plan, [rollback_change], target)
                applied = executor.execute(ProjectExecutionRequest(
                    plan, (rollback_change,), f"APPLY {rollback_digest}"
                ))
                self.assertTrue(applied.success, applied.error)

                def approve(prompt):
                    return prompt.split("'", 2)[1]
                output = io.StringIO()
                with patch("builtins.input", side_effect=approve), redirect_stdout(output):
                    lisa_main.run_project_command(["rollback", applied.execution_id])
                self.assertIn("Rollback completed", output.getvalue())
                self.assertFalse((target / "app" / "Rollback.kt").exists())

                validation_change = ExecutionChange("app/Validated.kt", "class Validated {}\n")
                validation_digest = executor.approval_digest(plan, [validation_change], target)
                validated = executor.execute(ProjectExecutionRequest(
                    plan, (validation_change,), f"APPLY {validation_digest}"
                ))
                self.assertTrue(validated.success, validated.error)

                output = io.StringIO()
                with patch("builtins.input", side_effect=approve), redirect_stdout(output):
                    lisa_main.run_project_command([
                        "validate", validated.execution_id, "--status", "passed",
                        "--command", "pytest -q", "--summary", "All tests passed",
                    ])
                self.assertIn("operator_reported_passed", output.getvalue())
                self.assertIn("operator-reported evidence", output.getvalue())
            finally:
                lisa_main.PROJECT_REGISTRY_PATH = original_registry
                lisa_main.PROJECT_EXECUTION_STATE_PATH = original_state


    def test_execution_history_and_verify_commands_are_read_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            original_registry = self._with_registry(root)
            original_state = lisa_main.PROJECT_EXECUTION_STATE_PATH
            lisa_main.PROJECT_EXECUTION_STATE_PATH = root / "executions"
            try:
                output = io.StringIO()
                with redirect_stdout(output):
                    lisa_main.run_project_command(["history"])
                self.assertIn("No matching cross-project executions", output.getvalue())

                output = io.StringIO()
                with redirect_stdout(output):
                    lisa_main.run_project_command(["verify", "not-an-execution"])
                self.assertIn("Integrity verification FAILED", output.getvalue())
            finally:
                lisa_main.PROJECT_REGISTRY_PATH = original_registry
                lisa_main.PROJECT_EXECUTION_STATE_PATH = original_state



if __name__ == "__main__":
    unittest.main()
