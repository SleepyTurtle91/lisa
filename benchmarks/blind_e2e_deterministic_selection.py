import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.core.context import SessionContext, Capability
from lisa.core.kernel import LisaRuntime
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool


class DeterministicSelectionHarnessProvider(BaseProvider):
    def __init__(self):
        self._turn = 0

    @property
    def id(self) -> str:
        return "blind_e2e_deterministic_selection_provider"

    @property
    def name(self) -> str:
        return "Blind E2E Deterministic Selection Provider"

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
            candidates_payload = {
                "candidates": [
                    {
                        "id": "A",
                        "confidence": 0.90,
                        "support": 5,
                        "contradictions": 0
                    },
                    {
                        "id": "B",
                        "confidence": 0.40,
                        "support": 2,
                        "contradictions": 3
                    }
                ]
            }
            return ChatResponse(content=json.dumps(candidates_payload), tool_calls=[])

        last_msg = request.messages[-1]
        if last_msg["role"] == "assistant":
            return ChatResponse(content="A")
        return ChatResponse(content="No selection made.")


def build_prompt() -> str:
    return "Select the candidate with the strongest evidence. Return its ID only."


async def run_deterministic_selection_harness(session_id: str | None = None, output_dir: Path | None = None) -> dict:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    resolved_session_id = session_id or f"blind_e2e_deterministic_{timestamp}"
    resolved_output_dir = output_dir or Path(__file__).resolve().parent
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    recorder = FlightRecorder(session_id=resolved_session_id, log_dir=resolved_output_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    await runtime.initialize()
    await runtime.register_provider(DeterministicSelectionHarnessProvider())
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="blind_e2e_deterministic_selection",
        provider_id="blind_e2e_deterministic_selection_provider",
        model_name="mock-flight",
        capabilities=[Capability.CHAT, Capability.TOOLS],
    )
    session = runtime.create_session(ctx)
    response = await session.send_message(build_prompt())

    events = recorder.get_events()
    stages = [event["payload"].get("stage") for event in events if event["event_type"] == "flight_stage"]

    boundary_events = [
        event for event in events
        if event["event_type"] in {"model_request", "model_response"}
    ]

    artifact = {
        "experiment_id": "BLIND-E2E-008",
        "title": "Deterministic Selection Baseline",
        "timestamp": datetime.now().isoformat(),
        "session_id": resolved_session_id,
        "prompt": build_prompt(),
        "response": response,
        "stages": stages,
        "events": events,
        "provider_boundary_events": boundary_events,
    }

    artifact_path = resolved_output_dir / f"{resolved_session_id}.json"
    with open(artifact_path, "w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2)

    await runtime.shutdown()
    return {"artifact_path": str(artifact_path), "stages": stages, "response": response}


if __name__ == "__main__":
    result = asyncio.run(run_deterministic_selection_harness())
    print("Deterministic selection harness completed.")
    print(f"Artifact: {result['artifact_path']}")
    print(f"Stages: {result['stages']}")
    print(f"Response: {result['response']}")
