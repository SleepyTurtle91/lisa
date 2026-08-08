import os
import sys
import unittest
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.engine.analyzer import TaskAnalyzer
from lisa.engine.auto_selector import AutoSelector
from lisa.providers.registry import ProviderRegistry
from lisa.providers.selector import ProviderSelector
from lisa.providers.ollama.provider import OllamaProvider

class TestAutoSelector(unittest.TestCase):
    def test_task_analyzer_code_edit(self):
        prompt = "Fix the inventory sync bug in products repository"
        profile = TaskAnalyzer.analyze(prompt)
        self.assertEqual(profile.detected_intent, "engineering_evidence")
        self.assertGreater(profile.complexity_score, 0.5)

    def test_task_analyzer_architecture(self):
        prompt = "Run system doctor and analyze architecture rules"
        profile = TaskAnalyzer.analyze(prompt)
        self.assertEqual(profile.detected_intent, "engineering_evidence")
        self.assertEqual(profile.suggested_model_tier, "heavy")

    def test_auto_selector_execution(self):
        async def _run():
            registry = ProviderRegistry()
            ollama = OllamaProvider()
            await registry.register(ollama)
            selector = ProviderSelector(registry)
            auto_sel = AutoSelector(selector)
            
            res = await auto_sel.select_for_prompt("Refactor standard tool compilation engine")
            self.assertIsNotNone(res.provider)
            self.assertIsNotNone(res.model_name)
            self.assertEqual(res.task_profile.detected_intent, "engineering_evidence")
        asyncio.run(_run())

if __name__ == "__main__":
    unittest.main()
