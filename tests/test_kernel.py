import unittest
import asyncio
from lisa.core.context import SessionContext, Capability
from lisa.core.errors import ProviderError, SessionError
from lisa.core.events import EventBus, Event
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.tools.registry import ToolRegistry
from lisa.tools.compiler import ToolCompiler
from lisa.tools.dispatcher import ToolExecutor
from lisa.tools.base import ToolRequest
from lisa.tools.filesystem.read_file import ReadFileTool

class MockProviderForKernelTests(BaseProvider):
    @property
    def id(self) -> str:
        return "mock_kernel"

    @property
    def name(self) -> str:
        return "Mock Kernel Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["mock-kernel-v1"],
            capabilities=[]
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(content="mock")

class TestLisaKernelAndTools(unittest.TestCase):
    def test_session_context_immutable(self):
        ctx = SessionContext(
            project_path="/tmp/project",
            workspace_name="test_ws",
            provider_id="ollama",
            model_name="qwen3:4b",
            capabilities=[Capability.TOOLS]
        )
        self.assertEqual(ctx.provider_id, "ollama")
        self.assertIn(Capability.TOOLS, ctx.capabilities)

    def test_event_bus(self):
        bus = EventBus()
        received = []
        bus.subscribe("BOOT_COMPLETE", lambda e: received.append(e.payload["status"]))
        bus.publish(Event(name="BOOT_COMPLETE", payload={"status": "OK"}))
        self.assertEqual(received, ["OK"])

    def test_tool_registry_compiler_executor(self):
        registry = ToolRegistry()
        tool = ReadFileTool()
        registry.register(tool)
        
        # Test Registry
        self.assertIsNotNone(registry.get("read_file"))
        
        # Test Compiler
        compiled = ToolCompiler.compile_schema(tool, "ollama")
        self.assertEqual(compiled["type"], "function")
        self.assertEqual(compiled["function"]["name"], "read_file")
        
        # Test ToolExecutor
        executor = ToolExecutor(registry)
        req = ToolRequest(tool_name="read_file", arguments={"path": "non_existent_file.txt"})
        res = asyncio.run(executor.execute_request(req))
        self.assertFalse(res.success)
        self.assertIn("File not found", res.error)

    def test_create_session_rejects_invalid_context(self):
        from lisa.core.kernel import LisaRuntime

        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())

        invalid_ctx = SessionContext(
            project_path="",
            workspace_name="",
            provider_id=None,
            model_name="",
            capabilities=[]
        )

        with self.assertRaises(SessionError):
            runtime.create_session(invalid_ctx)

    def test_register_provider_requires_runtime_initialization(self):
        from lisa.core.kernel import LisaRuntime

        runtime = LisaRuntime()

        with self.assertRaises(ProviderError):
            asyncio.run(runtime.register_provider(MockProviderForKernelTests()))

if __name__ == "__main__":
    unittest.main()
