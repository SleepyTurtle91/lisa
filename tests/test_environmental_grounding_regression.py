import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.core.context import Capability, SessionContext
from lisa.core.kernel import LisaRuntime
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.base import ToolRequest
from lisa.tools.dispatcher import ToolExecutor
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.registry import ToolRegistry


class RelativeReadProvider(BaseProvider):
    def __init__(self):
        self._turn = 0

    @property
    def id(self) -> str:
        return "relative_read_provider"

    @property
    def name(self) -> str:
        return "Relative Read Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["mock-relative-read"],
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self._turn += 1
        if self._turn == 1:
            return ChatResponse(
                content="",
                tool_calls=[
                    {
                        "function": {
                            "name": "read_file",
                            "arguments": {"path": "BOOT.md"},
                        }
                    }
                ],
            )

        last_msg = request.messages[-1]
        if last_msg["role"] == "tool" and "Active Milestone" in last_msg["content"]:
            return ChatResponse(content="grounded-relative-read-ok")
        return ChatResponse(content="relative-read-failed")


class MissingFileProvider(BaseProvider):
    def __init__(self):
        self._turn = 0

    @property
    def id(self) -> str:
        return "missing_file_provider"

    @property
    def name(self) -> str:
        return "Missing File Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["mock-missing-file"],
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self._turn += 1
        if self._turn == 1:
            return ChatResponse(
                content="",
                tool_calls=[
                    {
                        "function": {
                            "name": "read_file",
                            "arguments": {"path": "MISSING.md"},
                        }
                    }
                ],
            )
        return ChatResponse(content="unable-to-read")


class TestEnvironmentalGroundingRegression(unittest.TestCase):
    def test_absolute_path_remains_unchanged(self):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as other_dir:
            abs_file = Path(project_dir) / "BOOT.md"
            abs_file.write_text("Absolute path grounding check", encoding="utf-8")

            registry = ToolRegistry()
            registry.register(ReadFileTool())
            executor = ToolExecutor(registry)

            req = ToolRequest(tool_name="read_file", arguments={"path": str(abs_file)})
            result = asyncio.run(executor.execute_request(req, project_path=other_dir))

            self.assertTrue(result.success)
            self.assertEqual(result.output, "Absolute path grounding check")
            self.assertEqual(result.metadata.get("resolved_path"), str(abs_file))
            self.assertEqual(result.metadata.get("path_kind"), "absolute")

    def test_case_mismatch_returns_suggestion_without_substitution(self):
        with tempfile.TemporaryDirectory() as project_dir:
            Path(project_dir, "BOOT.md").write_text("Milestone A", encoding="utf-8")

            registry = ToolRegistry()
            registry.register(ReadFileTool())
            executor = ToolExecutor(registry)

            req = ToolRequest(tool_name="read_file", arguments={"path": "boot.md"})
            result = asyncio.run(executor.execute_request(req, project_path=project_dir))

            self.assertFalse(result.success)
            self.assertIn("Resolved: ", result.error)
            self.assertIn("boot.md", result.error)
            self.assertIn("Did you mean 'BOOT.md'?", result.error)
            self.assertEqual(result.metadata.get("path_kind"), "relative")
            self.assertEqual(result.metadata.get("resolved_path"), str(Path(project_dir, "boot.md")))

    def test_session_project_path_is_authoritative_for_relative_paths(self):
        with tempfile.TemporaryDirectory() as project_dir:
            Path(project_dir, "BOOT.md").write_text("Active Milestone: Grounding", encoding="utf-8")

            runtime = LisaRuntime()
            asyncio.run(runtime.initialize())
            asyncio.run(runtime.register_provider(RelativeReadProvider()))
            runtime.tool_registry.register(ReadFileTool())

            ctx = SessionContext(
                project_path=project_dir,
                workspace_name="grounding_ws",
                provider_id="relative_read_provider",
                model_name="mock-relative-read",
                capabilities=[Capability.CHAT, Capability.TOOLS],
            )
            session = runtime.create_session(ctx)
            response = asyncio.run(session.send_message("read boot file"))

            self.assertEqual(response, "grounded-relative-read-ok")
            asyncio.run(runtime.shutdown())

    def test_flight_recorder_emits_path_resolution_chain(self):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as log_dir:
            Path(project_dir, "BOOT.md").write_text("Active Milestone: Grounding", encoding="utf-8")

            recorder = FlightRecorder(session_id="grounding_regression", log_dir=Path(log_dir))
            runtime = LisaRuntime(flight_recorder=recorder)
            asyncio.run(runtime.initialize())
            asyncio.run(runtime.register_provider(RelativeReadProvider()))
            runtime.tool_registry.register(ReadFileTool())

            ctx = SessionContext(
                project_path=project_dir,
                workspace_name="grounding_ws_trace",
                provider_id="relative_read_provider",
                model_name="mock-relative-read",
                capabilities=[Capability.CHAT, Capability.TOOLS],
            )
            session = runtime.create_session(ctx)
            response = asyncio.run(session.send_message("read boot file"))

            self.assertEqual(response, "grounded-relative-read-ok")

            events = recorder.get_events()
            stages = [event["payload"].get("stage") for event in events if event["event_type"] == "flight_stage"]
            self.assertIn("task_received", stages)
            self.assertIn("project_context", stages)
            self.assertIn("tool_request", stages)
            self.assertIn("path_resolution", stages)
            self.assertIn("resolved_path", stages)
            self.assertIn("tool_result", stages)
            self.assertIn("model_response", stages)

            resolution_events = [
                event for event in events
                if event["event_type"] == "flight_stage" and event["payload"].get("stage") == "path_resolution"
            ]
            self.assertGreaterEqual(len(resolution_events), 1)
            self.assertEqual(resolution_events[0]["payload"].get("resolved_path"), str(Path(project_dir, "BOOT.md")))

            asyncio.run(runtime.shutdown())

    def test_failed_tool_emits_guarding_and_blocked_stages(self):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as log_dir:
            recorder = FlightRecorder(session_id="grounding_guarding", log_dir=Path(log_dir))
            runtime = LisaRuntime(flight_recorder=recorder)
            asyncio.run(runtime.initialize())
            asyncio.run(runtime.register_provider(MissingFileProvider()))
            runtime.tool_registry.register(ReadFileTool())

            ctx = SessionContext(
                project_path=project_dir,
                workspace_name="grounding_ws_blocked",
                provider_id="missing_file_provider",
                model_name="mock-missing-file",
                capabilities=[Capability.CHAT, Capability.TOOLS],
            )
            session = runtime.create_session(ctx)
            _ = asyncio.run(session.send_message("read missing file"))

            events = recorder.get_events()
            stages = [event["payload"].get("stage") for event in events if event["event_type"] == "flight_stage"]
            self.assertIn("guarding_decision", stages)
            self.assertIn("blocked", stages)

            asyncio.run(runtime.shutdown())


if __name__ == "__main__":
    unittest.main()
