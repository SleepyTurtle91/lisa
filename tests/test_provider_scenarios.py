import unittest
import asyncio
from lisa.core.kernel import LisaRuntime
from lisa.core.context import SessionContext, Capability
from lisa.core.errors import ProviderError, SessionError
from lisa.providers.ollama.provider import OllamaProvider
from lisa.providers.openai.provider import OpenAIProvider
from lisa.providers.base import BaseProvider
from lisa.providers.manifest import ProviderManifest
from lisa.providers.base import ChatRequest, ChatResponse

class UnhealthyMockProvider(BaseProvider):
    @property
    def id(self) -> str:
        return "unhealthy_provider"

    @property
    def name(self) -> str:
        return "Unhealthy Mock"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=False,
            capabilities=[Capability.CHAT]
        )

    async def is_healthy(self) -> bool:
        return False

    async def chat(self, request: ChatRequest) -> ChatResponse:
        raise ProviderError("Offline")

class TestProviderRuntimeScenarios(unittest.TestCase):
    # Scenario 1: Only Ollama installed -> Selected cleanly
    def test_scenario_01_only_ollama(self):
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        asyncio.run(runtime.register_provider(OllamaProvider()))

        ctx = SessionContext(
            project_path="/tmp",
            workspace_name="ws",
            provider_id="ollama",
            model_name="qwen3:4b",
            capabilities=[Capability.CHAT, Capability.TOOLS]
        )
        session = runtime.create_session(ctx)
        reply = asyncio.run(session.send_message("Ping"))
        self.assertIn("[Ollama Response]", reply)

    # Scenario 2: Ollama + OpenAI installed -> Need Vision -> OpenAI selected
    def test_scenario_02_capability_based_selection(self):
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        asyncio.run(runtime.register_provider(OllamaProvider()))
        asyncio.run(runtime.register_provider(OpenAIProvider()))

        ctx = SessionContext(
            project_path="/tmp",
            workspace_name="ws",
            provider_id=None,
            model_name="gpt-4o",
            capabilities=[Capability.CHAT, Capability.VISION]
        )
        session = runtime.create_session(ctx)
        reply = asyncio.run(session.send_message("Analyze image"))
        self.assertIn("[OpenAI Response]", reply)

    # Scenario 3: Unhealthy Provider -> Registration rejected & Health API reports accurately
    def test_scenario_03_unhealthy_provider_reported(self):
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        with self.assertRaises(ProviderError):
            asyncio.run(runtime.register_provider(UnhealthyMockProvider()))

        health = runtime.health()
        self.assertEqual(len(health["providers"]), 0)

    # Scenario 4: Capability Mismatch -> Selection fails safely during Session messaging
    def test_scenario_04_capability_mismatch_fails_safely(self):
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        asyncio.run(runtime.register_provider(OllamaProvider()))

        ctx = SessionContext(
            project_path="/tmp",
            workspace_name="ws",
            provider_id=None,
            model_name="qwen3:4b",
            capabilities=[Capability.AUDIO, Capability.VISION]
        )
        session = runtime.create_session(ctx)
        with self.assertRaises(SessionError):
            asyncio.run(session.send_message("Should fail"))

if __name__ == "__main__":
    unittest.main()
