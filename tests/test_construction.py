import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.engine.construction import ModelConstructionEngine
from lisa.engine.analyzer import TaskAnalyzer
from lisa.engine.planner import ExecutionPlanner

class TestModelConstructionEngine(unittest.TestCase):
    def test_get_profile_small_tier(self):
        env = ModelConstructionEngine.get_profile("qwen3:1.7b")
        self.assertEqual(env.tier, "small")
        self.assertIn("do_not_guess", env.active_rules)
        self.assertIn("STRICT GOVERNANCE & EVIDENCE RULES", env.scaffolded_system_prompt)

    def test_get_profile_standard_tier(self):
        env = ModelConstructionEngine.get_profile("qwen3:4b")
        self.assertEqual(env.tier, "standard")
        self.assertIn("analyze_context", env.workflow_steps)

    def test_get_profile_architecture_domain(self):
        env = ModelConstructionEngine.get_profile("qwen3:4b", intent="architecture")
        self.assertEqual(env.instruction_style, "evidence_disciplined")
        self.assertIn("never_invent_uninspected_files", env.active_rules)
        self.assertIn("STRICT GOVERNANCE & EVIDENCE RULES", env.scaffolded_system_prompt)

    def test_planner_links_scaffold(self):
        profile = TaskAnalyzer.analyze("Read BOOT.md and tell me active milestone")
        plan = ExecutionPlanner.create_plan(
            profile=profile,
            provider_id="ollama",
            model_name="qwen3:1.7b",
            available_tools=["read_file"]
        )
        self.assertIsNotNone(plan.scaffolded_env)
        self.assertEqual(plan.scaffolded_env.tier, "small")
        self.assertIn("Cognitive Scaffolding", plan.reason)

if __name__ == "__main__":
    unittest.main()
