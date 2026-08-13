"""
NE-011.2: Controlled A/B Environmental-Evidence Experiment

Tests the HALLUCINATED_PATH hypothesis from NE-011.1:

  "When L.I.S.A. has no environmental context it invents a plausible-sounding
  path.  Supplying the repository structure upfront suppresses hallucination
  and produces a grounded target."

Two conditions, one probe prompt (X3 from NE-011):

  Condition A — No context
      Prompt: "inspect documentation before doing anything"
      Represents the NE-011 X3 baseline.

  Condition B — Repository structure exposed
      Prompt: <project tree injected as first user message> +
              "inspect documentation before doing anything"
      The project tree is generated at runtime from the actual project path, so
      the harness stays grounded and does not fabricate structure.

Classification uses the refined NE-011.1 contract:
  DIRECT_PATH / HALLUCINATED_PATH / WRONG_TOOL_TYPE / NO_TOOL_CALL / CLARIFICATION

The hypothesis is falsified if Condition A → DIRECT_PATH.
The hypothesis is supported if A → HALLUCINATED_PATH and B → DIRECT_PATH.
"""

import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.core.context import Capability, SessionContext
from lisa.core.kernel import LisaRuntime
from lisa.providers.ollama.provider import OllamaProvider
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import ListDirectoryTool


# ── Shared probe prompt ───────────────────────────────────────────────────────

PROBE_PROMPT = "inspect documentation before doing anything"


# ── Project tree builder ──────────────────────────────────────────────────────

def build_project_tree(project_path: str, max_depth: int = 2) -> str:
    """
    Build a compact directory tree for the project root.
    Only directories and top-level files are included; benchmark artifacts
    and __pycache__ are excluded to keep the context concise.
    """
    root = Path(project_path)
    lines: List[str] = [f"{root.name}/"]

    _SKIP = {"__pycache__", ".git", ".venv", "node_modules"}

    def _walk(path: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return

        dirs = [e for e in entries if e.is_dir() and e.name not in _SKIP]
        files = [
            e for e in entries
            if e.is_file()
            and not e.name.endswith((".json", ".jsonl", ".pyc"))
            and e.name not in _SKIP
        ]

        # Limit file count per directory to keep context compact
        shown_files = files[:8]
        all_items = dirs + shown_files
        for i, entry in enumerate(all_items):
            connector = "└── " if i == len(all_items) - 1 else "├── "
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                extension = "    " if i == len(all_items) - 1 else "│   "
                _walk(entry, prefix + extension, depth + 1)
            else:
                lines.append(f"{prefix}{connector}{entry.name}")

    _walk(root, "", 1)
    return "\n".join(lines)


def condition_b_prompt(project_path: str) -> str:
    tree = build_project_tree(project_path)
    return (
        f"Repository structure:\n```\n{tree}\n```\n\n"
        f"{PROBE_PROMPT}"
    )


# ── Refined classification (NE-011.1 contract) ────────────────────────────────

_PROSE_MARKERS = [
    " inside ", " and ", " before ", " then ", " after ",
    "files inside", "suggest", "anything", "doing",
]


def _is_compound_literal(path_arg: str) -> bool:
    return any(m in path_arg.lower() for m in _PROSE_MARKERS)


def _project_relative_candidate(path_arg: str, project_path: str) -> Optional[Path]:
    project = Path(project_path)

    candidate = project / path_arg
    if candidate.exists():
        return candidate

    expanded = str(Path(path_arg).expanduser())
    parts = Path(expanded).parts
    for start in range(len(parts)):
        suffix = Path(*parts[start:]) if parts[start:] else Path()
        c = project / suffix
        if c.exists():
            return c

    return None


def refined_classify(
    tool_calls_made: int,
    first_tool_name: Optional[str],
    first_tool_path_arg: Optional[str],
    tool_success: Optional[bool],
    response_text: str,
    project_path: str,
) -> Tuple[str, str]:
    if tool_calls_made == 0 or first_tool_path_arg is None:
        text = (response_text or "").lower()
        clarify_tokens = [
            "could you clarify", "can you clarify", "which file",
            "what do you mean", "please specify", "what exactly",
            "would you like", "need more information",
        ]
        if any(t in text for t in clarify_tokens) or (
            "?" in text and len(text) < 300
        ):
            return "CLARIFICATION", "model requested clarification without tool use"
        return "NO_TOOL_CALL", "model answered without invoking any tool"

    if _is_compound_literal(first_tool_path_arg):
        return "COMPOUND_LITERAL", (
            f"path arg '{first_tool_path_arg}' contains prose"
        )

    if tool_success:
        return "DIRECT_PATH", (
            f"tool '{first_tool_name}' succeeded with path '{first_tool_path_arg}'"
        )

    equiv = _project_relative_candidate(first_tool_path_arg, project_path)
    if equiv is not None:
        if equiv.is_dir() and first_tool_name == "read_file":
            return "WRONG_TOOL_TYPE", (
                f"read_file on directory '{first_tool_path_arg}'"
            )
        if equiv.is_file() and first_tool_name == "list_directory":
            return "WRONG_TOOL_TYPE", (
                f"list_directory on file '{first_tool_path_arg}'"
            )
        return "DIRECT_PATH", (
            f"tool failed but project-relative equivalent exists at '{equiv}'"
        )

    return "HALLUCINATED_PATH", (
        f"'{first_tool_path_arg}' has no project-relative equivalent"
    )


# ── Per-condition runner ──────────────────────────────────────────────────────

@dataclass
class ConditionObservation:
    condition: str           # "A" | "B"
    condition_label: str     # human-readable
    prompt_sent: str         # actual prompt passed to the session
    tool_calls_made: int
    first_tool_name: Optional[str]
    first_tool_path_arg: Optional[str]
    tool_success: Optional[bool]
    tool_error: Optional[str]
    response_text: str
    recorder_file: str
    classification: str
    classification_reason: str
    error: Optional[str] = None


async def run_condition(
    condition: str,
    prompt: str,
    project_path: str,
    output_dir: Path,
) -> ConditionObservation:
    label = "No environmental context" if condition == "A" else "Repository structure exposed"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne011_2_{condition}_{timestamp}"
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
            workspace_name="ne_011_2_env_evidence",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )
        session = runtime.create_session(ctx)
        response_text = await session.send_message(prompt)

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

        cls, reason = refined_classify(
            tool_calls_made=tool_calls_made,
            first_tool_name=first_tool_name,
            first_tool_path_arg=first_tool_path_arg,
            tool_success=tool_success,
            response_text=response_text,
            project_path=project_path,
        )

        return ConditionObservation(
            condition=condition,
            condition_label=label,
            prompt_sent=prompt,
            tool_calls_made=tool_calls_made,
            first_tool_name=first_tool_name,
            first_tool_path_arg=first_tool_path_arg,
            tool_success=tool_success,
            tool_error=tool_error,
            response_text=response_text,
            recorder_file=str(recorder.log_file),
            classification=cls,
            classification_reason=reason,
        )

    except Exception as exc:
        return ConditionObservation(
            condition=condition,
            condition_label=label,
            prompt_sent=prompt,
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

    prompt_a = PROBE_PROMPT
    prompt_b = condition_b_prompt(project_path)

    print(f"  [A] No context        : {PROBE_PROMPT!r}")
    obs_a = await run_condition("A", prompt_a, project_path, resolved_dir)
    print(f"       → {obs_a.classification}  (path_arg={obs_a.first_tool_path_arg!r})")

    print(f"  [B] Structure exposed : {PROBE_PROMPT!r} (with project tree prepended)")
    obs_b = await run_condition("B", prompt_b, project_path, resolved_dir)
    print(f"       → {obs_b.classification}  (path_arg={obs_b.first_tool_path_arg!r})")

    # Hypothesis evaluation
    hypothesis_supported = (
        obs_a.classification == "HALLUCINATED_PATH"
        and obs_b.classification == "DIRECT_PATH"
    )
    hypothesis_falsified = obs_a.classification == "DIRECT_PATH"
    hypothesis_partial = (
        not hypothesis_supported
        and not hypothesis_falsified
        and obs_b.classification != obs_a.classification
    )

    if hypothesis_supported:
        verdict = "SUPPORTED"
        verdict_note = (
            "A hallucinated, B grounded: environmental perception suppressed hallucination."
        )
    elif hypothesis_falsified:
        verdict = "FALSIFIED"
        verdict_note = (
            "Condition A succeeded without environmental context; "
            "hallucination was not the baseline state."
        )
    elif hypothesis_partial:
        verdict = "PARTIAL"
        verdict_note = (
            f"A={obs_a.classification}, B={obs_b.classification}: "
            "conditions differ but the clean A→HALLUCINATED / B→DIRECT pattern was not observed."
        )
    else:
        verdict = "INCONCLUSIVE"
        verdict_note = (
            f"A={obs_a.classification}, B={obs_b.classification}: "
            "conditions produced the same result; "
            "environmental context did not change the outcome."
        )

    artifact = {
        "experiment": "NE-011.2",
        "question": (
            "Does supplying repository structure upfront suppress grounding hallucination "
            "and produce a correctly-grounded target selection?"
        ),
        "hypothesis": (
            "Condition A (no context) → HALLUCINATED_PATH; "
            "Condition B (structure exposed) → DIRECT_PATH"
        ),
        "probe_prompt": PROBE_PROMPT,
        "timestamp": datetime.now().astimezone().isoformat(),
        "project_path": project_path,
        "model": "qwen3:1.7b",
        "provider": "ollama",
        "verdict": verdict,
        "verdict_note": verdict_note,
        "condition_a": asdict(obs_a),
        "condition_b": asdict(obs_b),
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    artifact_path = resolved_dir / f"ne_011_2_env_evidence_{ts}.json"
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    print(f"\nVerdict : {verdict}")
    print(f"Note    : {verdict_note}")
    print(f"Artifact: {artifact_path}")

    return artifact


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-011.2 Environmental Evidence A/B Experiment")
    parser.add_argument(
        "project_path",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent),
        help="Project root (default: lisa repo root)",
    )
    args = parser.parse_args()

    print(f"NE-011.2 — Environmental Evidence A/B")
    print(f"Probe  : {PROBE_PROMPT!r}")
    print(f"Project: {args.project_path}")
    print()

    asyncio.run(run_experiment(project_path=args.project_path))
