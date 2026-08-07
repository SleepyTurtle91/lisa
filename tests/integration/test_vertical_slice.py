import unittest
import asyncio
from pathlib import Path
from lisa.core.kernel import LisaRuntime
from lisa.bootstrap.engine import BootstrapEngine
from lisa.providers.ollama.provider import OllamaProvider
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.core.context import SessionContext, Capability

class TestVerticalSliceIntegration(unittest.TestCase):
    GOLDEN_PROJECT_PATH = Path("/home/user/development/projects/lisa/examples/golden_project")

    def test_end_to_end_vertical_slice(self):
        # 1. Project Discovery & Bootstrap Engine
        engine = BootstrapEngine.discover(str(self.GOLDEN_PROJECT_PATH))
        self.assertTrue(engine.boot_md_present, "BOOT.md must be present in Golden Project.")
        self.assertTrue(engine.agents_md_present, "AGENTS.md must be present in Golden Project.")

        # 2. Kernel Initialization & Real Provider Handshake
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        self.assertEqual(runtime.state.name, "READY")

        manifest = asyncio.run(runtime.register_provider(OllamaProvider()))
        self.assertTrue(manifest.healthy, "OllamaProvider must report healthy in integration test.")

        # 3. Tool Registration (ReadFileTool)
        runtime.tool_registry.register(ReadFileTool())
        self.assertIsNotNone(runtime.tool_registry.get("read_file"))

        # 4. Session Creation via Provider Selector & Inference Engine
        ctx = SessionContext(
            project_path=str(self.GOLDEN_PROJECT_PATH),
            workspace_name="golden_workspace",
            provider_id="ollama",
            model_name="qwen3:4b",
            capabilities=[Capability.CHAT, Capability.TOOLS]
        )
        session = runtime.create_session(ctx)

        # 5. Zero-Mock Execution: Send message trigger tool execution on real filesystem
        agents_md_path = str(self.GOLDEN_PROJECT_PATH / "AGENTS.md")
        res = asyncio.run(session.send_message(f"Please read the contents of {agents_md_path}"))

        # 6. Verify Complete Integration Chain
        self.assertIsNotNone(res)
        self.assertTrue(len(res) > 0)
        self.assertEqual(session.state.name, "READY")

        # 7. Clean Shutdown
        asyncio.run(runtime.shutdown())
        self.assertEqual(runtime.state.name, "UNINITIALIZED")

if __name__ == "__main__":
    unittest.main()
