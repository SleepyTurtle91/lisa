"""
Unit tests for NE-018.2 Question-Driven Research & Investigation Integrity.
"""

import tempfile
import unittest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.core.kernel import LisaRuntime
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import ListDirectoryTool
from lisa.benchmarks.ne_018_2_investigation_integrity import QuestionDrivenInvestigationEngine


class TestQuestionDrivenInvestigation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.recorder = FlightRecorder(session_id="test_ne018_2", log_dir=Path(self.temp_dir.name))
        self.runtime = LisaRuntime(flight_recorder=self.recorder)
        self.runtime.tool_registry.register(ReadFileTool())
        self.runtime.tool_registry.register(ListDirectoryTool())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_investigation_resolves_questions_and_difficulties(self):
        project_path = str(Path(__file__).resolve().parent.parent)
        engine = QuestionDrivenInvestigationEngine(self.runtime, project_path, self.recorder)
        res = asyncio.run(engine.conduct_investigation())

        self.assertTrue(res["checkpoint_valid"])
        self.assertEqual(res["unresolved_diffs_count"], 0)
        self.assertEqual(res["promoted_mode"], "IMPLEMENTATION_MODE")


if __name__ == "__main__":
    unittest.main()
