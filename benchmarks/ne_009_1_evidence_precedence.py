import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CaseSemanticResult:
    case_id: str
    prompt: str
    expected_shape: str
    baseline_label: str
    recorder_file: str
    stage_sequence: List[str]
    signals: Dict[str, Any]
    model_response_class: str
    predicted_operator_state: str
    precedence_reason: str


def classify_model_response_text(text: str) -> Tuple[str, str]:
    lower = (text or "").strip().lower()
    if not lower:
        return "EMPTY", "no model response content"

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
        "i would need more evidence",
    ]
    clarify_tokens = [
        "would you like",
        "can you clarify",
        "need more information",
        "please provide",
        "what do you mean",
        "what should",
    ]

    if any(token in lower for token in refusal_tokens):
        return "REFUSAL", "response contains refusal token"
    if any(token in lower for token in abstain_tokens):
        return "ABSTENTION", "response contains abstention token"
    if any(token in lower for token in clarify_tokens) or "?" in lower:
        return "REQUEST_FOR_CLARIFICATION", "response requests clarification"
    return "NORMAL_CONCLUSION", "response contains no refusal/clarification markers"


def load_jsonl_events(path: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue
    return events


def derive_signals(events: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str], str]:
    stages = [
        e.get("payload", {}).get("stage")
        for e in events
        if e.get("event_type") == "flight_stage"
    ]

    tool_result_events = [
        e for e in events
        if e.get("event_type") == "flight_stage" and e.get("payload", {}).get("stage") == "tool_result"
    ]
    tool_result_successes = [bool(e.get("payload", {}).get("success")) for e in tool_result_events]

    blocked_reasons = [
        e.get("payload", {}).get("reason", "")
        for e in events
        if e.get("event_type") == "flight_stage" and e.get("payload", {}).get("stage") == "blocked"
    ]

    model_responses = [
        e.get("payload", {}).get("content", "")
        for e in events
        if e.get("event_type") == "model_response"
    ]
    final_model_response = model_responses[-1] if model_responses else ""

    signals = {
        "has_blocked_stage": "blocked" in stages,
        "has_guarding_stage": "guarding_decision" in stages,
        "has_tool_call_stage": "tool_call" in stages,
        "tool_result_total": len(tool_result_events),
        "tool_result_any_failure": any(s is False for s in tool_result_successes),
        "tool_result_any_success": any(s is True for s in tool_result_successes),
        "has_model_request": any(e.get("event_type") == "model_request" for e in events),
        "has_model_response": any(e.get("event_type") == "model_response" for e in events),
        "blocked_reasons": blocked_reasons,
    }
    return signals, [s for s in stages if s], final_model_response


def classify_operator_state(signals: Dict[str, Any], response_text: str) -> Tuple[str, str, str]:
    model_class, model_reason = classify_model_response_text(response_text)

    # Evidence precedence: stronger runtime evidence dominates weaker linguistic evidence.
    if signals["has_blocked_stage"]:
        return "BLOCKED", "explicit blocked stage present", model_class

    if signals["tool_result_any_failure"] and signals["has_guarding_stage"]:
        return "BLOCKED", "failed tool result with guarding decision", model_class

    if signals["tool_result_any_failure"]:
        return "ERROR", "failed tool result without blocked stage", model_class

    if signals["has_guarding_stage"]:
        return "GUARDING", "explicit guarding stage present", model_class

    # Model-only interpretation applies only when stronger stage/tool evidence is absent.
    if model_class == "REFUSAL":
        return "GUARDING", f"model-only refusal classification ({model_reason})", model_class
    if model_class == "ABSTENTION":
        return "GUARDING", f"model-only abstention classification ({model_reason})", model_class
    if model_class == "REQUEST_FOR_CLARIFICATION":
        return "CLARIFYING", f"model-only clarification classification ({model_reason})", model_class

    if signals["has_model_response"]:
        return "COMPLETED", "model response present with no stronger blocking evidence", model_class

    return "UNKNOWN", "insufficient evidence for terminal classification", model_class


def run_precedence_analysis(dataset_path: Path, output_dir: Optional[Path] = None) -> Path:
    with open(dataset_path, "r", encoding="utf-8") as handle:
        dataset = json.load(handle)

    results: List[CaseSemanticResult] = []
    state_counts: Dict[str, int] = {}

    for case in dataset.get("cases", []):
        recorder_file = Path(case["recorder_file"])
        events = load_jsonl_events(recorder_file)
        signals, stage_sequence, final_model_response = derive_signals(events)

        predicted_state, precedence_reason, model_response_class = classify_operator_state(
            signals=signals,
            response_text=final_model_response,
        )

        state_counts[predicted_state] = state_counts.get(predicted_state, 0) + 1

        results.append(
            CaseSemanticResult(
                case_id=case["case_id"],
                prompt=case["prompt"],
                expected_shape=case.get("expected_shape", ""),
                baseline_label=case.get("classifier_label", ""),
                recorder_file=str(recorder_file),
                stage_sequence=stage_sequence,
                signals=signals,
                model_response_class=model_response_class,
                predicted_operator_state=predicted_state,
                precedence_reason=precedence_reason,
            )
        )

    summary = {
        "experiment_id": "NE-009.1",
        "title": "Evidence Precedence Semantic Classification",
        "timestamp": datetime.now().isoformat(),
        "source_dataset": str(dataset_path),
        "source_case_count": len(results),
        "precedence_contract": [
            "Explicit blocked stage",
            "Failed tool result + guarding decision",
            "Failed tool result",
            "Explicit guarding stage",
            "Model-only refusal/abstention/clarification",
            "Generic completion",
        ],
        "predicted_operator_state_counts": state_counts,
        "cases": [asdict(r) for r in results],
    }

    resolved_output_dir = output_dir or dataset_path.parent
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_path = resolved_output_dir / f"ne_009_1_evidence_precedence_{ts}.json"

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    return output_path


def latest_dataset(bench_dir: Path) -> Path:
    candidates = sorted(bench_dir.glob("ne_009_refusal_classification_*.json"))
    if not candidates:
        raise FileNotFoundError("No NE-009 baseline dataset found in benchmarks directory.")
    return candidates[-1]


if __name__ == "__main__":
    bench_dir = Path(__file__).resolve().parent
    source = latest_dataset(bench_dir)
    out = run_precedence_analysis(source)
    print("NE-009.1 evidence precedence analysis complete.")
    print(f"Source dataset: {source}")
    print(f"Artifact: {out}")
