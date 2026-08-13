"""
Unit tests for NE-018 Research Before Implementation.
"""

import tempfile
import unittest
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.benchmarks.ne_018_research_gate import ResearchGate, ExecutionMode


class TestResearchGate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_evaluate_knowledge_score_missing_docs(self):
        score = ResearchGate.evaluate_project_knowledge(self.temp_dir.name)
        self.assertEqual(score.score, 0)
        self.assertFalse(score.is_sufficient)

    def test_validate_action_mode_blocks_write_in_research_mode(self):
        valid, reason = ResearchGate.validate_action_mode(ExecutionMode.RESEARCH_MODE, "write_file")
        self.assertFalse(valid)
        self.assertIn("Research Gate Blocked Action", reason)

    def test_validate_action_mode_allows_read_in_research_mode(self):
        valid, reason = ResearchGate.validate_action_mode(ExecutionMode.RESEARCH_MODE, "read_file")
        self.assertTrue(valid)
        self.assertIsNone(reason)

    def test_validate_action_mode_allows_write_in_implementation_mode(self):
        valid, reason = ResearchGate.validate_action_mode(ExecutionMode.IMPLEMENTATION_MODE, "write_file")
        self.assertTrue(valid)
        self.assertIsNone(reason)


if __name__ == "__main__":
    unittest.main()
