"""
Unit tests for NE-014.1 InputBoundaryClassifier.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.cli.input_classifier import InputBoundaryClassifier, InputClass


class TestInputBoundaryClassifier(unittest.TestCase):
    def test_direct_command_literal(self):
        res = InputBoundaryClassifier.classify("doctor")
        self.assertEqual(res.input_class, InputClass.DIRECT_COMMAND)
        self.assertEqual(res.command, "doctor")

    def test_direct_command_single_target(self):
        res = InputBoundaryClassifier.classify("read BOOT.md")
        self.assertEqual(res.input_class, InputClass.DIRECT_COMMAND)
        self.assertEqual(res.command, "read")
        self.assertEqual(res.target, "BOOT.md")

    def test_compound_natural_language_starting_with_read(self):
        res = InputBoundaryClassifier.classify("read files inside /docs and suggest a plan")
        self.assertEqual(res.input_class, InputClass.NATURAL_LANGUAGE)
        self.assertIsNone(res.command)

    def test_absolute_path_input(self):
        res = InputBoundaryClassifier.classify("/workspace/Projects/retails")
        self.assertEqual(res.input_class, InputClass.PATH_INPUT)
        self.assertEqual(res.target, "/workspace/Projects/retails")


if __name__ == "__main__":
    unittest.main()
