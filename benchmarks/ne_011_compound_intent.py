"""
NE-011: Compound Intent / Target Extraction Diagnostic

Classifies how L.I.S.A. handles prompts where the human's target is embedded
inside natural-language phrasing rather than given as a bare path.

No parser or runtime changes are made here.  This is a pure observation harness.

Case groups:
  CONTROL  — unambiguous single-target prompts (expected to succeed cleanly)
  COMPOUND — target embedded in natural-language phrasing (observed failure pattern)

Per-case classification is derived from the tool call record only:
  DIRECT_PATH        — tool invoked with a clean file/directory path
  DIRECTORY_AS_FILE  — read_file invoked on a directory path (wrong tool for target)
  COMPOUND_LITERAL   — tool path arg contains compound prose rather than a real path
  NO_TOOL_CALL       — model answered without invoking any tool
  CLARIFICATION      — model requested clarification or more information
  ERROR              — runtime or harness failure
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
class IntentCase:
    case_id: str
    group: str        # CONTROL | COMPOUND
    prompt: str
    note: str         # human-readable description of what we expect to observe


CASES: List[IntentCase] = [
    # Controls — bare, unambiguous targets
    IntentCase("C1", "CONTROL", "read README.md",
               "Unambiguous file path; should call read_file(path='README.md')"),
    IntentCase("C2", "CONTROL", "list docs",
               "Unambiguous directory; should call list_directory(path='docs')"),
    IntentCase("C3", "CONTROL", "read docs/ARCHITECTURE_SCORE.md",
               "Explicit relative path; should call read_file with that path"),

    # Compound cases — target embedded in natural-language phrasing
    IntentCase("X1", "COMPOUND", "read files inside docs",
               "Target is 'docs'; observe whether path arg is 'docs' or the literal phrase"),
    IntentCase("X2", "COMPOUND", "read docs and suggest a plan",
               "Target is 'docs'; trailing instruction should not pollute the path arg"),
    IntentCase("X3", "COMPOUND", "inspect documentation before doing anything",
               "Highly implicit; observe whether model calls a tool or explains without one"),
    IntentCase("X4", "COMPOUND", "read /docs before we do anything",
               "Replicates the observed session failure; absolute /docs with trailing clause"),
]


# ── Observation record ────────────────────────────────────────────────────────

@dataclass
class IntentObservation:
    case_id: str
    group: str
    prompt: str
    note: str
    # raw evidence
    tool_calls_made: int
    first_tool_name: Optional[str]
    first_tool_path_arg: Optional[str]
    tool_success: Optional[bool]
    tool_error: Optional[str]
    response_text: str
    recorder_file: str
    # derived classification (no runtime changes)
    classification: str
    classification_reason: str
    error: Optional[str] = None


# ── Classification (derived from recorder only) ───────────────────────────────

def _is_compound_literal(path_arg: str) -> bool:
    """True when the path argument contains prose words that are not valid path components."""
    prose_markers = [
        " inside ", " and ", " before ", " then ", " after ",
        "files inside", "suggest", "anything", "doing",
    ]
    low = path_arg.lower()
    return any(m in low for m in prose_markers)


def classify_observation(
    tool_calls_made: int,
    first_tool_name: Optional[str],
    first_tool_path_arg: Optional[str],
    response_text: str,
) -> tuple[str, str]:
    if tool_calls_made == 0:
        text = (response_text or "").lower()
        clarify_tokens = [
            "could you clarify", "can you clarify", "which file", "which directory",
            "what do you mean", "please specify", "what exactly", "what should",
            "would you like", "need more information",
        ]
        if any(t in text for t in clarify_tokens) or (text.endswith("?") and len(text) < 300):
            return "CLARIFICATION", "model requested clarification without tool use"
        return "NO_TOOL_CALL", "model answered without invoking any tool"

    if first_tool_path_arg is None:
        return "NO_TOOL_CALL", "tool invoked but path argument was absent"

    if _is_compound_literal(first_tool_path_arg):
        return "COMPOUND_LITERAL", (
            f"path arg '{first_tool_path_arg}' contains prose rather than a real path"
        )

    # Path looks structurally valid — check if it is a directory used with read_file
    resolved = Path(first_tool_path_arg)
    if first_tool_name == "read_file" and (
        first_tool_path_arg.endswith("/")
        or (resolved.exists() and resolved.is_dir())
    ):
        return "DIRECTORY_AS_FILE", (
            f"read_file invoked on directory path '{first_tool_path_arg}'"
        )

    return "DIRECT_PATH", f"tool '{first_tool_name}' invoked with clean path '{first_tool_path_arg}'"


# ── Per-case runner ───────────────────────────────────────────────────────────

async def run_case(
    case: IntentCase,
    project_path: str,
    output_dir: Path,
) -> IntentObservation:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne011_{case.case_id}_{timestamp}"
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
            workspace_name="ne_011_compound_intent",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )
        session = runtime.create_session(ctx)
        response_text = await session.send_message(case.prompt)

        # Extract tool evidence from recorder
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

        label, reason = classify_observation(
            tool_calls_made=tool_calls_made,
            first_tool_name=first_tool_name,
            first_tool_path_arg=first_tool_path_arg,
            response_text=response_text,
        )

        return IntentObservation(
            case_id=case.case_id,
            group=case.group,
            prompt=case.prompt,
            note=case.note,
            tool_calls_made=tool_calls_made,
            first_tool_name=first_tool_name,
            first_tool_path_arg=first_tool_path_arg,
            tool_success=tool_success,
            tool_error=tool_error,
            response_text=response_text,
            recorder_file=str(recorder.log_file),
            classification=label,
            classification_reason=reason,
        )

    except Exception as exc:
        return IntentObservation(
            case_id=case.case_id,
            group=case.group,
            prompt=case.prompt,
            note=case.note,
            tool_calls_made=tool_calls_made,
            first_tool_name=first_tool_name,
            first_tool_path_arg=first_tool_path_arg,
            tool_success=tool_success,
            tool_error=tool_error,
            response_text=response_text,
            recorder_file=str(recorder.log_file),
            classification="ERROR",
            classification_reason="case execution raised an exception",
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

    observations: List[IntentObservation] = []
    for case in CASES:
        print(f"  [{case.group}] {case.case_id}: {case.prompt}")
        obs = await run_case(case=case, project_path=project_path, output_dir=resolved_dir)
        observations.append(obs)
        print(f"         → {obs.classification}  (path_arg={obs.first_tool_path_arg!r})")

    # Summary by group
    control_obs = [o for o in observations if o.group == "CONTROL"]
    compound_obs = [o for o in observations if o.group == "COMPOUND"]

    def _count(obs_list: List[IntentObservation]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for o in obs_list:
            counts[o.classification] = counts.get(o.classification, 0) + 1
        return counts

    artifact = {
        "experiment": "NE-011",
        "question": "When the human gives L.I.S.A. a target indirectly, does it correctly extract what the human meant?",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "project_path": project_path,
        "model": "qwen3:1.7b",
        "provider": "ollama",
        "total_cases": len(observations),
        "control_summary": _count(control_obs),
        "compound_summary": _count(compound_obs),
        "observations": [asdict(o) for o in observations],
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    artifact_path = resolved_dir / f"ne_011_compound_intent_{ts}.json"
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    print(f"\nArtifact: {artifact_path}")
    print(f"Control  distribution: {artifact['control_summary']}")
    print(f"Compound distribution: {artifact['compound_summary']}")

    return artifact


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-011 Compound Intent Diagnostic")
    parser.add_argument(
        "project_path",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent),
        help="Project root to run flights against (default: lisa repo root)",
    )
    args = parser.parse_args()

    print(f"NE-011 — Compound Intent / Target Extraction")
    print(f"Project: {args.project_path}")
    print(f"Cases  : {len(CASES)} ({sum(1 for c in CASES if c.group == 'CONTROL')} controls, "
          f"{sum(1 for c in CASES if c.group == 'COMPOUND')} compound)")
    print()

    asyncio.run(run_experiment(project_path=args.project_path))
