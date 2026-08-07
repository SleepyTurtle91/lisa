import unittest
import asyncio
from lisa.core.kernel import LisaRuntime
from lisa.core.context import SessionContext, Capability
from lisa.core.states import RuntimeState, SessionState
from lisa.core.errors import ProviderError, ValidationError, SessionError
from lisa.tools.registry import ToolRegistry
from lisa.tools.dispatcher import ToolExecutor
from lisa.tools.base import BaseTool, ToolResult, ToolRequest
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.providers.base import BaseProvider
from lisa.providers.manifest import ProviderManifest
from lisa.providers.base import ChatRequest, ChatResponse

class HealthyMockProvider(BaseProvider):
    @property
    def id(self) -> str:
        return "mock_healthy"

    @property
    def name(self) -> str:
        return "Healthy Mock Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["mock-v1"],
            capabilities=[Capability.CHAT, Capability.TOOLS]
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(content="Echo: " + request.messages[-1]["content"])

class UnhealthyMockProvider(BaseProvider):
    @property
    def id(self) -> str:
        return "mock_unhealthy"

    @property
    def name(self) -> str:
        return "Unhealthy Mock Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=False,
            supported_models=[],
            capabilities=[]
        )

    async def is_healthy(self) -> bool:
        return False

    async def chat(self, request: ChatRequest) -> ChatResponse:
        raise ProviderError("Connection refused")

class ExceptionTool(BaseTool):
    @property
    def name(self) -> str:
        return "faulty_tool"

    @property
    def description(self) -> str:
        return "Tool that throws unexpected exceptions."

    @property
    def parameters_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        raise RuntimeError("Hardware/I/O hardware fault!")

class TestResilienceMatrix(unittest.TestCase):
    # Test 1: Runtime Starts cleanly with explicit states
    def test_01_runtime_starts(self):
        runtime = LisaRuntime()
        self.assertEqual(runtime.state, RuntimeState.UNINITIALIZED)
        asyncio.run(runtime.initialize())
        self.assertEqual(runtime.state, RuntimeState.READY)
        asyncio.run(runtime.shutdown())
        self.assertEqual(runtime.state, RuntimeState.UNINITIALIZED)

    # Test 2: Provider Connects via Handshake
    def test_02_provider_connects(self):
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        provider = HealthyMockProvider()
        manifest = asyncio.run(runtime.register_provider(provider))
        self.assertTrue(manifest.healthy)
        self.assertIn("mock_healthy", [p["id"] for p in runtime.health()["providers"]])

    # Test 3: Provider Unavailable Handshake Rejection
    def test_03_provider_unavailable(self):
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        provider = UnhealthyMockProvider()
        with self.assertRaises(ProviderError):
            asyncio.run(runtime.register_provider(provider))

    # Test 4: Tool Execution Success
    def test_04_tool_succeeds(self):
        registry = ToolRegistry()
        registry.register(ReadFileTool())
        executor = ToolExecutor(registry)
        req = ToolRequest(tool_name="read_file", arguments={"path": "/home/user/development/projects/lisa/AGENTS.md"})
        res = asyncio.run(executor.execute_request(req))
        self.assertTrue(res.success)

    # Test 5: Tool Throws Exception -> Runtime Survives & Isolates Error
    def test_05_tool_throws_exception(self):
        registry = ToolRegistry()
        registry.register(ExceptionTool())
        executor = ToolExecutor(registry, max_retries=1)
        req = ToolRequest(tool_name="faulty_tool", arguments={})
        res = asyncio.run(executor.execute_request(req))
        self.assertFalse(res.success)
        self.assertIn("attempt 2/2", res.error)

    # Test 6: Tool Schema Validator Rejects Bad Schema
    def test_06_tool_schema_validation(self):
        registry = ToolRegistry()
        class ReservedKeywordTool(BaseTool):
            @property
            def name(self) -> str:
                return "eval"
            @property
            def description(self) -> str:
                return "bad tool"
            @property
            def parameters_schema(self) -> dict:
                return {}
            async def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, output=None)

        with self.assertRaises(ValidationError):
            registry.register(ReservedKeywordTool())

    # Test 7: Session Failure & State Transition
    def test_07_session_failure_state(self):
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        asyncio.run(runtime.register_provider(HealthyMockProvider()))
        
        ctx = SessionContext(project_path="/tmp", workspace_name="ws", provider_id="mock_healthy", model_name="v1")
        session = runtime.create_session(ctx)
        self.assertEqual(session.state, SessionState.CREATED)
        
        reply = asyncio.run(session.send_message("Hello"))
        self.assertEqual(reply, "Echo: Hello")
        self.assertEqual(session.state, SessionState.READY)
        
        session.close()
        self.assertEqual(session.state, SessionState.CLOSED)
        with self.assertRaises(SessionError):
            asyncio.run(session.send_message("Should fail"))

    # Test 8: Health API Completeness
    def test_08_health_api(self):
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        asyncio.run(runtime.register_provider(HealthyMockProvider()))
        runtime.tool_registry.register(ReadFileTool())
        
        health = runtime.health()
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["runtime_state"], "READY")
        self.assertEqual(len(health["providers"]), 1)
        self.assertEqual(len(health["tools"]), 1)

if __name__ == "__main__":
    unittest.main()
