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


class TargetSelectionHarnessProvider(BaseProvider):
    def __init__(self):
        self._turn = 0

    @property
    def id(self) -> str:
        return "blind_e2e_target_selection_provider"

    @property
    def name(self) -> str:
        return "Blind E2E Target Selection Provider"

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
                        "id": "C1",
                        "observations": [
                            "Runtime session flow shows staged execution.",
                            "The runtime has explicit session lifecycle transitions."
                        ],
                        "supporting_evidence": [
                            "runtime/session.py exposes session execution stages.",
                            "core/kernel.py governs initialization and lifecycle operations."
                        ],
                        "contradictory_evidence": [
                            "No concrete defect is established yet."
                        ],
                        "confidence": 0.71
                    },
                    {
                        "id": "C2",
                        "observations": [
                            "The end-to-end flight tests assert runtime trace behavior."
                        ],
                        "supporting_evidence": [
                            "tests/test_end_to_end_flight.py checks stage ordering and flight behavior."
                        ],
                        "contradictory_evidence": [
                            "The tests themselves do not indicate a defect."
                        ],
                        "confidence": 0.43
                    },
                    {
                        "id": "C3",
                        "observations": [
                            "The kernel initialization path is part of the runtime contract surface."
                        ],
                        "supporting_evidence": [
                            "core/kernel.py initializes runtime state and dependencies."
                        ],
                        "contradictory_evidence": [
                            "No direct defect is yet observed."
                        ],
                        "confidence": 0.58
                    }
                ]
            }
            return ChatResponse(
                content=json.dumps(candidates_payload),
                tool_calls=[]
            )

        last_msg = request.messages[-1]
        if last_msg["role"] == "assistant":
            return ChatResponse(
                content=(
                    "Ranked candidates: C1, C3, C2. "
                    "Reasoning: C1 has the strongest direct evidence from runtime execution flow, C3 is a secondary lifecycle candidate, and C2 is more test-definition oriented. "
                    "Action threshold: insufficient evidence to cross from candidate selection to a concrete fix. "
                    "Decision: ABSTAIN."
                )
            )
        return ChatResponse(content="No selection made.")


def build_prompt() -> str:
    return (
        "You are given a candidate set produced from repository evidence. Rank the candidates, explain the ranking, "
        "state the confidence level, determine whether the evidence crosses the action threshold, and choose ACT or ABSTAIN."
    )


async def run_target_selection_harness(session_id: str | None = None, output_dir: Path | None = None) -> dict:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    resolved_session_id = session_id or f"blind_e2e_selection_{timestamp}"
    resolved_output_dir = output_dir or Path(__file__).resolve().parent
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    recorder = FlightRecorder(session_id=resolved_session_id, log_dir=resolved_output_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    await runtime.initialize()
    await runtime.register_provider(TargetSelectionHarnessProvider())
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="blind_e2e_target_selection",
        provider_id="blind_e2e_target_selection_provider",
        model_name="mock-flight",
        capabilities=[Capability.CHAT, Capability.TOOLS],
    )
    session = runtime.create_session(ctx)
    response = await session.send_message(build_prompt())

    events = recorder.get_events()
    stages = [event["payload"].get("stage") for event in events if event["event_type"] == "flight_stage"]

    artifact = {
        "experiment_id": "BLIND-E2E-006",
        "title": "Target Selection Blind Flight",
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
    result = asyncio.run(run_target_selection_harness())
    print("Target selection harness completed.")
    print(f"Artifact: {result['artifact_path']}")
    print(f"Stages: {result['stages']}")
    print(f"Response: {result['response']}")
