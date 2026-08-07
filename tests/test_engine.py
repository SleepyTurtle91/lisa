import unittest
import asyncio
from lisa.engine.models import InferenceRequest
from lisa.engine.inference import InferenceEngine
from lisa.providers.selector import ProviderSelector
from lisa.providers.registry import ProviderRegistry
from lisa.providers.ollama.provider import OllamaProvider
from lisa.core.context import Capability

class TestInferenceEngine(unittest.TestCase):
    def test_inference_engine_execution(self):
        registry = ProviderRegistry()
        asyncio.run(registry.register(OllamaProvider()))
        selector = ProviderSelector(registry)
        engine = InferenceEngine(selector)

        req = InferenceRequest(
            session_id="test_sess",
            messages=[{"role": "user", "content": "Test prompt"}],
            requested_capabilities=[Capability.CHAT]
        )

        res = asyncio.run(engine.execute(req, preferred_provider_id="ollama"))
        self.assertTrue(res.success)
        self.assertEqual(res.provider_id, "ollama")
        self.assertIn("[Ollama Response]", res.response.content)
        self.assertGreaterEqual(res.latency_ms, 0.0)

    def test_inference_engine_error_normalization(self):
        registry = ProviderRegistry()
        selector = ProviderSelector(registry)
        engine = InferenceEngine(selector)

        req = InferenceRequest(
            session_id="test_sess",
            messages=[{"role": "user", "content": "Test prompt"}],
            requested_capabilities=[Capability.VISION]
        )

        res = asyncio.run(engine.execute(req))
        self.assertFalse(res.success)
        self.assertIsNone(res.response)
        self.assertIn("Provider Selection Failed", res.error)

if __name__ == "__main__":
    unittest.main()
