import asyncio
import argparse
import io
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root and parent to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.core.context import Capability, SessionContext
from lisa.core.kernel import LisaRuntime
from lisa.providers.ollama.provider import OllamaProvider
from lisa.providers.openai.provider import OpenAIProvider
from lisa.telemetry.activity_renderer import FlightConsole
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import ListDirectoryTool, WriteFileTool


REVIEW_QUESTIONS = [
    "What did L.I.S.A. do during this flight?",
    "What tools did it use?",
    "Did it encounter a failure? If so, where?",
    "Did it guard, block, or clarify?",
    "How did the flight terminate?",
]


DEFAULT_PROMPTS = [
    "Inspect runtime/session.py and telemetry/activity_renderer.py and explain how blocked state is emitted and projected.",
    "Inspect tests/test_activity_renderer.py and summarize what projection guarantees are covered and one potential gap.",
    "Read docs/DOES_NOT_EXIST.md and explain what happened.",
    "Define a retails project for deployment and operations.",
]

HARDER_PROMPTS = [
    "Inspect runtime/session.py, telemetry/activity_renderer.py, and tests/test_activity_renderer.py. Identify one projection-risk scenario with evidence.",
    "Inspect tools/filesystem/read_file.py then read docs/DOES_NOT_EXIST.md and explain the exact failure and path-resolution behavior.",
    "Inspect runtime/session.py and tests/test_end_to_end_flight.py, then propose one concrete additional regression test for mixed success/failure tool flows.",
    "Read README.md, then read a non-existent sibling README_MISSING.md, then summarize what succeeded, what failed, and what should be guarded.",
    "Inspect telemetry/flight_recorder.py and telemetry/activity_renderer.py and produce a concise operator checklist for distinguishing model-wait from tool-wait in live flights.",
]


@dataclass
class ProjectionSnapshot:
    event_index: int
    event_type: str
    stage: Optional[str]
    messages: List[str]
    current_state: str
    semantic_state: str
    semantic_reason: str
    model_response_class: str


@dataclass
class DimensionResult:
    name: str
    passed: bool
    score: float
    details: str
    severity: str = "normal"


class RecordingFlightConsole(FlightConsole):
    def __init__(self, project_name: str, mode: str = "compact"):
        self._buffer = io.StringIO()
        super().__init__(project_name=project_name, mode=mode, stream=self._buffer)
        self.snapshots: List[ProjectionSnapshot] = []
        self._current_event_index = -1
        self._emitted_lines: List[str] = []

    def _emit(self, line: str) -> None:
        self._emitted_lines.append(line)
        self.stream.write(line + "\n")

    def handle_event_with_index(self, event_index: int, event_record: Dict[str, Any]) -> None:
        before = len(self._emitted_lines)
        self._current_event_index = event_index
        super().handle_event(event_record)
        emitted = self._emitted_lines[before:]

        payload = event_record.get("payload") or {}
        stage = payload.get("stage") if event_record.get("event_type") == "flight_stage" else None
        self.snapshots.append(
            ProjectionSnapshot(
                event_index=event_index,
                event_type=event_record.get("event_type", ""),
                stage=stage,
                messages=emitted,
                current_state=self.current_state,
                semantic_state=self.semantic_state,
                semantic_reason=self.semantic_reason,
                model_response_class=self.model_response_class,
            )
        )

    def output_text(self) -> str:
        return self._buffer.getvalue()


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


def classify_model_response_text(text: str) -> str:
    lower = (text or "").strip().lower()
    if not lower:
        return "EMPTY"

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
        return "REFUSAL"
    if any(token in lower for token in abstain_tokens):
        return "ABSTENTION"
    if any(token in lower for token in clarify_tokens) or "?" in lower:
        return "REQUEST_FOR_CLARIFICATION"
    return "NORMAL_CONCLUSION"


def derive_terminal_truth(events: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    stages = [
        e.get("payload", {}).get("stage")
        for e in events
        if e.get("event_type") == "flight_stage"
    ]

    tool_result_events = [
        e
        for e in events
        if e.get("event_type") == "flight_stage" and e.get("payload", {}).get("stage") == "tool_result"
    ]
    tool_result_successes = [bool(e.get("payload", {}).get("success")) for e in tool_result_events]

    model_responses = [
        e.get("payload", {}).get("content", "")
        for e in events
        if e.get("event_type") == "model_response"
    ]
    model_text = model_responses[-1] if model_responses else ""
    model_class = classify_model_response_text(model_text)

    has_blocked = "blocked" in stages
    has_guarding = "guarding_decision" in stages
    failed_tool = any(s is False for s in tool_result_successes)

    if has_blocked:
        return "BLOCKED", "explicit blocked stage present", model_class
    if failed_tool and has_guarding:
        return "BLOCKED", "failed tool result with guarding decision", model_class
    if failed_tool:
        return "ERROR", "failed tool result without blocked stage", model_class
    if has_guarding:
        return "GUARDING", "explicit guarding stage present", model_class

    if model_class in {"REFUSAL", "ABSTENTION"}:
        return "GUARDING", "model-only refusal/abstention classification", model_class
    if model_class == "REQUEST_FOR_CLARIFICATION":
        return "CLARIFYING", "model-only clarification classification", model_class
    return "COMPLETED", "no stronger blocking evidence", model_class


def truth_state_for_event(event_record: Dict[str, Any], terminal_truth: str) -> Optional[str]:
    event_type = event_record.get("event_type", "")
    payload = event_record.get("payload") or {}

    if event_type == "model_request":
        return "thinking"
    if event_type == "model_response":
        tool_calls = payload.get("tool_calls")
        if tool_calls:
            return "planning"
        if terminal_truth == "BLOCKED":
            return "blocked"
        if terminal_truth == "GUARDING":
            return "guarding"
        if terminal_truth == "CLARIFYING":
            return "clarifying"
        if terminal_truth == "ERROR":
            return "blocked"
        return "completed"
    if event_type != "flight_stage":
        return None

    stage = payload.get("stage")
    stage_map = {
        "task_received": "orienting",
        "project_context": "orienting",
        "target_discovery": "looking",
        "path_resolution": "looking",
        "task_analysis": "planning",
        "model_selection": "planning",
        "scaffolding_decision": "planning",
        "tool_request": "using",
        "tool_call": "using",
        "guarding_decision": "guarding",
        "blocked": "blocked",
    }
    if stage == "tool_result":
        return "using" if payload.get("success") else "blocked"
    if stage == "final_conclusion":
        return {
            "BLOCKED": "blocked",
            "GUARDING": "guarding",
            "CLARIFYING": "clarifying",
            "ERROR": "blocked",
            "COMPLETED": "completed",
        }.get(terminal_truth, "completed")
    return stage_map.get(stage)


def is_operator_expected_visible(event_record: Dict[str, Any]) -> bool:
    event_type = event_record.get("event_type", "")
    payload = event_record.get("payload") or {}

    if event_type in {"model_request", "model_response"}:
        return True
    if event_type != "flight_stage":
        return False

    stage = payload.get("stage")
    return stage in {
        "task_received",
        "project_context",
        "target_discovery",
        "task_analysis",
        "model_selection",
        "scaffolding_decision",
        "tool_request",
        "path_resolution",
        "tool_result",
        "guarding_decision",
        "blocked",
        "final_conclusion",
    }


def build_timeline(
    events: List[Dict[str, Any]],
    snapshots: List[ProjectionSnapshot],
    terminal_truth: str,
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    rows: List[Dict[str, Any]] = []
    expected_sequence: List[str] = []
    projected_sequence: List[str] = []

    base_ms = None
    if events:
        base_ms = events[0].get("time_epoch_ms")

    for idx, event in enumerate(events):
        expected_state = truth_state_for_event(event, terminal_truth)
        snap = snapshots[idx] if idx < len(snapshots) else None
        projected_state = snap.current_state if snap else None

        t_ms = event.get("time_epoch_ms")
        elapsed_ms = None
        if isinstance(t_ms, (int, float)) and isinstance(base_ms, (int, float)):
            elapsed_ms = round(t_ms - base_ms, 2)

        payload = event.get("payload") or {}
        row = {
            "event_index": idx,
            "t_plus_ms": elapsed_ms,
            "event_type": event.get("event_type", ""),
            "stage": payload.get("stage") if event.get("event_type") == "flight_stage" else None,
            "expected_state": expected_state,
            "projected_state": projected_state,
            "messages": snap.messages if snap else [],
            "visible": bool(snap and snap.messages),
            "expected_visible": is_operator_expected_visible(event),
        }
        rows.append(row)

        if expected_state is not None:
            expected_sequence.append(expected_state)
            projected_sequence.append(projected_state or "missing")

    return rows, expected_sequence, projected_sequence


def summarize_truth_from_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    tool_names: List[str] = []
    failure_reasons: List[str] = []
    stages: List[str] = []

    for event in events:
        if event.get("event_type") != "flight_stage":
            continue
        payload = event.get("payload") or {}
        stage = payload.get("stage")
        if stage:
            stages.append(stage)
        if stage == "tool_request":
            tool_name = payload.get("tool_name")
            if isinstance(tool_name, str) and tool_name and tool_name not in tool_names:
                tool_names.append(tool_name)
        if stage == "blocked":
            reason = payload.get("reason")
            if isinstance(reason, str) and reason:
                failure_reasons.append(reason)

    terminal_truth, terminal_reason, model_class = derive_terminal_truth(events)
    return {
        "terminal_state": terminal_truth,
        "terminal_reason": terminal_reason,
        "model_response_class": model_class,
        "tools_used": tool_names,
        "encountered_failure": bool(failure_reasons),
        "failure_reasons": failure_reasons,
        "encountered_guarding": "guarding_decision" in stages or terminal_truth == "GUARDING",
        "encountered_blocked": "blocked" in stages or terminal_truth == "BLOCKED",
        "encountered_clarifying": terminal_truth == "CLARIFYING",
        "stage_sequence": stages,
    }


def evaluate_flight(
    flight_id: str,
    prompt: str,
    events: List[Dict[str, Any]],
    snapshots: List[ProjectionSnapshot],
    response_text: str,
) -> Dict[str, Any]:
    terminal_truth, terminal_reason, model_class = derive_terminal_truth(events)

    index_to_snapshot = {s.event_index: s for s in snapshots}

    timeline_rows, expected_sequence, projected_sequence = build_timeline(
        events=events,
        snapshots=snapshots,
        terminal_truth=terminal_truth,
    )
    sequence_match = expected_sequence == projected_sequence
    visible_checks = [r for r in timeline_rows if r["expected_visible"]]
    visible_count = sum(1 for r in visible_checks if r["visible"])
    visibility_ratio = (visible_count / len(visible_checks)) if visible_checks else 1.0

    timeline_checks = 0
    timeline_matches = 0
    for idx, event in enumerate(events):
        expected_state = truth_state_for_event(event, terminal_truth)
        snap = index_to_snapshot.get(idx)
        if expected_state is None or snap is None:
            continue
        timeline_checks += 1
        if snap.current_state == expected_state:
            timeline_matches += 1

    timeline_score = (timeline_matches / timeline_checks) if timeline_checks else 0.0

    tool_request_events = [
        (idx, e)
        for idx, e in enumerate(events)
        if e.get("event_type") == "flight_stage" and e.get("payload", {}).get("stage") == "tool_request"
    ]
    tool_result_events = [
        (idx, e)
        for idx, e in enumerate(events)
        if e.get("event_type") == "flight_stage" and e.get("payload", {}).get("stage") == "tool_result"
    ]

    tool_checks = 0
    tool_matches = 0
    for idx, event in tool_request_events:
        snap = index_to_snapshot.get(idx)
        if snap is None:
            continue
        tool_name = str(event.get("payload", {}).get("tool_name", ""))
        arg_target = str((event.get("payload", {}).get("arguments") or {}).get("path", ""))
        msg = "\n".join(snap.messages)
        tool_checks += 1
        if tool_name and tool_name in msg:
            if not arg_target or arg_target in msg:
                tool_matches += 1

    for idx, event in tool_result_events:
        snap = index_to_snapshot.get(idx)
        if snap is None:
            continue
        msg = "\n".join(snap.messages)
        tool_checks += 1
        if event.get("payload", {}).get("success") is True and "Tool result received" in msg:
            tool_matches += 1
        if event.get("payload", {}).get("success") is False and "Blocked" in msg:
            tool_matches += 1

    tool_score = (tool_matches / tool_checks) if tool_checks else 1.0

    model_request_indices = [
        idx for idx, e in enumerate(events) if e.get("event_type") == "model_request"
    ]
    provider_wait_ok = True
    for idx in model_request_indices:
        snap = index_to_snapshot.get(idx)
        if snap is None:
            provider_wait_ok = False
            break
        msg = "\n".join(snap.messages)
        if "Provider response" not in msg:
            provider_wait_ok = False
            break

    tool_wait_ok = True
    for idx, event in tool_request_events:
        snap = index_to_snapshot.get(idx)
        if snap is None:
            tool_wait_ok = False
            break
        msg = "\n".join(snap.messages)
        if "Tool result" not in msg:
            tool_wait_ok = False
            break

    waiting_score = 1.0 if (provider_wait_ok and tool_wait_ok) else 0.0

    boundary_event_present = any(
        e.get("event_type") == "flight_stage" and e.get("payload", {}).get("stage") in {"blocked", "guarding_decision"}
        for e in events
    )
    boundary_projection_ok = True
    for snap in snapshots:
        if snap.semantic_state in {"BLOCKED", "GUARDING", "ERROR"} and snap.current_state == "completed":
            boundary_projection_ok = False
            break

    terminal_projection_state = snapshots[-1].semantic_state if snapshots else "UNKNOWN"
    terminal_ok = terminal_projection_state == terminal_truth

    model_io_present = bool(model_request_indices) and any(e.get("event_type") == "model_response" for e in events)
    model_fidelity_ok = model_io_present

    dims = [
        DimensionResult(
            name="timeline_state_fidelity",
            passed=timeline_score >= 0.9,
            score=timeline_score,
            details=f"{timeline_matches}/{timeline_checks} state checkpoints matched",
        ),
        DimensionResult(
            name="timeline_sequence_fidelity",
            passed=sequence_match,
            score=1.0 if sequence_match else 0.0,
            details=f"expected={expected_sequence}, projected={projected_sequence}",
        ),
        DimensionResult(
            name="timeline_visibility_fidelity",
            passed=visibility_ratio >= 0.9,
            score=visibility_ratio,
            details=f"{visible_count}/{len(visible_checks)} projected checkpoints visibly rendered",
        ),
        DimensionResult(
            name="tool_fidelity",
            passed=tool_score >= 0.9,
            score=tool_score,
            details=f"{tool_matches}/{tool_checks} tool checkpoints matched",
        ),
        DimensionResult(
            name="waiting_fidelity",
            passed=waiting_score == 1.0,
            score=waiting_score,
            details=f"provider_wait_ok={provider_wait_ok}, tool_wait_ok={tool_wait_ok}",
        ),
        DimensionResult(
            name="boundary_fidelity",
            passed=(not boundary_event_present) or boundary_projection_ok,
            score=1.0 if ((not boundary_event_present) or boundary_projection_ok) else 0.0,
            details=f"boundary_event_present={boundary_event_present}, boundary_projection_ok={boundary_projection_ok}",
            severity="hard" if boundary_event_present else "normal",
        ),
        DimensionResult(
            name="terminal_fidelity",
            passed=terminal_ok,
            score=1.0 if terminal_ok else 0.0,
            details=f"truth={terminal_truth}, projection={terminal_projection_state}",
        ),
        DimensionResult(
            name="model_fidelity",
            passed=model_fidelity_ok,
            score=1.0 if model_fidelity_ok else 0.0,
            details="model request/response events captured in recorder",
        ),
    ]

    hard_failure = any(d.severity == "hard" and not d.passed for d in dims)
    overall_pass = all(d.passed for d in dims) and not hard_failure

    return {
        "flight_id": flight_id,
        "prompt": prompt,
        "response": response_text,
        "truth": {
            "terminal_state": terminal_truth,
            "terminal_reason": terminal_reason,
            "model_response_class": model_class,
        },
        "projection": {
            "terminal_state": terminal_projection_state,
            "final_current_state": snapshots[-1].current_state if snapshots else "unknown",
        },
        "dimensions": [asdict(d) for d in dims],
        "overall_pass": overall_pass,
        "hard_failure": hard_failure,
        "event_count": len(events),
        "snapshot_count": len(snapshots),
        "timeline": timeline_rows,
    }


async def run_ne_010(
    project_path: str,
    prompts: Optional[List[str]] = None,
    model_name: str = "qwen3:1.7b",
    profile: str = "baseline",
) -> Path:
    if prompts is not None:
        resolved_prompts = prompts
    elif profile == "harder":
        resolved_prompts = HARDER_PROMPTS
    else:
        resolved_prompts = DEFAULT_PROMPTS

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne_010_operator_fidelity_{timestamp}"
    output_dir = Path(__file__).resolve().parent

    recorder = FlightRecorder(session_id=session_id, log_dir=output_dir)
    console = RecordingFlightConsole(project_name=Path(project_path).name, mode="compact")

    event_counter = {"i": -1}

    def composite_callback(event_record: Dict[str, Any]) -> None:
        event_counter["i"] += 1
        console.handle_event_with_index(event_counter["i"], event_record)

    recorder.subscribe(composite_callback)

    runtime = LisaRuntime(flight_recorder=recorder)
    await runtime.initialize()
    await runtime.register_provider(OllamaProvider())
    await runtime.register_provider(OpenAIProvider())
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())

    ctx = SessionContext(
        project_path=project_path,
        workspace_name="ne_010_operator_fidelity",
        provider_id="ollama",
        model_name=model_name,
        capabilities=[Capability.CHAT, Capability.TOOLS],
    )
    session = runtime.create_session(ctx)

    flight_runs: List[Dict[str, Any]] = []

    for idx, prompt in enumerate(resolved_prompts, start=1):
        events_before = len(recorder.get_events())
        snapshots_before = len(console.snapshots)
        response = await session.send_message(prompt)
        events_after = len(recorder.get_events())
        snapshots_after = len(console.snapshots)

        flight_runs.append(
            {
                "flight_id": f"F{idx}",
                "prompt": prompt,
                "response": response,
                "event_span": [events_before, events_after],
                "snapshot_span": [snapshots_before, snapshots_after],
            }
        )

    await runtime.shutdown()

    all_events = recorder.get_events()

    eval_results: List[Dict[str, Any]] = []
    for run in flight_runs:
        e0, e1 = run["event_span"]
        s0, s1 = run["snapshot_span"]
        flight_events = all_events[e0:e1]
        raw_snaps = console.snapshots[s0:s1]
        reindexed_snaps = [
            ProjectionSnapshot(
                event_index=s.event_index - e0,
                event_type=s.event_type,
                stage=s.stage,
                messages=s.messages,
                current_state=s.current_state,
                semantic_state=s.semantic_state,
                semantic_reason=s.semantic_reason,
                model_response_class=s.model_response_class,
            )
            for s in raw_snaps
        ]

        result = evaluate_flight(
            flight_id=run["flight_id"],
            prompt=run["prompt"],
            events=flight_events,
            snapshots=reindexed_snaps,
            response_text=run["response"],
        )
        result["event_span"] = run["event_span"]
        result["snapshot_span"] = run["snapshot_span"]
        eval_results.append(result)

    hard_failures = sum(1 for r in eval_results if r["hard_failure"])
    passes = sum(1 for r in eval_results if r["overall_pass"])

    artifact = {
        "experiment_id": "NE-010",
        "title": "Operator Perception Fidelity",
        "profile": profile,
        "timestamp": datetime.now().isoformat(),
        "frozen_dependency": "NE-009.2",
        "policy": {
            "no_manual_model_answer_scoring": True,
            "ground_truth_source": "recorder+model events",
            "hard_fail_on_boundary_misprojection": True,
            "console_behavior_modified": False,
        },
        "project_path": project_path,
        "session_id": session_id,
        "log_file": str(recorder.log_file),
        "prompts": resolved_prompts,
        "flights": eval_results,
        "summary": {
            "flights_total": len(eval_results),
            "flights_passed": passes,
            "flights_failed": len(eval_results) - passes,
            "hard_failures": hard_failures,
            "overall_pass": hard_failures == 0 and passes == len(eval_results),
        },
        "operator_view": {
            "console_mode": "compact",
            "line_count": len(console.output_text().splitlines()),
            "console_output": console.output_text(),
        },
    }

    artifact_path = output_dir / f"ne_010_operator_perception_fidelity_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    with open(artifact_path, "w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2)

    return artifact_path


def print_summary(artifact_path: Path) -> None:
    with open(artifact_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    print("NE-010 operator perception fidelity complete.")
    print(f"Artifact: {artifact_path}")
    print(f"JSONL log: {data['log_file']}")
    print(f"Summary: {data['summary']}")
    for flight in data["flights"]:
        truth = flight["truth"]["terminal_state"]
        projection = flight["projection"]["terminal_state"]
        print(
            f"{flight['flight_id']}: pass={flight['overall_pass']} hard_fail={flight['hard_failure']} "
            f"truth={truth} projection={projection}"
        )


def build_blind_review_packet(artifact: Dict[str, Any]) -> str:
    lines = [
        "# NE-010.2 Blind Operator Reconstruction Packet",
        "",
        "Instructions:",
        "- Use only the console transcript below.",
        "- Do not infer from missing hidden data such as model payloads, recorder traces, or evaluator results.",
        "- Answer the five review questions for each case.",
        "",
    ]

    for idx, flight in enumerate(artifact.get("flights", []), start=1):
        case_label = chr(ord("A") + idx - 1)
        lines.append(f"## Case {case_label}")
        lines.append("")
        lines.append("Console Transcript:")
        lines.append("")
        for row in flight.get("timeline", []):
            if not row.get("expected_visible"):
                continue
            messages = row.get("messages") or []
            if not messages:
                continue
            t_plus_ms = row.get("t_plus_ms")
            seconds = 0.0 if t_plus_ms is None else float(t_plus_ms) / 1000.0
            lines.append(f"T+{seconds:.2f}s")
            for message in messages:
                lines.append(message)
            lines.append("")

        lines.append("Review Questions:")
        for question_idx, question in enumerate(REVIEW_QUESTIONS, start=1):
            lines.append(f"{question_idx}. {question}")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_truth_key(artifact: Dict[str, Any], all_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    truth_flights: List[Dict[str, Any]] = []
    for idx, flight in enumerate(artifact.get("flights", []), start=1):
        case_label = chr(ord("A") + idx - 1)
        e0, e1 = flight.get("event_span", [0, 0])
        flight_events = all_events[e0:e1]
        truth = summarize_truth_from_events(flight_events)
        truth_flights.append({
            "case": case_label,
            "flight_id": flight.get("flight_id"),
            "prompt": flight.get("prompt"),
            "truth": truth,
        })

    return {
        "experiment_id": artifact.get("experiment_id"),
        "profile": artifact.get("profile"),
        "source_artifact": artifact.get("timestamp"),
        "flights": truth_flights,
    }


def export_review_packets(artifact_path: Path) -> Dict[str, str]:
    with open(artifact_path, "r", encoding="utf-8") as handle:
        artifact = json.load(handle)

    log_file = Path(artifact["log_file"])
    all_events = load_jsonl_events(log_file)
    output_dir = artifact_path.parent
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    packet_text = build_blind_review_packet(artifact)
    truth_key = build_truth_key(artifact, all_events)

    reviewer_a = output_dir / f"ne_010_2_reviewer_a_packet_{timestamp}.md"
    reviewer_b = output_dir / f"ne_010_2_reviewer_b_packet_{timestamp}.md"
    truth_key_path = output_dir / f"ne_010_2_truth_key_{timestamp}.json"

    reviewer_a.write_text(packet_text, encoding="utf-8")
    reviewer_b.write_text(packet_text, encoding="utf-8")
    truth_key_path.write_text(json.dumps(truth_key, indent=2), encoding="utf-8")

    return {
        "reviewer_a": str(reviewer_a),
        "reviewer_b": str(reviewer_b),
        "truth_key": str(truth_key_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run NE-010 operator perception fidelity benchmark")
    parser.add_argument("project_path", nargs="?", default="/home/user/Projects/lisa")
    parser.add_argument("--profile", choices=["baseline", "harder"], default="baseline")
    parser.add_argument("--export-review-packets", dest="export_review_packets", default=None)
    args = parser.parse_args()

    if args.export_review_packets:
        exported = export_review_packets(Path(args.export_review_packets))
        print("NE-010.2 blind review packets exported.")
        print(f"Reviewer A Packet: {exported['reviewer_a']}")
        print(f"Reviewer B Packet: {exported['reviewer_b']}")
        print(f"Truth Key: {exported['truth_key']}")
    else:
        artifact_file = asyncio.run(run_ne_010(project_path=args.project_path, profile=args.profile))
        print_summary(artifact_file)
