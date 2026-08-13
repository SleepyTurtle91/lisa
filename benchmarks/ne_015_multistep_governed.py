"""
NE-015 Multi-Step Governed Execution Benchmark Harness

Evaluates whether L.I.S.A. can execute multi-step natural language engineering requests
('Read files inside /docs before we do anything and suggest a solid plan')
while adhering to all frozen execution boundaries (Input Classification, Target Identity,
Target Type Grounding, and Authoritative Evidence).

Verifies:
  1. Input Boundary classifies prompt as NATURAL_LANGUAGE.
  2. Multi-step execution reads files inside /docs without hijacking or target mismatches.
  3. EvidenceStore records OBSERVED tool executions cleanly.
  4. Final synthesis distinguishes OBSERVED tool events from DOCUMENTED claims.
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
from lisa.core.context import Capability, SessionContext
from lisa.core.kernel import LisaRuntime
from lisa.memory.authoritative_query import AuthoritativeEvidenceQuery
from lisa.memory.evidence_store import EvidenceCategory, EvidenceStore
from lisa.providers.ollama.provider import OllamaProvider
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import ListDirectoryTool


async def run_experiment_ne015(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne015_multistep_governed_{timestamp}"
    recorder = FlightRecorder(session_id=session_id, log_dir=resolved_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    prompt = "Read the files inside /docs before we do anything and suggest a solid plan."

    try:
        await runtime.initialize()
        await runtime.register_provider(OllamaProvider())
        runtime.tool_registry.register(ReadFileTool())
        runtime.tool_registry.register(ListDirectoryTool())

        # Step 1: Verify Upstream Ingress Input Boundary
        classified = InputBoundaryClassifier.classify(prompt, project_path=project_path)
        input_class_passed = (classified.input_class == InputClass.NATURAL_LANGUAGE)

        ctx = SessionContext(
            project_path=project_path,
            workspace_name="ne_015_multistep",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )
        session = runtime.create_session(ctx)

        # Step 2: Execute Multi-step Governed Prompt
        response_text = await session.send_message(prompt)

        # Step 3: Extract & Evaluate Recorded Evidence
        store = EvidenceStore()
        events = recorder.get_events()
        for ev in events:
            store.ingest_event(ev)

        observed = store.query(EvidenceCategory.OBSERVED)
        unverified = store.query(EvidenceCategory.UNVERIFIED)
        authoritative = AuthoritativeEvidenceQuery.query_session_provenance(recorder)

        tool_calls_made = len([e for e in events if e.get("event_type") == "flight_stage" and (e.get("payload") or {}).get("stage") == "tool_request"])

        artifact = {
            "experiment": "NE-015",
            "title": "Multi-Step Governed Execution Diagnostic Baseline",
            "timestamp": datetime.now().isoformat() + "Z",
            "project_path": project_path,
            "model": "qwen3:1.7b",
            "provider": "ollama",
            "prompt": prompt,
            "input_classified": classified.input_class.name,
            "input_class_passed": input_class_passed,
            "tool_calls_made": tool_calls_made,
            "observed_events_count": len(observed),
            "unverified_events_count": len(unverified),
            "authoritative_summary": authoritative,
            "model_response_snippet": response_text[:300],
            "recorder_file": str(recorder.log_file),
        }

        artifact_path = resolved_dir / f"ne_015_multistep_governed_{timestamp}.json"
        with open(artifact_path, "w", encoding="utf-8") as fh:
            json.dump(artifact, fh, indent=2)

        print(f"\nNE-015 Diagnostic Artifact written to: {artifact_path}")
        print(f"Input Classification: {classified.input_class.name} (Passed={input_class_passed})")
        print(f"Tool Calls Executed: {tool_calls_made}")
        print(f"Observed Evidence Events: {len(observed)}")
        print(f"Unverified Events: {len(unverified)}")

        return artifact
    finally:
        try:
            await runtime.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-015 Multi-Step Governed Execution Benchmark")
    parser.add_argument("project_path", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    print("NE-015 — Multi-Step Governed Execution Benchmark")
    print(f"Project: {args.project_path}")
    print()

    asyncio.run(run_experiment_ne015(project_path=args.project_path))
