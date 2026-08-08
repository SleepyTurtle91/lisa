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
        return "selection_ladder_provider"

    @property
    def name(self) -> str:
        return "Selection Ladder Provider"

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


async def run_case(case: dict) -> dict:
    provider = LadderProvider()
    prompt = case["prompt"]
    candidate_payload = case["candidate_payload"]
    full_prompt = f"{prompt}\n\nCandidate set:\n{json.dumps(candidate_payload, sort_keys=True)}"

    recorder = FlightRecorder(session_id=f"selection_ladder_{case['id']}", log_dir=Path(__file__).resolve().parent)
    runtime = LisaRuntime(flight_recorder=recorder)
    await runtime.initialize()
    await runtime.register_provider(provider)
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="selection_ladder",
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
        "prompt": prompt,
        "candidate_payload": candidate_payload,
        "full_prompt": full_prompt,
        "response": response,
        "events": recorder.get_events(),
        "timestamp": datetime.now().isoformat(),
    }


async def main() -> None:
    cases = [
        {
            "id": "S-001",
            "title": "Deterministic",
            "prompt": "Select the candidate with the strongest evidence. Return its ID only.",
            "candidate_payload": {
                "candidates": [
                    {"id": "A", "confidence": 0.90, "support": 5, "contradictions": 0},
                    {"id": "B", "confidence": 0.40, "support": 2, "contradictions": 3},
                ]
            },
        },
        {
            "id": "S-002",
            "title": "Balanced",
            "prompt": "Select the candidate with the strongest evidence. Return its ID only.",
            "candidate_payload": {
                "candidates": [
                    {"id": "A", "confidence": 0.72, "support": 4, "contradictions": 1},
                    {"id": "B", "confidence": 0.70, "support": 4, "contradictions": 1},
                ]
            },
        },
        {
            "id": "S-003",
            "title": "Contradictory",
            "prompt": "Select the candidate with the strongest evidence. Return its ID only.",
            "candidate_payload": {
                "candidates": [
                    {"id": "A", "confidence": 0.68, "support": 5, "contradictions": 3},
                    {"id": "B", "confidence": 0.67, "support": 3, "contradictions": 1},
                ]
            },
        },
        {
            "id": "S-004",
            "title": "Multi Candidate",
            "prompt": "Select the candidate with the strongest evidence. Return its ID only.",
            "candidate_payload": {
                "candidates": [
                    {"id": "A", "confidence": 0.86, "support": 7, "contradictions": 1},
                    {"id": "B", "confidence": 0.82, "support": 6, "contradictions": 2},
                    {"id": "C", "confidence": 0.79, "support": 5, "contradictions": 0},
                ]
            },
        },
        {
            "id": "S-005",
            "title": "Engineering Candidates",
            "prompt": "Select the candidate with the strongest evidence. Return its ID only.",
            "candidate_payload": {
                "candidates": [
                    {"id": "session-context", "confidence": 0.83, "support": 6, "contradictions": 1, "notes": "runtime/session contract"},
                    {"id": "provider-registry", "confidence": 0.81, "support": 5, "contradictions": 2, "notes": "duplicate provider registration"},
                    {"id": "tool-dispatch", "confidence": 0.79, "support": 5, "contradictions": 0, "notes": "project-relative path resolution"},
                ]
            },
        },
    ]

    results = []
    for case in cases:
        results.append(await run_case(case))

    artifact = {
        "experiment_id": "BLIND-E2E-012",
        "title": "Selection Complexity Ladder",
        "timestamp": datetime.now().isoformat(),
        "results": results,
    }
    out_path = Path(__file__).resolve().parent / f"selection_complexity_ladder_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
