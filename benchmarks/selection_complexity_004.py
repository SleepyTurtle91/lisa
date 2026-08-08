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


class LadderProvider(BaseProvider):
    @property
    def id(self) -> str:
        return "selection_complexity_provider"

    @property
    def name(self) -> str:
        return "Selection Complexity Provider"

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


def normalize_response(response: str) -> str:
    cleaned = (response or "").strip().upper()
    if cleaned.startswith("SELECT"):
        cleaned = cleaned.split()[-1]
    return cleaned


def classify_validity(response: str, expected: str, allow_abstain: bool = True) -> str:
    normalized = normalize_response(response)
    if allow_abstain and normalized in {"ABSTAIN", "NONE", "NONE OF THESE"}:
        return "valid_abstention"
    if normalized == expected.upper():
        return "valid_selection"
    return "invalid_selection"


async def run_case(case: dict) -> dict:
    provider = LadderProvider()
    prompt = case["prompt"]
    candidate_payload = case["candidate_payload"]
    full_prompt = f"{prompt}\n\nCandidate set:\n{json.dumps(candidate_payload, sort_keys=True)}"

    recorder = FlightRecorder(session_id=f"selection_complexity_004_{case['id']}", log_dir=Path(__file__).resolve().parent)
    runtime = LisaRuntime(flight_recorder=recorder)
    await runtime.initialize()
    await runtime.register_provider(provider)
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="selection_complexity_004",
        provider_id=provider.id,
        model_name="qwen3:4b",
        capabilities=[Capability.CHAT, Capability.TOOLS],
    )
    session = runtime.create_session(ctx)
    response = await session.send_message(full_prompt)
    await runtime.shutdown()

    return {
        "id": case["id"],
        "title": case["title"],
        "response": response,
        "normalized_response": normalize_response(response),
        "expected_selection": case["expected_selection"],
        "validity": classify_validity(response, case["expected_selection"], allow_abstain=case.get("allow_abstain", True)),
        "prompt": full_prompt,
        "candidate_payload": candidate_payload,
        "timestamp": datetime.now().isoformat(),
    }


async def main() -> None:
    case = {
        "id": "S-004",
        "title": "Multi-candidate overlap",
        "prompt": "Select the single best candidate. If the evidence is insufficient to justify a choice, return ABSTAIN. Return the ID only.",
        "expected_selection": "C",
        "allow_abstain": True,
        "candidate_payload": {
            "candidates": [
                {"id": "A", "confidence": 0.62, "support": 4, "contradictions": 2, "notes": "Partial validation but no execution evidence."},
                {"id": "B", "confidence": 0.59, "support": 4, "contradictions": 1, "notes": "Solid inspection but weaker cross-checks."},
                {"id": "C", "confidence": 0.71, "support": 5, "contradictions": 2, "notes": "Best overall evidence with one unresolved contradiction."},
                {"id": "D", "confidence": 0.58, "support": 3, "contradictions": 0, "notes": "Low volume evidence and no corroboration."},
            ]
        },
    }

    result = await run_case(case)
    artifact = {
        "experiment_id": "BLIND-E2E-013",
        "title": "Selection Complexity Ladder — Multi-candidate Overlap",
        "timestamp": datetime.now().isoformat(),
        "result": result,
    }
    out_path = Path(__file__).resolve().parent / f"selection_complexity_004_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
