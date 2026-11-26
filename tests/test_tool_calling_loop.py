import unittest
import asyncio
import tempfile
from pathlib import Path
from lisa.core.kernel import LisaRuntime
from lisa.core.context import SessionContext, Capability
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.tools.filesystem.read_file import ReadFileTool

class ToolCallingMockProvider(BaseProvider):
    def __init__(self):
        self._turn = 0

    @property
    def id(self) -> str:
        return "tool_calling_mock"

    @property
    def name(self) -> str:
        return "Tool Calling Mock Provider"

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
            # Turn 1: Model requests a tool call to read AGENTS.md
            return ChatResponse(
                content="",
                tool_calls=[
                    {
                        "function": {
                            "name": "read_file",
                            "arguments": {"path": "AGENTS.md"}
                        }
                    }
                ]
            )
        else:
            # Turn 2: Model receives tool result in history and synthesizes final answer
            last_msg = request.messages[-1]
            if last_msg["role"] == "tool" and "L.I.S.A." in last_msg["content"]:
                return ChatResponse(content="The target file contains L.I.S.A. Kernel instructions.")
            return ChatResponse(content="Failed to find tool output in history.")

class TestToolCallingLoop(unittest.TestCase):
    def test_multi_turn_tool_calling_loop(self):
        runtime = LisaRuntime()
        asyncio.run(runtime.initialize())

        provider = ToolCallingMockProvider()
        asyncio.run(runtime.register_provider(provider))
        runtime.tool_registry.register(ReadFileTool())

        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "AGENTS.md").write_text(
                "L.I.S.A. Kernel instructions", encoding="utf-8"
            )
            ctx = SessionContext(
                project_path=temp_dir,
                workspace_name="ws",
                provider_id="tool_calling_mock",
                model_name="mock-tool-calling",
                capabilities=[Capability.CHAT, Capability.TOOLS]
            )
            session = runtime.create_session(ctx)

            # Trigger session execution - Turn 1 -> ToolExecutor -> Turn 2.
            final_answer = asyncio.run(session.send_message("What is in AGENTS.md?"))

            self.assertEqual(final_answer, "The target file contains L.I.S.A. Kernel instructions.")
            self.assertEqual(session.state.name, "READY")

if __name__ == "__main__":
    unittest.main()
