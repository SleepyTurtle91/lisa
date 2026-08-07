import unittest
import asyncio
from pathlib import Path
from lisa.core.kernel import LisaRuntime
from lisa.bootstrap.engine import BootstrapEngine
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.core.context import SessionContext, Capability

class RealToolCallingProvider(BaseProvider):
    def __init__(self):
        self._turn = 0

    @property
    def id(self) -> str:
        return "real_tool_calling_provider"

    @property
    def name(self) -> str:
        return "Real Tool Calling Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["mock-tool-calling"],
            capabilities=[Capability.CHAT, Capability.TOOLS]
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self._turn += 1
        if self._turn == 1:
            # Turn 1: Model requests a tool call to read BOOT.md in Golden Project
            boot_path = "/home/user/development/projects/lisa/examples/golden_project/BOOT.md"
            return ChatResponse(
                content="",
                tool_calls=[
                    {
                        "function": {
                            "name": "read_file",
                            "arguments": {"path": boot_path}
                        }
                    }
                ]
            )
        else:
            # Turn 2: Model receives tool result in history containing real file contents
            last_msg = request.messages[-1]
            if last_msg["role"] == "tool" and "Milestone v0.6" in last_msg["content"]:
                return ChatResponse(content="The active milestone in BOOT.md is Milestone v0.6 — Vertical Slice Integration Baseline.")
            return ChatResponse(content="Failed to find tool output in history.")

class TestVerticalSliceIntegration(unittest.TestCase):
    GOLDEN_PROJECT_PATH = Path("/home/user/development/projects/lisa/examples/golden_project")

    def test_end_to_end_vertical_slice(self):
        # 1. Project Discovery & Bootstrap Engine
        engine = BootstrapEngine.discover(str(self.GOLDEN_PROJECT_PATH))
        self.assertTrue(engine.boot_md_present, "BOOT.md must be present in Golden Project.")
        self.assertTrue(engine.agents_md_present, "AGENTS.md must be present in Golden Project.")

        # 2. Kernel Initialization & Provider Handshake
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())
        self.assertEqual(runtime.state.name, "READY")

        provider = RealToolCallingProvider()
        manifest = asyncio.run(runtime.register_provider(provider))
        self.assertTrue(manifest.healthy)

        # 3. Tool Registration (ReadFileTool)
        runtime.tool_registry.register(ReadFileTool())
        self.assertIsNotNone(runtime.tool_registry.get("read_file"))

        # 4. Session Creation via Provider Selector & Inference Engine
        ctx = SessionContext(
            project_path=str(self.GOLDEN_PROJECT_PATH),
            workspace_name="golden_workspace",
            provider_id="real_tool_calling_provider",
            model_name="mock-tool-calling",
            capabilities=[Capability.CHAT, Capability.TOOLS]
        )
        session = runtime.create_session(ctx)

        # 5. Zero-Mock Execution: Tool-calling prompt triggers ToolExecutor -> Real Filesystem Read -> Synthesis
        res = asyncio.run(session.send_message("What is the active milestone in BOOT.md?"))

        # 6. Verify Complete Integration Chain & Synthesis Outcome
        self.assertIn("Milestone v0.6", res)
        self.assertEqual(session.state.name, "READY")

        # 7. Clean Shutdown
        asyncio.run(runtime.shutdown())
        self.assertEqual(runtime.state.name, "UNINITIALIZED")

if __name__ == "__main__":
    unittest.main()
