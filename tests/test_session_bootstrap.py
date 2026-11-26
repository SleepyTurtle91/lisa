import unittest
import asyncio
import tempfile
from pathlib import Path
from lisa.bootstrap.engine import BootstrapEngine
from lisa.providers.base import BaseProvider
from lisa.providers.manifest import ProviderManifest
from lisa.providers.base import ChatRequest, ChatResponse
from lisa.providers.registry import ProviderRegistry
from lisa.providers.selector import ProviderSelector
from lisa.engine.inference import InferenceEngine
from lisa.tools.registry import ToolRegistry
from lisa.runtime.session import LisaSession
from lisa.core.context import SessionContext

class MockProvider(BaseProvider):
    @property
    def id(self) -> str:
        return "mock"

    @property
    def name(self) -> str:
        return "Mock Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["mock-v1"],
            capabilities=[]
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(content="Mocked response")

class TestPhase4BootstrapAndSession(unittest.TestCase):
    def test_bootstrap_discover(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "AGENTS.md").write_text("# Project instructions", encoding="utf-8")
            engine = BootstrapEngine.discover(temp_dir)
            self.assertTrue(engine.project.agents_md_present)
            self.assertEqual(engine.project.project_path, temp_dir)

    def test_session_execution(self):
        provider = MockProvider()
        p_registry = ProviderRegistry()
        asyncio.run(p_registry.register(provider))
        selector = ProviderSelector(p_registry)
        engine = InferenceEngine(selector)
        
        t_registry = ToolRegistry()
        ctx = SessionContext(
            project_path="/tmp",
            workspace_name="test",
            provider_id="mock",
            model_name="mock-v1"
        )
        session = LisaSession(ctx, engine, t_registry)
        res = asyncio.run(session.send_message("Hello"))
        self.assertEqual(res, "Mocked response")

if __name__ == "__main__":
    unittest.main()
