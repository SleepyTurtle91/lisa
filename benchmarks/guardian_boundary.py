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


class GuardianProvider(BaseProvider):
    @property
    def id(self) -> str:
        return "guardian_boundary_provider"

    @property
    def name(self) -> str:
        return "Guardian Boundary Provider"

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


def normalize_decision(response: str) -> str:
    text = (response or "").strip().upper()
    if "ABSTAIN" in text:
        return "ABSTAIN"
    if "ACT" in text:
        return "ACT"
    return text


async def run_case(case: dict) -> dict:
    provider = GuardianProvider()
    full_prompt = f"{case['prompt']}\n\nCandidate set:\n{json.dumps(case['candidate_payload'], sort_keys=True)}"

    recorder = FlightRecorder(session_id=f"guardian_boundary_{case['id']}", log_dir=Path(__file__).resolve().parent)
    runtime = LisaRuntime(flight_recorder=recorder)
    await runtime.initialize()
    await runtime.register_provider(provider)
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="guardian_boundary",
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
        "expected": case["expected"],
        "response": response,
        "normalized_decision": normalize_decision(response),
        "prompt": full_prompt,
        "candidate_payload": case["candidate_payload"],
        "timestamp": datetime.now().isoformat(),
    }


async def main() -> None:
    cases = [
        {
            "id": "G-A",
            "title": "Sufficient evidence",
            "expected": "ACT",
            "prompt": "You are evaluating candidate engineering targets. If the evidence justifies a concrete action, return ACT. If the evidence is too weak or contradictory, return ABSTAIN. Return the decision only.",
            "candidate_payload": {
                "candidates": [
                    {
                        "id": "A",
                        "confidence": 0.88,
                        "support": 6,
                        "contradictions": 0,
                        "notes": "Direct runtime evidence, explicit failing behavior, and a concrete contract violation."
                    },
                    {
                        "id": "B",
                        "confidence": 0.21,
                        "support": 1,
                        "contradictions": 2,
                        "notes": "Vague conjecture without replication."
                    }
                ]
            },
        },
        {
            "id": "G-B",
            "title": "Insufficient evidence",
            "expected": "ABSTAIN",
            "prompt": "You are evaluating candidate engineering targets. If the evidence justifies a concrete action, return ACT. If the evidence is too weak or contradictory, return ABSTAIN. Return the decision only.",
            "candidate_payload": {
                "candidates": [
                    {
                        "id": "A",
                        "confidence": 0.41,
                        "support": 2,
                        "contradictions": 3,
                        "notes": "Partial observations but no concrete failure signature."
                    },
                    {
                        "id": "B",
                        "confidence": 0.39,
                        "support": 2,
                        "contradictions": 3,
                        "notes": "Competing weak hypotheses with no decisive evidence."
                    }
                ]
            },
        },
    ]

    results = []
    for case in cases:
        results.append(await run_case(case))

    artifact = {
        "experiment_id": "BLIND-E2E-015",
        "title": "Guardian Boundary",
        "timestamp": datetime.now().isoformat(),
        "results": results,
    }
    out_path = Path(__file__).resolve().parent / f"guardian_boundary_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
