import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.cli import main as lisa_main


class TestProjectCLI(unittest.TestCase):
    def test_add_use_and_list_commands_persist_project_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "Project With Spaces"
            project.mkdir()
            (project / "README.md").write_text("# CLI test project\n", encoding="utf-8")

            original_path = lisa_main.PROJECT_REGISTRY_PATH
            lisa_main.PROJECT_REGISTRY_PATH = root / ".lisa" / "projects.json"
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


if __name__ == "__main__":
    unittest.main()
