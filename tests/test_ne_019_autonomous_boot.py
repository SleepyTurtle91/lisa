"""
Unit tests for NE-019 Autonomous Project Boot Engine.
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
from lisa.benchmarks.ne_019_autonomous_boot import AutonomousProjectBootEngine


class TestAutonomousProjectBootEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.recorder = FlightRecorder(session_id="test_ne019", log_dir=Path(self.temp_dir.name))
        self.runtime = LisaRuntime(flight_recorder=self.recorder)
        self.runtime.tool_registry.register(ReadFileTool())
        self.runtime.tool_registry.register(ListDirectoryTool())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_autonomous_boot_engine_executes_discovery(self):
        project_path = str(Path(__file__).resolve().parent.parent)
        engine = AutonomousProjectBootEngine(self.runtime, project_path, self.recorder)
        checkpoint = asyncio.run(engine.boot_project())

        self.assertTrue(checkpoint.is_authorized)
        self.assertGreaterEqual(checkpoint.integrity_score, 0.7)
        self.assertEqual(len(checkpoint.knowledge_items), 10)


if __name__ == "__main__":
    unittest.main()
