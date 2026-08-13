"""
NE-014.1 Input Boundary Classifier Benchmark Harness

Evaluates whether InputBoundaryClassifier correctly routes:
  1. Direct Commands ('read BOOT.md', 'doctor', 'help') -> DIRECT_COMMAND
  2. Absolute / Relative Paths ('/workspace/Projects/retails') -> PATH_INPUT
  3. Compound Natural Language ('read files inside /docs and suggest a plan') -> NATURAL_LANGUAGE (no prefix hijacking!)
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

from lisa.cli.input_classifier import InputBoundaryClassifier, InputClass


@dataclass
class ClassifierTestCase:
    case_id: str
    prompt: str
    expected_class: InputClass


TEST_CASES: List[ClassifierTestCase] = [
    ClassifierTestCase("TC1", "read files inside /docs and suggest a plan", InputClass.NATURAL_LANGUAGE),
    ClassifierTestCase("TC2", "/workspace/Projects/retails", InputClass.PATH_INPUT),
    ClassifierTestCase("TC3", "read BOOT.md", InputClass.DIRECT_COMMAND),
    ClassifierTestCase("TC4", "doctor", InputClass.DIRECT_COMMAND),
    ClassifierTestCase("TC5", "how does the memory architecture work?", InputClass.NATURAL_LANGUAGE),
]


async def run_experiment_ne014_1(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    results = []
    all_passed = True

    for case in TEST_CASES:
        res = InputBoundaryClassifier.classify(case.prompt, project_path=project_path)
        passed = (res.input_class == case.expected_class)
        if not passed:
            all_passed = False

        results.append({
            "case_id": case.case_id,
            "prompt": case.prompt,
            "expected_class": case.expected_class.name,
            "actual_class": res.input_class.name,
            "command": res.command,
            "target": res.target,
            "passed": passed,
        })
        print(f"  [{case.case_id}] Prompt: {case.prompt!r}")
        print(f"         → expected={case.expected_class.name}, actual={res.input_class.name}, passed={passed}")

    artifact = {
        "experiment": "NE-014.1",
        "title": "Input Boundary Classifier Benchmark",
        "timestamp": datetime.now().isoformat() + "Z",
        "project_path": project_path,
        "all_passed": all_passed,
        "results": results,
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    artifact_path = resolved_dir / f"ne_014_1_input_classifier_{ts}.json"
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    print(f"\nNE-014.1 Benchmark Artifact written to: {artifact_path}")
    print(f"All Cases Passed: {all_passed}")
    return artifact


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-014.1 Input Boundary Classifier Benchmark")
    parser.add_argument("project_path", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    print("NE-014.1 — Input Boundary Classifier Benchmark")
    print(f"Project: {args.project_path}")
    print()

    asyncio.run(run_experiment_ne014_1(project_path=args.project_path))
