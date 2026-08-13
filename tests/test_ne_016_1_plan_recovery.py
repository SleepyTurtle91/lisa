"""
Unit tests for NE-016.1 Plan Recovery & Replanning.
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
from lisa.memory.evidence_store import EvidenceStore, EvidenceCategory
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import ListDirectoryTool
from lisa.benchmarks.ne_016_governed_plan import GovernedPlan, GovernedPlanStep, GovernedPlanExecutor, PlanStepStatus


class TestPlanRecoveryAndReplanning(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.recorder = FlightRecorder(session_id="test_ne016_1", log_dir=Path(self.temp_dir.name))
        self.runtime = LisaRuntime(flight_recorder=self.recorder)
        self.runtime.tool_registry.register(ReadFileTool())
        self.runtime.tool_registry.register(ListDirectoryTool())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_plan_failure_and_replanning_recovery(self):
        project_path = str(Path(__file__).resolve().parent.parent)
        executor = GovernedPlanExecutor(self.runtime, project_path, self.recorder)

        # Plan A: Step 1 valid, Step 2 missing file
        plan_a = GovernedPlan(
            goal="Plan A",
            steps=[
                GovernedPlanStep(1, "Step 1", "list_directory", "."),
                GovernedPlanStep(2, "Step 2", "read_file", "non_existent_file.md"),
                GovernedPlanStep(3, "Step 3", "read_file", "README.md"),
            ]
        )
        res_a = asyncio.run(executor.execute_plan(plan_a))

        self.assertEqual(res_a[0].status, PlanStepStatus.EXECUTED)
        self.assertEqual(res_a[1].status, PlanStepStatus.BLOCKED)
        self.assertEqual(res_a[2].status, PlanStepStatus.PENDING)

        # Plan B: Recovery plan
        plan_b = GovernedPlan(
            goal="Plan B",
            steps=[
                GovernedPlanStep(1, "Step 1", "read_file", "README.md"),
            ]
        )
        res_b = asyncio.run(executor.execute_plan(plan_b))

        self.assertEqual(res_b[0].status, PlanStepStatus.EXECUTED)

        # Verify Evidence Invariance
        store = EvidenceStore()
        for ev in self.recorder.get_events():
            store.ingest_event(ev)

        self.assertEqual(len(store.query(EvidenceCategory.OBSERVED)), 2)
        self.assertEqual(len(store.query(EvidenceCategory.UNVERIFIED)), 1)


if __name__ == "__main__":
    unittest.main()
