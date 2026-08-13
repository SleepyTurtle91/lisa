"""
Unit tests for NE-016 Governed Plan Execution.
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
from lisa.benchmarks.ne_016_governed_plan import GovernedPlan, GovernedPlanStep, GovernedPlanExecutor, PlanStepStatus


class TestGovernedPlanExecution(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.recorder = FlightRecorder(session_id="test_ne016", log_dir=Path(self.temp_dir.name))
        self.runtime = LisaRuntime(flight_recorder=self.recorder)
        self.runtime.tool_registry.register(ReadFileTool())
        self.runtime.tool_registry.register(ListDirectoryTool())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_plan_step_validation_rejection(self):
        plan = GovernedPlan(
            goal="Invalid step test",
            steps=[
                GovernedPlanStep(1, "List file", "list_directory", "README.md"),
                GovernedPlanStep(2, "Read file", "read_file", "README.md"),
            ]
        )
        project_path = str(Path(__file__).resolve().parent.parent)
        executor = GovernedPlanExecutor(self.runtime, project_path, self.recorder)
        res = asyncio.run(executor.execute_plan(plan))

        self.assertEqual(res[0].status, PlanStepStatus.REJECTED)
        self.assertIn("Cannot execute list_directory on FILE target", res[0].rejection_reason)
        # Step 2 must remain PENDING because Step 1 halted execution
        self.assertEqual(res[1].status, PlanStepStatus.PENDING)


if __name__ == "__main__":
    import asyncio
    unittest.main()
