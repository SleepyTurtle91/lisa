import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.core.context import SessionContext, Capability
from lisa.core.kernel import LisaRuntime
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool


class E2EGuardianHarnessProvider(BaseProvider):
    def __init__(self, scenario: str) -> None:
        self._turn = 0
        self._scenario = scenario

    @property
    def id(self) -> str:
        return "e2e_guardian_harness_provider"

    @property
    def name(self) -> str:
        return "E2E Guardian Harness Provider"

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
                            "arguments": {"path": "/home/user/Projects/lisa/core/kernel.py"},
                        }
                    }
                ],
            )

        last_msg = request.messages[-1]
        if last_msg["role"] == "tool":
            if self._scenario == "strong":
                candidate_payload = {
                    "candidates": [
                        {
                            "id": "kernel-initialization",
                            "confidence": 0.88,
                            "support": 6,
                            "contradictions": 0,
                            "notes": "The runtime initialization path and provider registration flow are directly observable in core/kernel.py."
                        },
                        {
                            "id": "speculative-bridge",
                            "confidence": 0.21,
                            "support": 1,
                            "contradictions": 2,
                            "notes": "A weaker hypothesis with no direct contract evidence."
                        }
                    ]
                }
            else:
                candidate_payload = {
                    "candidates": [
                        {
                            "id": "weak-target",
                            "confidence": 0.41,
                            "support": 2,
                            "contradictions": 3,
                            "notes": "Partial observations but no concrete defect signature."
                        },
                        {
                            "id": "competing-guess",
                            "confidence": 0.39,
                            "support": 2,
                            "contradictions": 3,
                            "notes": "Competing weak hypotheses with no decisive evidence."
                        }
                    ]
                }
            return ChatResponse(content=json.dumps(candidate_payload), tool_calls=[])

        return ChatResponse(content="No evidence produced.")


def derive_guardian_decision(candidate_payload: Dict[str, Any]) -> Dict[str, Any]:
    candidates = candidate_payload.get("candidates", [])
    if not candidates:
        return {
            "decision": "ABSTAIN",
            "confidence": 0.0,
            "guardian_confidence": 0.0,
            "evidence_confidence": 0.0,
            "selection_confidence": 0.0,
            "decision_reason": "No candidates provided.",
            "supporting_evidence_ids": [],
            "contradictory_evidence_ids": [],
        }

    strong = [c for c in candidates if c.get("confidence", 0.0) >= 0.7 and c.get("support", 0) >= 4 and c.get("contradictions", 0) == 0]
    weak = [c for c in candidates if c.get("confidence", 0.0) < 0.5 or c.get("contradictions", 0) >= 2]

    max_confidence = max((c.get("confidence", 0.0) for c in candidates), default=0.0)
    total_support = sum(c.get("support", 0) for c in candidates)
    total_contradictions = sum(c.get("contradictions", 0) for c in candidates)
    support_score = min(1.0, total_support / (6.0 * max(1, len(candidates))))
    contradiction_score = max(0.0, 1.0 - (total_contradictions / (4.0 * max(1, len(candidates)))))
    evidence_confidence = min(1.0, 0.5 * max_confidence + 0.3 * support_score + 0.2 * contradiction_score)

    supporting_evidence_ids = [c["id"] for c in candidates if c.get("confidence", 0.0) >= 0.7 and c.get("support", 0) >= 4]
    contradictory_evidence_ids = [c["id"] for c in candidates if c.get("contradictions", 0) >= 2]

    dominant_strong = bool(strong) and (max_confidence >= 0.7) and (len(strong) >= 1) and not any(c.get("confidence", 0.0) >= 0.7 and c.get("contradictions", 0) >= 2 for c in candidates)

    if dominant_strong:
        return {
            "decision": "ACT",
            "confidence": evidence_confidence,
            "guardian_confidence": 0.9,
            "evidence_confidence": evidence_confidence,
            "selection_confidence": max_confidence,
            "decision_reason": "A dominant candidate has strong support and no decisive contradictions.",
            "supporting_evidence_ids": supporting_evidence_ids,
            "contradictory_evidence_ids": contradictory_evidence_ids,
        }
    if weak and not strong:
        return {
            "decision": "ABSTAIN",
            "confidence": evidence_confidence,
            "guardian_confidence": 0.84,
            "evidence_confidence": evidence_confidence,
            "selection_confidence": max_confidence,
            "decision_reason": "Evidence is weak or contradictory.",
            "supporting_evidence_ids": supporting_evidence_ids,
            "contradictory_evidence_ids": contradictory_evidence_ids,
        }
    return {
        "decision": "ABSTAIN",
        "confidence": evidence_confidence,
        "guardian_confidence": 0.72,
        "evidence_confidence": evidence_confidence,
        "selection_confidence": max_confidence,
        "decision_reason": "Evidence is mixed; no decisive threshold is met.",
        "supporting_evidence_ids": supporting_evidence_ids,
        "contradictory_evidence_ids": contradictory_evidence_ids,
    }


async def run_e2e_guardian_case(scenario: str, session_id: str | None = None, output_dir: Path | None = None) -> Dict[str, Any]:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    resolved_session_id = session_id or f"e2e_guardian_{scenario}_{timestamp}"
    resolved_output_dir = output_dir or Path(__file__).resolve().parent
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    recorder = FlightRecorder(session_id=resolved_session_id, log_dir=resolved_output_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    await runtime.initialize()
    await runtime.register_provider(E2EGuardianHarnessProvider(scenario=scenario))
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="e2e_guardian_chain",
        provider_id="e2e_guardian_harness_provider",
        model_name="mock-flight",
        capabilities=[Capability.CHAT, Capability.TOOLS],
    )
    session = runtime.create_session(ctx)
    response = await session.send_message(
        "Inspect the repository evidence, identify a viable engineering target, and decide whether to ACT or ABSTAIN."
    )

    try:
        candidate_payload = json.loads(response)
    except json.JSONDecodeError:
        candidate_payload = {"candidates": []}

    guardian = derive_guardian_decision(candidate_payload)

    result = {
        "experiment_id": "E2E-Guardian-001",
        "title": "Perception-to-Authorization",
        "scenario": scenario,
        "timestamp": datetime.now().isoformat(),
        "session_id": resolved_session_id,
        "prompt": "Inspect the repository evidence, identify a viable engineering target, and decide whether to ACT or ABSTAIN.",
        "response": response,
        "candidate_payload": candidate_payload,
        "guardian_decision": guardian,
        "events": recorder.get_events(),
    }

    artifact_path = resolved_output_dir / f"{resolved_session_id}.json"
    artifact_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    await runtime.shutdown()
    return result


async def run_e2e_guardian_chain(session_id: str | None = None, output_dir: Path | None = None) -> Dict[str, Any]:
    strong_case = await run_e2e_guardian_case("strong", session_id=session_id, output_dir=output_dir)
    weak_case = await run_e2e_guardian_case("weak", session_id=None, output_dir=output_dir)
    return {
        "experiment_id": "E2E-Guardian-001",
        "title": "Perception-to-Authorization",
        "timestamp": datetime.now().isoformat(),
        "cases": [strong_case, weak_case],
    }


if __name__ == "__main__":
    artifact = asyncio.run(run_e2e_guardian_chain())
    print(json.dumps(artifact, indent=2))
