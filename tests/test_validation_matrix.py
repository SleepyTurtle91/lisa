import unittest
import asyncio
from lisa.core.kernel import LisaRuntime
from lisa.core.context import SessionContext
from lisa.bootstrap.engine import BootstrapEngine
from lisa.tools.registry import ToolRegistry
from lisa.tools.dispatcher import ToolExecutor
from lisa.tools.base import ToolRequest
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.providers.base import BaseProvider
from lisa.providers.manifest import ProviderManifest
from lisa.providers.base import ChatRequest, ChatResponse

class DummyProvider(BaseProvider):
    @property
    def id(self) -> str:
        return "dummy"

    @property
    def name(self) -> str:
        return "Dummy Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["dummy-v1"],
            capabilities=[]
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(content="Echo: " + request.messages[-1]["content"])

class TestRuntimeValidationMatrix(unittest.TestCase):
    # Test 1: Runtime Boot (Start -> Stop without AI/Providers)
    def test_01_runtime_boot(self):
        runtime = LisaRuntime()
        events = []
        runtime.event_bus.subscribe("BOOT_STARTED", lambda e: events.append(e.name))
        runtime.event_bus.subscribe("RUNTIME_SHUTDOWN", lambda e: events.append(e.name))

        asyncio.run(runtime.initialize())
        self.assertTrue(runtime.state.name == "READY")

        asyncio.run(runtime.shutdown())
        self.assertTrue(runtime.state.name == "UNINITIALIZED")
        self.assertEqual(events, ["BOOT_STARTED", "RUNTIME_SHUTDOWN"])

    # Test 2: Provider (Runtime -> DummyProvider -> Response without tools)
    def test_02_provider_no_tools(self):
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())

        provider = DummyProvider()
        asyncio.run(runtime.register_provider(provider))

        ctx = SessionContext(
            project_path="/tmp",
            workspace_name="ws",
            provider_id="dummy",
            model_name="dummy-v1"
        )
        session = runtime.create_session(ctx)
        reply = asyncio.run(session.send_message("Ping"))
        self.assertEqual(reply, "Echo: Ping")

    # Test 3: Tool Execution (Tool -> Executor -> ReadFileTool without Provider/AI)
    def test_03_tool_standalone(self):
        registry = ToolRegistry()
        registry.register(ReadFileTool())
        executor = ToolExecutor(registry)

        req = ToolRequest(tool_name="read_file", arguments={"path": "/home/user/development/projects/lisa/AGENTS.md"})
        res = asyncio.run(executor.execute_request(req))
        self.assertTrue(res.success)
        self.assertIn("L.I.S.A.", res.output)

    # Test 4: Provider + Tool execution pipeline
    def test_04_provider_plus_tool(self):
        registry = ToolRegistry()
        registry.register(ReadFileTool())
        executor = ToolExecutor(registry)

        tool = registry.get("read_file")
        self.assertIsNotNone(tool)
        req = ToolRequest(tool_name="read_file", arguments={"path": "/non_existent.txt"})
        res = asyncio.run(executor.execute_request(req))
        self.assertFalse(res.success)

    # Test 5: Bootstrap Engine Discovery
    def test_05_bootstrap_discovery(self):
        boot = BootstrapEngine.discover("/home/user/development/projects/lisa")
        self.assertTrue(boot.agents_md_present)

if __name__ == "__main__":
    unittest.main()
