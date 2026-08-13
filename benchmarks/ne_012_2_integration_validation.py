"""
NE-012.2: End-to-End Grounded Session Integration Validation Harness

Tests whether NE-012.1 A (Target Grounding Pre-Dispatch Guard) and
NE-012.1 B (Recorder-Backed EvidenceStore Epistemic Provenance)
compose correctly in real end-to-end sessions.

Flight Cases:
  - Flight A: Invalid Target Operation ("list README.md")
    Expected: TargetInspector intercepts list_directory(FILE) -> BLOCKED / GUARDED before execution.
  - Flight B: Valid Directory Operation ("list docs")
    Expected: TargetInspector validates list_directory(DIRECTORY) -> Executed -> OBSERVED success.
  - Flight C: Provenance Query ("What has actually been verified in this session?")
    Expected: EvidenceStore provides structured provenance directly from recorder events.

Rule: Do not modify FlightConsole, intent parser, or runtime code. Preserve empirical observations as evidence.
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
from lisa.memory.evidence_store import EvidenceCategory, EvidenceStore
from lisa.providers.ollama.provider import OllamaProvider
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import ListDirectoryTool


@dataclass
class IntegrationFlightCase:
    flight_id: str
    prompt: str
    description: str


CASES: List[IntegrationFlightCase] = [
    IntegrationFlightCase("Flight_A", "list README.md", "Invalid operation: list_directory on FILE target"),
    IntegrationFlightCase("Flight_B", "list docs", "Valid operation: list_directory on DIRECTORY target"),
    IntegrationFlightCase("Flight_C", "What has actually been verified in this session?", "Provenance query: EvidenceStore recorder derivation"),
]


@dataclass
class IntegrationFlightResult:
    flight_id: str
    prompt: str
    description: str
    tool_calls_made: int
    first_tool_name: Optional[str]
    first_tool_path_arg: Optional[str]
    tool_success: Optional[bool]
    tool_error: Optional[str]
    rejected_before_execution: bool
    response_text: str
    evidence_observed_count: int
    evidence_observed_summaries: List[str]
    recorder_file: str


async def run_integration_flight(
    case: IntegrationFlightCase, project_path: str, output_dir: Path
) -> IntegrationFlightResult:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne012_2_{case.flight_id}_{timestamp}"
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
            workspace_name="ne_012_2_integration",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )
        session = runtime.create_session(ctx)

        # For Flight C (provenance test), run a preceding read_file tool to ensure session has recorded evidence
        if case.flight_id == "Flight_C":
            await session.send_message("read README.md")

        response_text = await session.send_message(case.prompt)

        # Parse raw recorder events into EvidenceStore
        store = EvidenceStore()
        for event in recorder.get_events():
            store.ingest_event(event)

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

        observed_items = store.query(EvidenceCategory.OBSERVED)

        return IntegrationFlightResult(
            flight_id=case.flight_id,
            prompt=case.prompt,
            description=case.description,
            tool_calls_made=tool_calls_made,
            first_tool_name=first_tool_name,
            first_tool_path_arg=first_tool_path_arg,
            tool_success=tool_success,
            tool_error=tool_error,
            rejected_before_execution=rejected_before_exec,
            response_text=response_text,
            evidence_observed_count=len(observed_items),
            evidence_observed_summaries=[i.summary for i in observed_items],
            recorder_file=str(recorder.log_file),
        )
    finally:
        try:
            await runtime.shutdown()
        except Exception:
            pass


async def run_experiment_ne012_2(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    results: List[IntegrationFlightResult] = []
    for case in CASES:
        print(f"  [{case.flight_id}] Prompt: '{case.prompt}'")
        res = await run_integration_flight(case=case, project_path=project_path, output_dir=resolved_dir)
        results.append(res)
        print(f"         → tool={res.first_tool_name!r}, path={res.first_tool_path_arg!r}, rejected_before_exec={res.rejected_before_execution}, evidence_observed={res.evidence_observed_count}")

    artifact = {
        "experiment": "NE-012.2",
        "title": "End-to-End Grounded Session Integration Validation",
        "timestamp": datetime.now().isoformat() + "Z",
        "project_path": project_path,
        "model": "qwen3:1.7b",
        "provider": "ollama",
        "flights": [asdict(r) for r in results],
    }

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    artifact_path = resolved_dir / f"ne_012_2_integration_validation_{ts}.json"
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    print(f"\nIntegration Validation Artifact written to: {artifact_path}")
    return artifact


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-012.2 Integration Validation Benchmark")
    parser.add_argument("project_path", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    print(f"NE-012.2 — End-to-End Grounded Session Integration Validation")
    print(f"Project: {args.project_path}")
    print(f"Flights: {len(CASES)}")
    print()

    asyncio.run(run_experiment_ne012_2(project_path=args.project_path))
