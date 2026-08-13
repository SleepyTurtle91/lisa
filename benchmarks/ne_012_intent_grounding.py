"""
NE-012: Intent & Context Grounding Diagnostic Harness

Evaluates three explicit intent & context grounding frontiers:
  - Test A: Filesystem Intent Extraction (e.g. "read files inside /docs" -> LIST_DIRECTORY vs READ_FILE)
  - Test B: File vs Directory Type Grounding (e.g. "list BOOT.md" -> target type inspection / guard)
  - Test C: Evidence Provenance Classification (OBSERVED vs DOCUMENTED vs INFERRED vs UNVERIFIED)

This benchmark runs without modifying runtime logic to establish an empirical baseline
and test classifier boundaries against actual model behavior and trace evidence.
"""

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
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
from lisa.tools.filesystem.standard import ListDirectoryTool, WriteFileTool


# ── Case definitions ──────────────────────────────────────────────────────────

@dataclass
class GroundingCase:
    case_id: str
    category: str      # TEST_A_INTENT | TEST_B_TYPE | TEST_C_PROVENANCE
    prompt: str
    expected_intent: str
    note: str


CASES: List[GroundingCase] = [
    # Test A — Intent Boundaries
    GroundingCase("A1", "TEST_A_INTENT", "read README.md", "READ_FILE",
                  "Direct file read request; target is README.md"),
    GroundingCase("A2", "TEST_A_INTENT", "read files inside docs", "LIST_DIRECTORY",
                  "Natural phrasing requesting directory contents; intent is LIST_DIRECTORY"),
    GroundingCase("A3", "TEST_A_INTENT", "show me what's inside docs", "LIST_DIRECTORY",
                  "Colloquial directory contents request; intent is LIST_DIRECTORY"),

    # Test B — Target Type Grounding
    GroundingCase("B1", "TEST_B_TYPE", "list README.md", "TYPE_MISMATCH_GUARD",
                  "Invoking directory listing on a file target; should inspect type and reject/switch tool"),
    GroundingCase("B2", "TEST_B_TYPE", "read docs", "TYPE_MISMATCH_GUARD",
                  "Invoking read_file on a directory target; should inspect type and switch to list_directory"),

    # Test C — Provenance Classification
    GroundingCase("C1", "TEST_C_PROVENANCE", "What has actually been verified in this project session?", "PROVENANCE_SEPARATION",
                  "Requires separating OBSERVED execution vs DOCUMENTED text vs INFERRED claims"),
]


# ── Observation record ────────────────────────────────────────────────────────

@dataclass
class GroundingObservation:
    case_id: str
    category: str
    prompt: str
    expected_intent: str
    note: str
    # Raw evidence
    tool_calls_made: int
    first_tool_name: Optional[str]
    first_tool_path_arg: Optional[str]
    tool_success: Optional[bool]
    tool_error: Optional[str]
    response_text: str
    recorder_file: str
    # Evaluation metrics
    actual_intent: str
    intent_match: bool
    type_grounded: bool
    provenance_buckets_found: List[str]
    notes: str
    error: Optional[str] = None


# ── Evaluators ────────────────────────────────────────────────────────────────

def evaluate_intent(first_tool_name: Optional[str], first_tool_path_arg: Optional[str], response_text: str) -> str:
    if first_tool_name == "read_file":
        return "READ_FILE"
    elif first_tool_name == "list_directory":
        return "LIST_DIRECTORY"
    elif tool_calls_made_from_text(response_text) > 0:
        return "OTHER_TOOL"
    else:
        return "NO_TOOL_CALL"


def tool_calls_made_from_text(text: str) -> int:
    return 0


def evaluate_provenance(response_text: str) -> List[str]:
    buckets = []
    text_lower = response_text.lower()
    if any(k in text_lower for k in ["observed", "executed", "verified in this session", "tool ran"]):
        buckets.append("OBSERVED")
    if any(k in text_lower for k in ["documented", "boot.md", "specified in", "reads", "states"]):
        buckets.append("DOCUMENTED")
    if any(k in text_lower for k in ["inferred", "deduced", "suggests", "likely"]):
        buckets.append("INFERRED")
    if any(k in text_lower for k in ["unverified", "not executed", "not run", "untested"]):
        buckets.append("UNVERIFIED")
    return buckets


# ── Per-case runner ───────────────────────────────────────────────────────────

async def run_case(
    case: GroundingCase,
    project_path: str,
    output_dir: Path,
) -> GroundingObservation:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne012_{case.case_id}_{timestamp}"
    recorder = FlightRecorder(session_id=session_id, log_dir=output_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    first_tool_name: Optional[str] = None
    first_tool_path_arg: Optional[str] = None
    tool_success: Optional[bool] = None
    tool_error: Optional[str] = None
    tool_calls_made: int = 0
    response_text: str = ""

    try:
        await runtime.initialize()
        await runtime.register_provider(OllamaProvider())
        runtime.tool_registry.register(ReadFileTool())
        runtime.tool_registry.register(ListDirectoryTool())

        ctx = SessionContext(
            project_path=project_path,
            workspace_name="ne_012_intent_grounding",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )
        session = runtime.create_session(ctx)
        response_text = await session.send_message(case.prompt)

        for event in recorder.get_events():
            etype = event.get("event_type", "")
            payload = event.get("payload") or {}

            if etype == "flight_stage" and payload.get("stage") == "tool_request":
                tool_calls_made += 1
                if first_tool_name is None:
                    first_tool_name = payload.get("tool_name")
                    args = payload.get("arguments") or {}
                    first_tool_path_arg = args.get("path")

            if etype == "flight_stage" and payload.get("stage") == "tool_result":
                if tool_success is None:
                    tool_success = bool(payload.get("success"))
                    if not tool_success:
                        tool_error = payload.get("error")

        actual_intent = evaluate_intent(first_tool_name, first_tool_path_arg, response_text)
        intent_match = (actual_intent == case.expected_intent)

        # Type grounding check
        type_grounded = True
        if case.category == "TEST_B_TYPE":
            if tool_error and ("Not a directory" in tool_error or "Is a directory" in tool_error):
                type_grounded = False  # Failed to inspect type before execution

        prov_buckets = []
        if case.category == "TEST_C_PROVENANCE":
            prov_buckets = evaluate_provenance(response_text)

        return GroundingObservation(
            case_id=case.case_id,
            category=case.category,
            prompt=case.prompt,
            expected_intent=case.expected_intent,
            note=case.note,
            tool_calls_made=tool_calls_made,
            first_tool_name=first_tool_name,
            first_tool_path_arg=first_tool_path_arg,
            tool_success=tool_success,
            tool_error=tool_error,
            response_text=response_text,
            recorder_file=str(recorder.log_file),
            actual_intent=actual_intent,
            intent_match=intent_match,
            type_grounded=type_grounded,
            provenance_buckets_found=prov_buckets,
            notes=f"Tool: {first_tool_name}, Path: {first_tool_path_arg}",
        )

    except Exception as exc:
        return GroundingObservation(
            case_id=case.case_id,
            category=case.category,
            prompt=case.prompt,
            expected_intent=case.expected_intent,
            note=case.note,
            tool_calls_made=tool_calls_made,
            first_tool_name=first_tool_name,
            first_tool_path_arg=first_tool_path_arg,
            tool_success=tool_success,
            tool_error=tool_error,
            response_text=response_text,
            recorder_file=str(recorder.log_file),
            actual_intent="ERROR",
            intent_match=False,
            type_grounded=False,
            provenance_buckets_found=[],
            notes="Execution exception",
            error=str(exc),
        )
    finally:
        try:
            await runtime.shutdown()
        except Exception:
            pass


# ── Experiment runner ─────────────────────────────────────────────────────────

async def run_experiment(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    observations: List[GroundingObservation] = []
    for case in CASES:
        print(f"  [{case.category}] {case.case_id}: {case.prompt}")
        obs = await run_case(case=case, project_path=project_path, output_dir=resolved_dir)
        observations.append(obs)
        print(f"         → actual_intent={obs.actual_intent} (expected={obs.expected_intent}, tool={obs.first_tool_name!r})")

    artifact = {
        "experiment": "NE-012",
        "question": "Does L.I.S.A. accurately resolve intent, inspect target types, and isolate evidence provenance?",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "project_path": project_path,
        "model": "qwen3:1.7b",
        "provider": "ollama",
        "total_cases": len(observations),
        "observations": [asdict(o) for o in observations],
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    artifact_path = resolved_dir / f"ne_012_intent_grounding_{ts}.json"
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    print(f"\nArtifact: {artifact_path}")
    return artifact


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-012 Intent & Grounding Diagnostic")
    parser.add_argument(
        "project_path",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent),
        help="Project root to run flights against",
    )
    args = parser.parse_args()

    print(f"NE-012 — Intent & Context Grounding Diagnostic")
    print(f"Project: {args.project_path}")
    print(f"Cases  : {len(CASES)}")
    print()

    asyncio.run(run_experiment(project_path=args.project_path))
