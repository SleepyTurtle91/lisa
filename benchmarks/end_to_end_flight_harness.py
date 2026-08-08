import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root and parent to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.core.context import SessionContext, Capability
from lisa.core.kernel import LisaRuntime
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool


class EndToEndHarnessProvider(BaseProvider):
    def __init__(self):
        self._turn = 0

    @property
    def id(self) -> str:
        return "end_to_end_harness_provider"

    @property
    def name(self) -> str:
        return "End to End Harness Provider"

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
            return ChatResponse(
                content="The runtime guidance in AGENTS.md is grounded in L.I.S.A. evidence discipline."
            )
        return ChatResponse(content="Failed to find the requested evidence in the tool output.")


def build_prompt() -> str:
    return "Inspect AGENTS.md and summarize the runtime guidance."


async def run_end_to_end_harness(session_id: str | None = None, output_dir: Path | None = None) -> dict:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    resolved_session_id = session_id or f"e2e_flight_{timestamp}"
    resolved_output_dir = output_dir or Path(__file__).resolve().parent
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    recorder = FlightRecorder(session_id=resolved_session_id, log_dir=resolved_output_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    await runtime.initialize()
    await runtime.register_provider(EndToEndHarnessProvider())
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="e2e_harness",
        provider_id="end_to_end_harness_provider",
        model_name="mock-flight",
        capabilities=[Capability.CHAT, Capability.TOOLS],
    )
    session = runtime.create_session(ctx)
    response = await session.send_message(build_prompt())

    events = recorder.get_events()
    stages = [event["payload"].get("stage") for event in events if event["event_type"] == "flight_stage"]

    artifact = {
        "experiment_id": "NE-007",
        "title": "Composition-Level End-to-End Flight Trace",
        "timestamp": datetime.now().isoformat(),
        "session_id": resolved_session_id,
        "prompt": build_prompt(),
        "response": response,
        "stages": stages,
        "events": events,
    }

    artifact_path = resolved_output_dir / f"{resolved_session_id}.json"
    with open(artifact_path, "w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2)

    await runtime.shutdown()
    return {"artifact_path": str(artifact_path), "stages": stages, "response": response}


if __name__ == "__main__":
    result = asyncio.run(run_end_to_end_harness())
    print("End-to-end harness completed.")
    print(f"Artifact: {result['artifact_path']}")
    print(f"Stages: {result['stages']}")
    print(f"Response: {result['response']}")
