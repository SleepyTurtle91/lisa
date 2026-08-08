import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.telemetry.activity_renderer import FlightConsole


EXPECTED_MATRIX = {
    "C1": "CLARIFYING",
    "C2": "CLARIFYING",
    "C3": "GUARDING",
    "C4": "BLOCKED",
    "C5": "CLARIFYING",
    "C6": "BLOCKED",
}


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


def latest_case_trace(bench_dir: Path, case_id: str) -> Path:
    candidates = sorted(bench_dir.glob(f"ne009_{case_id}_*.jsonl"))
    if not candidates:
        raise FileNotFoundError(f"No trace found for {case_id}.")
    return candidates[-1]


def replay_case(case_id: str, trace_path: Path) -> Dict[str, Any]:
    events = load_jsonl_events(trace_path)
    output = io.StringIO()
    console = FlightConsole(project_name="retails", mode="compact", stream=output)

    for event in events:
        console.handle_event(event)

    expected = EXPECTED_MATRIX[case_id]
    observed = console.semantic_state
    return {
        "case_id": case_id,
        "trace_path": str(trace_path),
        "event_count": len(events),
        "expected_state": expected,
        "observed_state": observed,
        "pass": observed == expected,
        "semantic_reason": console.semantic_reason,
        "model_response_class": console.model_response_class,
    }


def run_replay(bench_dir: Path) -> Path:
    case_results: List[Dict[str, Any]] = []
    for case_id in sorted(EXPECTED_MATRIX.keys()):
        trace_path = latest_case_trace(bench_dir, case_id)
        case_results.append(replay_case(case_id, trace_path))

    passed = sum(1 for c in case_results if c["pass"])
    summary = {
        "experiment_id": "NE-009.2",
        "title": "Renderer Integration Replay Against NE-009.1 Contract v0.1",
        "timestamp": datetime.now().isoformat(),
        "contract_version": "NE-009.1 Evidence Precedence Contract v0.1",
        "cases_total": len(case_results),
        "cases_passed": passed,
        "cases_failed": len(case_results) - passed,
        "results": case_results,
    }

    out_path = bench_dir / f"ne_009_2_renderer_replay_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return out_path


if __name__ == "__main__":
    bench_dir = Path(__file__).resolve().parent
    artifact = run_replay(bench_dir)
    print("NE-009.2 renderer replay complete.")
    print(f"Artifact: {artifact}")
