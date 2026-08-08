import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lisa.core.context import SessionContext, Capability
from lisa.core.kernel import LisaRuntime
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool
import urllib.request


ORIGINAL_PROMPT = (
    "You are given a candidate set produced from repository evidence. "
    "Rank the candidates, explain the ranking, state the confidence level, "
    "determine whether the evidence crosses the action threshold, and choose ACT or ABSTAIN."
)

ORIGINAL_CANDIDATES = {
    "candidates": [
        {
            "id": "C1",
            "observations": [
                "Runtime session flow shows staged execution.",
                "The runtime has explicit session lifecycle transitions.",
            ],
            "supporting_evidence": [
                "runtime/session.py exposes session execution stages.",
                "core/kernel.py governs initialization and lifecycle operations.",
            ],
            "contradictory_evidence": ["No concrete defect is established yet."],
            "confidence": 0.71,
        },
        {
            "id": "C2",
            "observations": ["The end-to-end flight tests assert runtime trace behavior."],
            "supporting_evidence": [
                "tests/test_end_to_end_flight.py checks stage ordering and flight behavior."
            ],
            "contradictory_evidence": ["The tests themselves do not indicate a defect."],
            "confidence": 0.43,
        },
        {
            "id": "C3",
            "observations": [
                "The kernel initialization path is part of the runtime contract surface."
            ],
            "supporting_evidence": ["core/kernel.py initializes runtime state and dependencies."],
            "contradictory_evidence": ["No direct defect is yet observed."],
            "confidence": 0.58,
        },
    ]
}


def build_full_prompt(prompt: str, payload: dict) -> str:
    return f"{prompt}\n\nCandidate set:\n{json.dumps(payload, sort_keys=True)}"


class ReplayProvider(BaseProvider):
    @property
    def id(self) -> str:
        return "replay_failure_provider"

    @property
    def name(self) -> str:
        return "Replay Failure Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["qwen3:4b"],
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        payload = {
            "model": "qwen3:4b",
            "messages": request.messages,
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data.get("message", {})
            return ChatResponse(content=msg.get("content", ""), tool_calls=msg.get("tool_calls"), usage={})


def classify_response(response: str) -> str:
    text = (response or "").strip()
    lower = text.lower()
    if not text:
        return "empty"
    if lower.startswith("{") and '"candidates"' in lower:
        return "payload_echo"
    if lower.startswith("act") or lower.startswith("abstain"):
        return "act_abstain"
    if any(marker in lower for marker in ["c1", "c2", "c3"]):
        return "candidate_id"
    return "other"


async def run_direct_provider(full_prompt: str) -> dict:
    provider = ReplayProvider()
    request = ChatRequest(messages=[{"role": "user", "content": full_prompt}], model="qwen3:4b", temperature=0.7)
    response = await provider.chat(request)
    return {
        "mode": "direct_provider",
        "prompt": full_prompt,
        "response": response.content,
        "classification": classify_response(response.content),
        "timestamp": datetime.now().isoformat(),
    }


async def run_lisa_path(full_prompt: str) -> dict:
    recorder = FlightRecorder(session_id="replay_failure_condition_lisa", log_dir=Path(__file__).resolve().parent)
    runtime = LisaRuntime(flight_recorder=recorder)
    await runtime.initialize()
    await runtime.register_provider(ReplayProvider())
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="replay_failure_condition",
        provider_id="replay_failure_provider",
        model_name="qwen3:4b",
        capabilities=[Capability.CHAT, Capability.TOOLS],
    )
    session = runtime.create_session(ctx)
    response = await session.send_message(full_prompt)
    await runtime.shutdown()

    return {
        "mode": "lisa_runtime_path",
        "prompt": full_prompt,
        "response": response,
        "classification": classify_response(response),
        "events": recorder.get_events(),
        "timestamp": datetime.now().isoformat(),
    }


async def run_current_selection_path(full_prompt: str) -> dict:
    recorder = FlightRecorder(session_id="replay_failure_condition_current", log_dir=Path(__file__).resolve().parent)
    runtime = LisaRuntime(flight_recorder=recorder)
    await runtime.initialize()
    await runtime.register_provider(ReplayProvider())
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="replay_failure_condition_current",
        provider_id="replay_failure_provider",
        model_name="qwen3:4b",
        capabilities=[Capability.CHAT, Capability.TOOLS],
    )
    session = runtime.create_session(ctx)
    response = await session.send_message(full_prompt)
    await runtime.shutdown()

    return {
        "mode": "current_selection_path",
        "prompt": full_prompt,
        "response": response,
        "classification": classify_response(response),
        "events": recorder.get_events(),
        "timestamp": datetime.now().isoformat(),
    }


async def main() -> None:
    full_prompt = build_full_prompt(ORIGINAL_PROMPT, ORIGINAL_CANDIDATES)
    direct_result = await run_direct_provider(full_prompt)
    lisa_result = await run_lisa_path(full_prompt)
    current_result = await run_current_selection_path(full_prompt)

    artifact = {
        "experiment_id": "BLIND-E2E-014",
        "title": "Failure Reproduction Replay",
        "timestamp": datetime.now().isoformat(),
        "original_prompt": ORIGINAL_PROMPT,
        "original_candidate_payload": ORIGINAL_CANDIDATES,
        "full_prompt": full_prompt,
        "results": {
            "direct_provider": direct_result,
            "lisa_runtime_path": lisa_result,
            "current_selection_path": current_result,
        },
    }

    out_path = Path(__file__).resolve().parent / f"replay_failure_condition_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
