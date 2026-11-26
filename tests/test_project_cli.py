import tempfile
import unittest
import io
from contextlib import redirect_stdout
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.cli import main as lisa_main


class TestProjectCLI(unittest.TestCase):
    def test_execution_preview_escapes_terminal_control_characters(self):
        raw = "name" + chr(27) + "[2J" + chr(13) + chr(10) + "next" + chr(9) + "line"
        visible = lisa_main._escape_terminal_controls(raw)
        self.assertEqual(visible, "name\\x1b[2J\\x0d\nnext\\x09line")
        self.assertNotIn(chr(27), visible)

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

    def test_project_apply_escapes_changed_paths_in_success_summary(self):
        import json
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "Source"
            target = root / "Target"
            source.mkdir()
            target.mkdir()
            (source / "README.md").write_text(
                "# Inventory\\nInventory supports stocktake.", encoding="utf-8"
            )
            (source / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
            (target / "README.md").write_text(
                "# Target\\nCore must not depend on Feature. Money must use BigDecimal.",
                encoding="utf-8",
            )
            (target / "settings.gradle.kts").write_text('include(":app")', encoding="utf-8")
            (target / "app").mkdir()
            unsafe_path = "app/terminal" + chr(27) + "[2J.kt"
            patch_file = root / "adaptation.json"
            patch_file.write_text(json.dumps({
                "changes": [{"path": unsafe_path, "content": "class Terminal {}\\n"}]
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
                rendered = output.getvalue()
                self.assertTrue((target / unsafe_path).exists())
                self.assertNotIn(chr(27), rendered)
                self.assertIn(r"\\x1b[2J", rendered)
                self.assertIn("Execution completed", rendered)
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


if __name__ == "__main__":
    unittest.main()
