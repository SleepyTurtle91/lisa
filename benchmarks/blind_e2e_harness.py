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


class BlindObjectiveHarnessProvider(BaseProvider):
    def __init__(self):
        self._turn = 0

    @property
    def id(self) -> str:
        return "blind_e2e_harness_provider"

    @property
    def name(self) -> str:
        return "Blind E2E Harness Provider"

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
        objective = request.messages[0]["content"] if request.messages else ""
        objective_lower = objective.lower()

        if self._turn == 1:
            if "provider" in objective_lower:
                target_path = "/home/user/Projects/lisa/providers/registry.py"
            elif "kernel" in objective_lower:
                target_path = "/home/user/Projects/lisa/core/kernel.py"
            else:
                target_path = "/home/user/Projects/lisa/runtime/session.py"
            return ChatResponse(
                content="",
                tool_calls=[
                    {
                        "function": {
                            "name": "read_file",
                            "arguments": {"path": target_path},
                        }
                    }
                ],
            )

        last_msg = request.messages[-1]
        if last_msg["role"] == "tool":
            return ChatResponse(
                content="I inspected the runtime contract-handling surface and found a likely boundary around session or runtime state transitions. I would need more evidence before proposing a minimal fix."
            )
        return ChatResponse(content="I did not find enough repository evidence to safely claim a fix target.")


def build_prompt() -> str:
    return (
        "Find a small defect in the runtime contract handling, fix it with the minimum necessary change, "
        "and verify the fix with tests. Do not modify unrelated behavior."
    )


async def run_blind_e2e_harness(session_id: str | None = None, output_dir: Path | None = None) -> dict:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    resolved_session_id = session_id or f"blind_e2e_{timestamp}"
    resolved_output_dir = output_dir or Path(__file__).resolve().parent
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    recorder = FlightRecorder(session_id=resolved_session_id, log_dir=resolved_output_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    await runtime.initialize()
    await runtime.register_provider(BlindObjectiveHarnessProvider())
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="blind_e2e_harness",
        provider_id="blind_e2e_harness_provider",
        model_name="mock-flight",
        capabilities=[Capability.CHAT, Capability.TOOLS],
    )
    session = runtime.create_session(ctx)
    response = await session.send_message(build_prompt())

    events = recorder.get_events()
    stages = [event["payload"].get("stage") for event in events if event["event_type"] == "flight_stage"]

    artifact = {
        "experiment_id": "BLIND-E2E-002",
        "title": "Ambiguous Objective Runtime Discovery Flight",
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
    result = asyncio.run(run_blind_e2e_harness())
    print("Blind objective harness completed.")
    print(f"Artifact: {result['artifact_path']}")
    print(f"Stages: {result['stages']}")
    print(f"Response: {result['response']}")
