import unittest
import asyncio
import tempfile
from pathlib import Path
from lisa.engine.models import InferenceRequest
from lisa.engine.inference import InferenceEngine
from lisa.providers.selector import ProviderSelector
from lisa.providers.registry import ProviderRegistry
from lisa.providers.ollama.provider import OllamaProvider
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.core.context import Capability
from lisa.telemetry.flight_recorder import FlightRecorder

class MockProviderForInferenceTests(BaseProvider):
    @property
    def id(self) -> str:
        return "mock_inference"

    @property
    def name(self) -> str:
        return "Mock Inference Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["mock-model"],
            capabilities=[Capability.CHAT]
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(content="inference-ok", usage={"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12})

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
        self.assertTrue(len(res.response.content) > 0)
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

    def test_inference_engine_uses_registered_provider(self):
        registry = ProviderRegistry()
        asyncio.run(registry.register(MockProviderForInferenceTests()))

        selector = ProviderSelector(registry)
        engine = InferenceEngine(selector)

        req = InferenceRequest(
            session_id="test_sess",
            messages=[{"role": "user", "content": "Test prompt"}],
            requested_capabilities=[Capability.CHAT]
        )

        res = asyncio.run(engine.execute(req))
        self.assertTrue(res.success)
        self.assertEqual(res.provider_id, "mock_inference")
        self.assertEqual(res.response.content, "inference-ok")

    def test_inference_engine_records_provider_boundary_events(self):
        registry = ProviderRegistry()
        asyncio.run(registry.register(MockProviderForInferenceTests()))

        selector = ProviderSelector(registry)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = FlightRecorder(session_id="provider_boundary_test", log_dir=Path(tmpdir))
            engine = InferenceEngine(selector, flight_recorder=recorder)

            req = InferenceRequest(
                session_id="test_sess",
                messages=[{"role": "user", "content": "Test prompt"}],
                requested_capabilities=[Capability.CHAT]
            )

            res = asyncio.run(engine.execute(req))
            self.assertTrue(res.success)

            events = recorder.get_events()
            event_types = [event["event_type"] for event in events]
            self.assertIn("model_request", event_types)
            self.assertIn("model_response", event_types)

            request_event = next(event for event in events if event["event_type"] == "model_request")
            response_event = next(event for event in events if event["event_type"] == "model_response")
            self.assertEqual(request_event["payload"]["provider_id"], "mock_inference")
            self.assertEqual(response_event["payload"]["content"], "inference-ok")

if __name__ == "__main__":
    unittest.main()
