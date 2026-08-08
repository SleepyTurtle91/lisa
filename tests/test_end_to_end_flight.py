import asyncio
import tempfile
import unittest
from pathlib import Path

from lisa.core.context import SessionContext, Capability
from lisa.core.kernel import LisaRuntime
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool


class EndToEndFlightProvider(BaseProvider):
    def __init__(self):
        self._turn = 0

    @property
    def id(self) -> str:
        return "end_to_end_flight_provider"

    @property
    def name(self) -> str:
        return "End to End Flight Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["mock-flight"],
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
                            "arguments": {"path": "/home/user/Projects/lisa/AGENTS.md"},
                        }
                    }
                ],
            )

        last_msg = request.messages[-1]
        if last_msg["role"] == "tool" and "L.I.S.A." in last_msg["content"]:
            return ChatResponse(content="The runtime guidance in AGENTS.md is grounded in L.I.S.A. evidence discipline.")
        return ChatResponse(content="Failed to find the requested evidence in the tool output.")


class TestEndToEndFlight(unittest.TestCase):
    def test_session_emits_trace_stages_for_end_to_end_flight(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = FlightRecorder(session_id="flight_trace_test", log_dir=Path(tmpdir))

            runtime = LisaRuntime(flight_recorder=recorder)
            asyncio.run(runtime.initialize())
            asyncio.run(runtime.register_provider(EndToEndFlightProvider()))
            runtime.tool_registry.register(ReadFileTool())

            ctx = SessionContext(
                project_path="/home/user/Projects/lisa",
                workspace_name="e2e_flight",
                provider_id="end_to_end_flight_provider",
                model_name="mock-flight",
                capabilities=[Capability.CHAT, Capability.TOOLS],
            )
            session = runtime.create_session(ctx)
            response = asyncio.run(session.send_message("Inspect AGENTS.md and summarize the runtime guidance."))

            self.assertIn("L.I.S.A.", response)

            events = recorder.get_events()
            stages = [event["payload"].get("stage") for event in events if event["event_type"] == "flight_stage"]
            self.assertIn("objective_received", stages)
            self.assertIn("tool_call", stages)
            self.assertIn("final_conclusion", stages)
            self.assertLess(stages.index("objective_received"), stages.index("tool_call"))
            self.assertLess(stages.index("tool_call"), stages.index("final_conclusion"))

            asyncio.run(runtime.shutdown())

    def test_blind_objective_emits_discovery_and_decision_stages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = FlightRecorder(session_id="blind_objective_trace", log_dir=Path(tmpdir))

            runtime = LisaRuntime(flight_recorder=recorder)
            asyncio.run(runtime.initialize())
            asyncio.run(runtime.register_provider(EndToEndFlightProvider()))
            runtime.tool_registry.register(ReadFileTool())

            ctx = SessionContext(
                project_path="/home/user/Projects/lisa",
                workspace_name="blind_objective_flight",
                provider_id="end_to_end_flight_provider",
                model_name="mock-flight",
                capabilities=[Capability.CHAT, Capability.TOOLS],
            )
            session = runtime.create_session(ctx)
            response = asyncio.run(session.send_message("Find and fix a small bug in the provider registration behavior. Do not modify unrelated functionality. Verify with tests."))

            self.assertIn("L.I.S.A.", response)

            events = recorder.get_events()
            stages = [event["payload"].get("stage") for event in events if event["event_type"] == "flight_stage"]
            self.assertIn("target_discovery", stages)
            self.assertIn("task_analysis", stages)
            self.assertIn("model_selection", stages)
            self.assertIn("scaffolding_decision", stages)

            asyncio.run(runtime.shutdown())


if __name__ == "__main__":
    unittest.main()
