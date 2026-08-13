"""
Unit tests for Target Identity Binding (NE-012.3).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.tools.filesystem.target_grounding import TargetInspector


class TestTargetIdentityBinding(unittest.TestCase):
    def test_identity_match_valid(self):
        v, err = TargetInspector.validate_target_identity("read README.md", "README.md")
        self.assertTrue(v)
        self.assertIsNone(err)

    def test_identity_mismatch_root_fallback(self):
        v, err = TargetInspector.validate_target_identity("list README.md", "/")
        self.assertFalse(v)
        self.assertIn("Target Identity Mismatch", err)

    def test_identity_mismatch_dot_fallback(self):
        v, err = TargetInspector.validate_target_identity("list README.md", ".")
        self.assertFalse(v)
        self.assertIn("Target Identity Mismatch", err)

    def test_no_prompt_valid(self):
        v, err = TargetInspector.validate_target_identity(None, "/")
        self.assertTrue(v)
        self.assertIsNone(err)


if __name__ == "__main__":
    unittest.main()
