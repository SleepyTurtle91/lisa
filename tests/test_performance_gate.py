import unittest
import asyncio
import time
from lisa.core.kernel import LisaRuntime
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import WriteFileTool, ListDirectoryTool
from lisa.providers.ollama.provider import OllamaProvider

class TestPerformanceGate(unittest.TestCase):
    def test_boot_overhead_performance_gate(self):
        """Ensures L.I.S.A. framework boot overhead remains under strict 15.0 ms limit."""
        start = time.perf_counter()
        
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        asyncio.run(runtime.register_provider(OllamaProvider()))
        
        runtime.tool_registry.register(ReadFileTool())
        runtime.tool_registry.register(WriteFileTool())
        runtime.tool_registry.register(ListDirectoryTool())
        
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        asyncio.run(runtime.shutdown())

        self.assertLess(elapsed_ms, 15.0, f"Framework boot overhead ({elapsed_ms:.2f} ms) exceeded 15.0 ms CI Performance Gate limit!")

    def test_tool_dispatch_performance_gate(self):
        """Ensures tool registration & retrieval overhead remains under strict 2.0 ms limit."""
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        
        start = time.perf_counter()
        runtime.tool_registry.register(ReadFileTool())
        tools = runtime.tool_registry.list_tools()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        
        asyncio.run(runtime.shutdown())
        self.assertEqual(len(tools), 1)
        self.assertLess(elapsed_ms, 2.0, f"Tool dispatch overhead ({elapsed_ms:.2f} ms) exceeded 2.0 ms CI Performance Gate limit!")

if __name__ == "__main__":
    unittest.main()
