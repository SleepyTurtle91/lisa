import unittest
import asyncio
from lisa.core.context import SessionContext, Capability
from lisa.core.events import EventBus, Event
from lisa.tools.registry import ToolRegistry
from lisa.tools.compiler import ToolCompiler
from lisa.tools.dispatcher import ToolExecutor
from lisa.tools.base import ToolRequest
from lisa.tools.filesystem.read_file import ReadFileTool

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

if __name__ == "__main__":
    unittest.main()
