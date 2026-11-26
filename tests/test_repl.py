import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.cli.repl import add_recent_project, get_recent_projects, scan_common_projects


class TestReplFunctionality(unittest.TestCase):
    def test_recent_projects_flow_uses_existing_user_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "sample-project"
            project.mkdir()
            recent_file = Path(temp_dir) / ".lisa" / "recent.json"
            config_dir = recent_file.parent

            with patch("lisa.cli.repl.RECENT_FILE", recent_file), patch(
                "lisa.cli.repl.CONFIG_DIR", config_dir
            ):
                add_recent_project(str(project))
                self.assertEqual(get_recent_projects(), [str(project.resolve())])

    def test_scan_common_projects_uses_supplied_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            project = workspace / "sample-project"
            project.mkdir(parents=True)
            (project / "README.md").write_text("# Sample", encoding="utf-8")

            self.assertEqual(scan_common_projects([workspace]), [str(project.resolve())])

    def test_scan_common_projects_tolerates_missing_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "does-not-exist"
            self.assertEqual(scan_common_projects([missing]), [])

    def test_scan_common_projects_supports_configured_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "custom-workspace"
            project = workspace / "configured-project"
            project.mkdir(parents=True)
            (project / "AGENTS.md").write_text("# Project", encoding="utf-8")

            with patch.dict("os.environ", {"LISA_PROJECTS_DIRS": str(workspace)}):
                self.assertEqual(scan_common_projects(), [str(project.resolve())])


if __name__ == "__main__":
    unittest.main()
