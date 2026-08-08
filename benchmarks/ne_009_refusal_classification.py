import asyncio
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.core.context import Capability, SessionContext
from lisa.core.kernel import LisaRuntime
from lisa.providers.ollama.provider import OllamaProvider
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool


@dataclass
class RefusalCase:
    case_id: str
    prompt: str
    expected_shape: str


@dataclass
class RefusalObservation:
    case_id: str
    prompt: str
    expected_shape: str
    response: str
    tool_calls_count: int
    classifier_label: str
    classifier_reason: str
    recorder_file: str
    model_request_present: bool
    model_response_present: bool
    blocked_stage_present: bool
    guarding_stage_present: bool
    error: Optional[str] = None


def classify_response(response: str, tool_calls_count: int, blocked_stage_present: bool, guarding_stage_present: bool) -> tuple[str, str]:
    """Independent derived classification for NE-009 (not used by runtime)."""
    text = (response or "").strip().lower()

    if blocked_stage_present:
        return "ERROR", "blocked stage emitted by runtime"

    if guarding_stage_present:
        return "REFUSAL", "guarding stage emitted"

    if tool_calls_count > 0:
        return "NORMAL_CONCLUSION", "tool calls executed in session"

    if not text:
        return "ERROR", "empty response"

    refusal_tokens = [
        "cannot",
        "can't",
        "not able",
        "unable",
        "do not have",
        "don't have",
        "no appropriate tool",
        "not supported",
        "not a standard operation",
    ]
    abstain_tokens = [
        "not enough evidence",
        "need more evidence",
        "before proposing",
        "cannot safely",
        "insufficient evidence",
    ]
    clarify_tokens = [
        "would you like",
        "can you clarify",
        "need more information",
        "please provide",
        "which",
        "what exactly",
    ]

    if any(token in text for token in refusal_tokens):
        return "REFUSAL", "response text indicates capability refusal"
    if any(token in text for token in abstain_tokens):
        return "ABSTENTION", "response text indicates evidence abstention"
    if any(token in text for token in clarify_tokens) or "?" in text:
        return "REQUEST_FOR_CLARIFICATION", "response requests additional input"

    return "NORMAL_CONCLUSION", "response provides normal conclusion"


def extract_case_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    model_request_present = any(e.get("event_type") == "model_request" for e in events)
    model_response_present = any(e.get("event_type") == "model_response" for e in events)

    stages = [
        e.get("payload", {}).get("stage")
        for e in events
        if e.get("event_type") == "flight_stage"
    ]
    tool_calls_count = sum(1 for s in stages if s == "tool_call")

    return {
        "model_request_present": model_request_present,
        "model_response_present": model_response_present,
        "tool_calls_count": tool_calls_count,
        "blocked_stage_present": "blocked" in stages,
        "guarding_stage_present": "guarding_decision" in stages,
    }


async def run_case(case: RefusalCase, project_path: str, output_dir: Path) -> RefusalObservation:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne009_{case.case_id}_{timestamp}"

    recorder = FlightRecorder(session_id=session_id, log_dir=output_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    try:
        await runtime.initialize()
        await runtime.register_provider(OllamaProvider())
        runtime.tool_registry.register(ReadFileTool())

        ctx = SessionContext(
            project_path=project_path,
            workspace_name="ne_009_refusal_classification",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )
        session = runtime.create_session(ctx)
        response = await session.send_message(case.prompt)

        events = recorder.get_events()
        metrics = extract_case_metrics(events)
        label, reason = classify_response(
            response=response,
            tool_calls_count=metrics["tool_calls_count"],
            blocked_stage_present=metrics["blocked_stage_present"],
            guarding_stage_present=metrics["guarding_stage_present"],
        )

        return RefusalObservation(
            case_id=case.case_id,
            prompt=case.prompt,
            expected_shape=case.expected_shape,
            response=response,
            tool_calls_count=metrics["tool_calls_count"],
            classifier_label=label,
            classifier_reason=reason,
            recorder_file=str(recorder.log_file),
            model_request_present=metrics["model_request_present"],
            model_response_present=metrics["model_response_present"],
            blocked_stage_present=metrics["blocked_stage_present"],
            guarding_stage_present=metrics["guarding_stage_present"],
        )
    except Exception as exc:
        return RefusalObservation(
            case_id=case.case_id,
            prompt=case.prompt,
            expected_shape=case.expected_shape,
            response="",
            tool_calls_count=0,
            classifier_label="ERROR",
            classifier_reason="case execution failed",
            recorder_file=str(recorder.log_file),
            model_request_present=False,
            model_response_present=False,
            blocked_stage_present=False,
            guarding_stage_present=False,
            error=str(exc),
        )
    finally:
        try:
            await runtime.shutdown()
        except Exception:
            pass


async def run_experiment(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_output_dir = output_dir or Path(__file__).resolve().parent
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    cases = [
        RefusalCase("C1", "define retails project", "capability_refusal"),
        RefusalCase("C2", "create a purchase order workflow in this project without writing files", "capability_refusal_or_clarify"),
        RefusalCase("C3", "fix the most critical bug in the project without reading any files", "abstention_or_refusal"),
        RefusalCase("C4", "read BOOT.md and summarize the smoke sequence", "normal_conclusion"),
        RefusalCase("C5", "what should I fix?", "request_for_clarification_or_abstention"),
        RefusalCase("C6", "read boot.md", "filesystem_failure_path"),
    ]

    observations: List[RefusalObservation] = []
    for case in cases:
        obs = await run_case(case=case, project_path=project_path, output_dir=resolved_output_dir)
        observations.append(obs)

    counts: Dict[str, int] = {}
    for obs in observations:
        counts[obs.classifier_label] = counts.get(obs.classifier_label, 0) + 1

    artifact = {
        "experiment_id": "NE-009",
        "title": "Refusal Classification Baseline",
        "timestamp": datetime.now().isoformat(),
        "project_path": project_path,
        "model": "qwen3:1.7b",
        "provider": "ollama",
        "cases": [asdict(o) for o in observations],
        "classification_counts": counts,
        "notes": [
            "Raw runtime events remain in per-case JSONL files.",
            "This artifact is a derived classification dataset for renderer semantics work.",
            "No activity-renderer logic is changed by this experiment harness.",
        ],
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    artifact_path = resolved_output_dir / f"ne_009_refusal_classification_{ts}.json"
    with open(artifact_path, "w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2)

    return {
        "artifact_path": str(artifact_path),
        "classification_counts": counts,
        "cases": len(observations),
    }


if __name__ == "__main__":
    result = asyncio.run(run_experiment(project_path="/workspace/Projects/retails"))
    print("NE-009 refusal classification baseline complete.")
    print(f"Artifact: {result['artifact_path']}")
    print(f"Cases: {result['cases']}")
    print(f"Counts: {result['classification_counts']}")
