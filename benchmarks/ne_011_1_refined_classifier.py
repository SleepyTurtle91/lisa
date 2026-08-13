"""
NE-011.1: Refined Classification Replay

Replays the NE-011 artifact through a finer classification scheme without
making any new live model calls.  Follows the same replay-over-dataset
pattern as NE-009.1.

Original NE-011 used a single DIRECT_PATH bucket that masked two materially
different sub-failures.  This replay splits the outcome space into:

  DIRECT_PATH        — tool invoked, path resolved, tool call succeeded
  HALLUCINATED_PATH  — tool invoked, path has no grounding in project structure
                       or the prompt-supplied target, and fails resolution
  WRONG_TOOL_TYPE    — a project-relative equivalent of the path exists but the
                       wrong tool was selected (e.g. read_file on a directory)
  COMPOUND_LITERAL   — path arg contains compound prose rather than a path
  NO_TOOL_CALL       — no tool was invoked; model answered in prose
  CLARIFICATION      — model requested clarification without invoking a tool
  ERROR              — runtime or harness failure during the original run

Classification contract:
  1. tool_calls_made == 0              → NO_TOOL_CALL | CLARIFICATION
  2. path_arg contains prose markers   → COMPOUND_LITERAL
  3. tool_success == True              → DIRECT_PATH  (positive ground truth)
  4. project-relative equivalent exists + wrong tool → WRONG_TOOL_TYPE
  5. no project-relative equivalent exists           → HALLUCINATED_PATH
  6. failure for another reason                      → DIRECT_PATH (failed)
     (preserves the label while adding a failed_resolution flag)
"""

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


# ── Prose-marker detection (unchanged from NE-011) ───────────────────────────

_PROSE_MARKERS = [
    " inside ", " and ", " before ", " then ", " after ",
    "files inside", "suggest", "anything", "doing",
]


def _is_compound_literal(path_arg: str) -> bool:
    low = path_arg.lower()
    return any(m in low for m in _PROSE_MARKERS)


# ── Project-relative resolution ───────────────────────────────────────────────

def _project_relative_candidate(path_arg: str, project_path: str) -> Optional[Path]:
    """
    Return the first Path under project_path that plausibly corresponds to
    path_arg, or None if no such path exists.

    Strategy (in order):
      1. Resolve the raw arg relative to project_path.
      2. If the arg is absolute or starts with ~/, strip the leading component
         and try the remainder relative to project_path.
    """
    project = Path(project_path)

    # Direct resolve
    candidate = project / path_arg
    if candidate.exists():
        return candidate

    # Normalise home-dir prefix then try again
    expanded = str(Path(path_arg).expanduser())
    candidate2 = project / Path(expanded).name
    if candidate2.exists():
        return candidate2

    # Strip leading separator from absolute paths and try each suffix
    parts = Path(expanded).parts
    for start in range(len(parts)):
        suffix = Path(*parts[start:]) if parts[start:] else Path()
        candidate3 = project / suffix
        if candidate3.exists():
            return candidate3

    return None


# ── Refined classifier ────────────────────────────────────────────────────────

def refined_classify(
    tool_calls_made: int,
    first_tool_name: Optional[str],
    first_tool_path_arg: Optional[str],
    tool_success: Optional[bool],
    response_text: str,
    project_path: str,
) -> Tuple[str, str, bool]:
    """
    Returns (classification, reason, failed_resolution).

    failed_resolution is True when the tool was invoked but the path did not
    resolve successfully — useful for DIRECT_PATH cases that still failed.
    """
    if tool_calls_made == 0 or first_tool_path_arg is None:
        text = (response_text or "").lower()
        clarify_tokens = [
            "could you clarify", "can you clarify", "which file", "which directory",
            "what do you mean", "please specify", "what exactly", "what should",
            "would you like", "need more information",
        ]
        if any(t in text for t in clarify_tokens) or (
            "?" in text and len(text) < 300
        ):
            return "CLARIFICATION", "model requested clarification without tool use", False
        return "NO_TOOL_CALL", "model answered without invoking any tool", False

    if _is_compound_literal(first_tool_path_arg):
        return "COMPOUND_LITERAL", (
            f"path arg '{first_tool_path_arg}' contains prose rather than a real path"
        ), True

    if tool_success:
        return "DIRECT_PATH", (
            f"tool '{first_tool_name}' invoked with '{first_tool_path_arg}' and succeeded"
        ), False

    # Tool was called and failed — determine why
    project_equiv = _project_relative_candidate(first_tool_path_arg, project_path)

    if project_equiv is not None:
        # A project-relative equivalent exists; check tool-type mismatch
        if project_equiv.is_dir() and first_tool_name == "read_file":
            return "WRONG_TOOL_TYPE", (
                f"read_file invoked on directory '{first_tool_path_arg}'; "
                f"project-relative equivalent '{project_equiv}' is a directory"
            ), True
        if project_equiv.is_file() and first_tool_name == "list_directory":
            return "WRONG_TOOL_TYPE", (
                f"list_directory invoked on file '{first_tool_path_arg}'; "
                f"project-relative equivalent '{project_equiv}' is a file"
            ), True
        # Equivalent exists but failure for another reason
        return "DIRECT_PATH", (
            f"tool '{first_tool_name}' invoked with '{first_tool_path_arg}' but failed; "
            f"project-relative equivalent exists at '{project_equiv}'"
        ), True

    # No project-relative equivalent — classify as hallucinated
    return "HALLUCINATED_PATH", (
        f"path '{first_tool_path_arg}' has no project-relative equivalent under '{project_path}'"
    ), True


# ── Replay ────────────────────────────────────────────────────────────────────

@dataclass
class RefinedObservation:
    case_id: str
    group: str
    prompt: str
    # raw evidence (preserved from NE-011)
    tool_calls_made: int
    first_tool_name: Optional[str]
    first_tool_path_arg: Optional[str]
    tool_success: Optional[bool]
    # NE-011 label
    ne011_classification: str
    # NE-011.1 refined label
    classification: str
    classification_reason: str
    failed_resolution: bool


def replay_artifact(artifact_path: Path, project_path: str) -> Dict[str, Any]:
    with open(artifact_path, "r", encoding="utf-8") as fh:
        artifact = json.load(fh)

    observations: List[RefinedObservation] = []
    for obs in artifact["observations"]:
        label, reason, failed = refined_classify(
            tool_calls_made=obs["tool_calls_made"],
            first_tool_name=obs["first_tool_name"],
            first_tool_path_arg=obs["first_tool_path_arg"],
            tool_success=obs["tool_success"],
            response_text=obs["response_text"],
            project_path=project_path,
        )
        observations.append(RefinedObservation(
            case_id=obs["case_id"],
            group=obs["group"],
            prompt=obs["prompt"],
            tool_calls_made=obs["tool_calls_made"],
            first_tool_name=obs["first_tool_name"],
            first_tool_path_arg=obs["first_tool_path_arg"],
            tool_success=obs["tool_success"],
            ne011_classification=obs["classification"],
            classification=label,
            classification_reason=reason,
            failed_resolution=failed,
        ))

    def _count(obs_list: List[RefinedObservation]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for o in obs_list:
            counts[o.classification] = counts.get(o.classification, 0) + 1
        return counts

    control_obs = [o for o in observations if o.group == "CONTROL"]
    compound_obs = [o for o in observations if o.group == "COMPOUND"]

    result = {
        "experiment": "NE-011.1",
        "question": (
            "When L.I.S.A. successfully extracts an intent, did it ground the target "
            "in actual repository evidence and select an operation appropriate to the target type?"
        ),
        "timestamp": datetime.now(datetime.now().astimezone().tzinfo).isoformat(),
        "source_artifact": str(artifact_path),
        "project_path": project_path,
        "model": artifact.get("model"),
        "provider": artifact.get("provider"),
        "total_cases": len(observations),
        "control_summary": _count(control_obs),
        "compound_summary": _count(compound_obs),
        "observations": [asdict(o) for o in observations],
    }
    return result


def print_report(result: Dict[str, Any]) -> None:
    print(f"\nNE-011.1 — Refined Classification Replay")
    print(f"Source : {result['source_artifact']}")
    print(f"Project: {result['project_path']}")
    print()

    header = f"{'ID':<4} {'Group':<10} {'NE-011':<20} {'NE-011.1':<22} {'path_arg'}"
    print(header)
    print("-" * len(header))
    for o in result["observations"]:
        changed = " ←" if o["ne011_classification"] != o["classification"] else "  "
        print(
            f"{o['case_id']:<4} {o['group']:<10} "
            f"{o['ne011_classification']:<20} {o['classification']:<22}{changed} "
            f"{o['first_tool_path_arg']!r}"
        )

    print()
    print(f"Control  distribution: {result['control_summary']}")
    print(f"Compound distribution: {result['compound_summary']}")


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-011.1 Refined Classification Replay")
    parser.add_argument(
        "artifact",
        nargs="?",
        help="Path to a ne_011_*.json artifact (defaults to most recent in benchmarks/)",
    )
    parser.add_argument(
        "project_path",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent),
        help="Project root used for project-relative resolution (default: lisa repo root)",
    )
    args = parser.parse_args()

    benchmarks_dir = Path(__file__).resolve().parent
    if args.artifact:
        artifact_path = Path(args.artifact)
    else:
        candidates = sorted(benchmarks_dir.glob("ne_011_compound_intent_*.json"))
        if not candidates:
            print("No NE-011 artifact found.  Run ne_011_compound_intent.py first.")
            sys.exit(1)
        artifact_path = candidates[-1]

    result = replay_artifact(artifact_path=artifact_path, project_path=args.project_path)

    output_path = benchmarks_dir / f"ne_011_1_refined_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    print_report(result)
    print(f"\nArtifact: {output_path}")
