"""
NE-014: Intent / Input Command Boundary Diagnostic Harness

Diagnoses how user inputs are classified at the input boundary before LLM inference.

Input Classification Types:
  - DIRECT_REPL_COMMAND : 'help', 'doctor', 'activity', 'read BOOT.md', etc.
  - ABSOLUTE_PATH_INPUT : '/workspace/Projects/retails' or '/home/user/...'
  - COMPOUND_NATURAL    : 'read files inside /docs and suggest a plan'
  - AMBIGUOUS_PROSE     : 'how does this work?'

Evaluates whether inputs can be parsed deterministically prior to model routing.
"""

import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class InputBoundaryType(Enum):
    DIRECT_REPL_COMMAND = auto()
    ABSOLUTE_PATH_INPUT = auto()
    COMPOUND_NATURAL = auto()
    AMBIGUOUS_PROSE = auto()


@dataclass
class InputClassifierResult:
    input_text: str
    boundary_type: InputBoundaryType
    extracted_operation: Optional[str]
    extracted_target: Optional[str]
    extracted_followup: Optional[str]


class DeterministicInputClassifier:
    """Classifies user REPL inputs deterministically prior to LLM routing."""

    @staticmethod
    def classify(input_text: str, project_path: Optional[str] = None) -> InputClassifierResult:
        text = input_text.strip()
        text_lower = text.lower()

        # 1. Check for Absolute Path Input
        if (text.startswith("/") or text.startswith("~/")) and os.path.exists(os.path.expanduser(text)):
            return InputClassifierResult(
                input_text=text,
                boundary_type=InputBoundaryType.ABSOLUTE_PATH_INPUT,
                extracted_operation="INSPECT_PATH",
                extracted_target=text,
                extracted_followup=None,
            )

        # 2. Check for Direct REPL Commands
        if text_lower in ("help", "doctor", "compare", "switch", "exit", "quit", "list", "ls", "dir") or text_lower.startswith("read ") or text_lower.startswith("activity "):
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower()
            target = parts[1] if len(parts) > 1 else None
            return InputClassifierResult(
                input_text=text,
                boundary_type=InputBoundaryType.DIRECT_REPL_COMMAND,
                extracted_operation=cmd,
                extracted_target=target,
                extracted_followup=None,
            )

        # 3. Check for Compound Natural Language Input (e.g. "read files inside /docs and suggest a plan")
        compound_verbs = ["read files inside", "list files in", "inspect directory", "show contents of"]
        followup_conjunctions = [" and ", " then ", " before "]

        for verb in compound_verbs:
            if verb in text_lower:
                idx_verb = text_lower.find(verb)
                remainder = text[idx_verb + len(verb):].strip()
                
                target = remainder
                followup = None
                for conj in followup_conjunctions:
                    if conj in remainder.lower():
                        c_idx = remainder.lower().find(conj)
                        target = remainder[:c_idx].strip()
                        followup = remainder[c_idx + len(conj):].strip()
                        break

                return InputClassifierResult(
                    input_text=text,
                    boundary_type=InputBoundaryType.COMPOUND_NATURAL,
                    extracted_operation="INSPECT_DIRECTORY",
                    extracted_target=target,
                    extracted_followup=followup,
                )

        # 4. Fallback to Ambiguous Prose
        return InputClassifierResult(
            input_text=text,
            boundary_type=InputBoundaryType.AMBIGUOUS_PROSE,
            extracted_operation=None,
            extracted_target=None,
            extracted_followup=None,
        )


# ── Benchmark Harness ──────────────────────────────────────────────────────────

@dataclass
class NE014TestCase:
    case_id: str
    prompt: str
    expected_type: str
    expected_target: Optional[str]


CASES: List[NE014TestCase] = [
    NE014TestCase("X1", "read files inside /docs and suggest a plan", "COMPOUND_NATURAL", "/docs"),
    NE014TestCase("X2", "/workspace/Projects/retails", "ABSOLUTE_PATH_INPUT", "/workspace/Projects/retails"),
    NE014TestCase("C1", "read BOOT.md", "DIRECT_REPL_COMMAND", "BOOT.md"),
    NE014TestCase("C2", "how does the architecture work?", "AMBIGUOUS_PROSE", None),
]


async def run_experiment_ne014(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for case in CASES:
        print(f"  [{case.case_id}] Input: '{case.prompt}'")
        res = DeterministicInputClassifier.classify(case.prompt, project_path=project_path)
        pass_type = (res.boundary_type.name == case.expected_type)
        pass_target = (res.extracted_target == case.expected_target) if case.expected_target else True

        results.append({
            "case_id": case.case_id,
            "prompt": case.prompt,
            "expected_type": case.expected_type,
            "actual_type": res.boundary_type.name,
            "extracted_operation": res.extracted_operation,
            "extracted_target": res.extracted_target,
            "extracted_followup": res.extracted_followup,
            "type_match": pass_type,
            "target_match": pass_target,
        })
        print(f"         → type={res.boundary_type.name} (target={res.extracted_target!r}, followup={res.extracted_followup!r})")

    artifact = {
        "experiment": "NE-014",
        "title": "Intent / Input Command Boundary Diagnostic Baseline",
        "timestamp": datetime.now().isoformat() + "Z",
        "project_path": project_path,
        "results": results,
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    artifact_path = resolved_dir / f"ne_014_intent_input_boundary_{ts}.json"
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    print(f"\nNE-014 Diagnostic Artifact written to: {artifact_path}")
    return artifact


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-014 Intent / Input Command Boundary Harness")
    parser.add_argument("project_path", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    print("NE-014 — Intent / Input Command Boundary Harness")
    print(f"Project: {args.project_path}")
    print()

    asyncio.run(run_experiment_ne014(project_path=args.project_path))
