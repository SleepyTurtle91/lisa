import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.engine.analyzer import TaskAnalyzer
from lisa.engine.planner import ExecutionPlanner, ExecutionPlan

class TestExecutionPlanner(unittest.TestCase):
    def test_execution_plan_creation_low_complexity(self):
        profile = TaskAnalyzer.analyze("Hello, tell me about your capabilities")
        plan = ExecutionPlanner.create_plan(
            profile=profile,
            provider_id="ollama",
            model_name="qwen3:1.7b",
            available_tools=["read_file"],
            ram_gb=16.0
        )
        self.assertEqual(plan.complexity_level, "LOW")
        self.assertEqual(plan.mode, "AUTO")
        self.assertGreater(plan.hardware_score, 0.9)
        self.assertIn("optimal fast response model", plan.reason)

    def test_execution_plan_high_complexity_architecture(self):
        profile = TaskAnalyzer.analyze("Analyze system architecture and run doctor gate checks")
        plan = ExecutionPlanner.create_plan(
            profile=profile,
            provider_id="ollama",
            model_name="qwen3:30b",
            available_tools=["read_file", "write_file", "list_directory"],
            ram_gb=16.0
        )
        self.assertEqual(plan.complexity_level, "HIGH")
        self.assertIn("architecture keywords", plan.reason)

if __name__ == "__main__":
    unittest.main()
