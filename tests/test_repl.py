import os
import sys
import unittest
from pathlib import Path

# Add project root and parent to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.cli.repl import get_recent_projects, add_recent_project, scan_common_projects

class TestReplFunctionality(unittest.TestCase):
    def test_recent_projects_flow(self):
        test_path = "/home/user/development/projects/lisa"
        add_recent_project(test_path)
        recents = get_recent_projects()
        self.assertIn(os.path.abspath(test_path), recents)

    def test_scan_common_projects(self):
        projects = scan_common_projects()
        self.assertIsInstance(projects, list)
        self.assertTrue(len(projects) > 0)

if __name__ == "__main__":
    unittest.main()
