"""
NE-012.1 Experiment A: Target Grounding Benchmark Harness

Runs live model session probes targeting Experiment A:
  - B1: "list README.md" (FILE target + list_directory) -> must trigger pre-invocation grounding guard rejection, preventing root / fallback
  - B2: "read docs" (DIRECTORY target + read_file) -> must trigger pre-invocation grounding guard rejection
  - A1: "read README.md" (FILE target + read_file) -> must execute cleanly
  - A2: "list docs" (DIRECTORY target + list_directory) -> must execute cleanly
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
from lisa.tools.filesystem.standard import ListDirectoryTool


@dataclass
class ExpACase:
    case_id: str
    prompt: str
    expected_outcome: str


CASES: List[ExpACase] = [
    ExpACase("A1", "read README.md", "EXECUTE_SUCCESS"),
    ExpACase("A2", "list docs", "EXECUTE_SUCCESS"),
    ExpACase("B1", "list README.md", "GUARD_REJECTED_BEFORE_EXECUTION"),
    ExpACase("B2", "read docs", "GUARD_REJECTED_BEFORE_EXECUTION_OR_MODEL_CLARIFY"),
]


@dataclass
class ExpAObservation:
    case_id: str
    prompt: str
    expected_outcome: str
    tool_calls_made: int
    first_tool_name: Optional[str]
    first_tool_path_arg: Optional[str]
    tool_success: Optional[bool]
    tool_error: Optional[str]
    rejected_before_execution: bool
    response_text: str
    recorder_file: str


async def run_case(case: ExpACase, project_path: str, output_dir: Path) -> ExpAObservation:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne012_1_expA_{case.case_id}_{timestamp}"
    recorder = FlightRecorder(session_id=session_id, log_dir=output_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    first_tool_name: Optional[str] = None
    first_tool_path_arg: Optional[str] = None
    tool_success: Optional[bool] = None
    tool_error: Optional[str] = None
    rejected_before_exec = False
    tool_calls_made = 0
    response_text = ""

    try:
        await runtime.initialize()
        await runtime.register_provider(OllamaProvider())
        runtime.tool_registry.register(ReadFileTool())
        runtime.tool_registry.register(ListDirectoryTool())

        ctx = SessionContext(
            project_path=project_path,
            workspace_name="ne_012_1_expA",
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
                    tool_error = payload.get("error")
                    metadata = payload.get("metadata") or {}
                    if metadata.get("rejected_before_execution"):
                        rejected_before_exec = True

        return ExpAObservation(
            case_id=case.case_id,
            prompt=case.prompt,
            expected_outcome=case.expected_outcome,
            tool_calls_made=tool_calls_made,
            first_tool_name=first_tool_name,
            first_tool_path_arg=first_tool_path_arg,
            tool_success=tool_success,
            tool_error=tool_error,
            rejected_before_execution=rejected_before_exec,
            response_text=response_text,
            recorder_file=str(recorder.log_file),
        )
    finally:
        try:
            await runtime.shutdown()
        except Exception:
            pass


async def run_experiment(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    observations: List[ExpAObservation] = []
    for case in CASES:
        print(f"  [{case.case_id}] {case.prompt}")
        obs = await run_case(case=case, project_path=project_path, output_dir=resolved_dir)
        observations.append(obs)
        print(f"         → tool={obs.first_tool_name!r}, path={obs.first_tool_path_arg!r}, rejected_before_exec={obs.rejected_before_execution}")

    artifact = {
        "experiment": "NE-012.1-ExperimentA",
        "title": "Target Type Grounding Pre-Invocation Guard Validation",
        "timestamp": datetime.now().isoformat() + "Z",
        "project_path": project_path,
        "observations": [asdict(o) for o in observations],
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    artifact_path = resolved_dir / f"ne_012_1_expA_target_grounding_{ts}.json"
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    print(f"\nArtifact written to: {artifact_path}")
    return artifact


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-012.1 Experiment A Target Grounding Benchmark")
    parser.add_argument("project_path", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    asyncio.run(run_experiment(project_path=args.project_path))
