"""
NE-012.3 Target Identity Binding Benchmark Harness

Evaluates whether L.I.S.A. can distinguish between:
  - User Intended Target (e.g. 'README.md')
  - Model Selected Fallback Target (e.g. '/' or '.')

Flight Cases:
  - C1: "list README.md" -> must trigger Target Identity Mismatch rejection if model proposes root '/' or '.' fallback.
  - C2: "list docs" -> valid candidate target 'docs'; must execute cleanly if model targets 'docs'.
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
class IdentityFlightCase:
    case_id: str
    prompt: str
    description: str


CASES: List[IdentityFlightCase] = [
    IdentityFlightCase("C1", "list README.md", "Prompt specifies file 'README.md'; rejects model fallback '/' or '.'"),
    IdentityFlightCase("C2", "list docs", "Prompt specifies directory 'docs'; valid target execution"),
]


@dataclass
class IdentityFlightResult:
    case_id: str
    prompt: str
    description: str
    tool_calls_made: int
    first_tool_name: Optional[str]
    first_tool_path_arg: Optional[str]
    tool_success: Optional[bool]
    tool_error: Optional[str]
    identity_mismatch_blocked: bool
    response_text: str
    recorder_file: str


async def run_identity_case(
    case: IdentityFlightCase, project_path: str, output_dir: Path
) -> IdentityFlightResult:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne012_3_{case.case_id}_{timestamp}"
    recorder = FlightRecorder(session_id=session_id, log_dir=output_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    first_tool_name: Optional[str] = None
    first_tool_path_arg: Optional[str] = None
    tool_success: Optional[bool] = None
    tool_error: Optional[str] = None
    identity_mismatch_blocked = False
    tool_calls_made = 0
    response_text = ""

    try:
        await runtime.initialize()
        await runtime.register_provider(OllamaProvider())
        runtime.tool_registry.register(ReadFileTool())
        runtime.tool_registry.register(ListDirectoryTool())

        ctx = SessionContext(
            project_path=project_path,
            workspace_name="ne_012_3_identity",
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
                    if metadata.get("identity_mismatch"):
                        identity_mismatch_blocked = True

        return IdentityFlightResult(
            case_id=case.case_id,
            prompt=case.prompt,
            description=case.description,
            tool_calls_made=tool_calls_made,
            first_tool_name=first_tool_name,
            first_tool_path_arg=first_tool_path_arg,
            tool_success=tool_success,
            tool_error=tool_error,
            identity_mismatch_blocked=identity_mismatch_blocked,
            response_text=response_text,
            recorder_file=str(recorder.log_file),
        )
    finally:
        try:
            await runtime.shutdown()
        except Exception:
            pass


async def run_experiment_ne012_3(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    results: List[IdentityFlightResult] = []
    for case in CASES:
        print(f"  [{case.case_id}] Prompt: '{case.prompt}'")
        res = await run_identity_case(case=case, project_path=project_path, output_dir=resolved_dir)
        results.append(res)
        print(f"         → tool={res.first_tool_name!r}, path={res.first_tool_path_arg!r}, identity_mismatch_blocked={res.identity_mismatch_blocked}")

    artifact = {
        "experiment": "NE-012.3",
        "title": "Target Identity Binding Benchmark",
        "timestamp": datetime.now().isoformat() + "Z",
        "project_path": project_path,
        "model": "qwen3:1.7b",
        "provider": "ollama",
        "observations": [asdict(r) for r in results],
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    artifact_path = resolved_dir / f"ne_012_3_target_identity_{ts}.json"
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    print(f"\nTarget Identity Benchmark Artifact written to: {artifact_path}")
    return artifact


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-012.3 Target Identity Binding Benchmark")
    parser.add_argument("project_path", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    print("NE-012.3 — Target Identity Binding Benchmark")
    print(f"Project: {args.project_path}")
    print()

    asyncio.run(run_experiment_ne012_3(project_path=args.project_path))
