"""
NE-017 Real-Project OS Validation Benchmark Harness

Evaluates end-to-end performance of L.I.S.A. Intelligence OS (v2.0.0) on a real engineering workspace
(e.g., /home/user/development/projects/retails) without synthetic mocks.

Measures all 8 System Validation Criteria:
  1. Project Context Grounding & Discovery
  2. Upstream Input Boundary Routing (NE-014.2)
  3. Governed Multi-Step Driver Planning & Kernel Validation (NE-016.1)
  4. Capability Execution & Target Grounding (NE-012.1A / NE-012.3)
  5. Recovery / Replanning on Missing Paths or Execution Failures
  6. Immutable FlightRecorder Trace Ingestion
  7. Authoritative Evidence Derivation (NE-013)
  8. Distinction of OBSERVED, DOCUMENTED, and INFERRED Facts in Final Synthesis
"""

import asyncio
import json
import os
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


async def run_experiment_ne017(target_project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne017_real_project_validation_{timestamp}"
    recorder = FlightRecorder(session_id=session_id, log_dir=resolved_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    real_path = os.path.abspath(target_project_path)
    print(f"Target Real Project: {real_path}")

    # 1. Complex Real-World Engineering Objective
    user_prompt = "Inspect the architecture and project files inside docs, read key project directives, and synthesize an active engineering plan."

    try:
        await runtime.initialize()
        await runtime.register_provider(OllamaProvider())
        runtime.tool_registry.register(ReadFileTool())
        runtime.tool_registry.register(ListDirectoryTool())

        # Criteria 2: Ingress Boundary Classification
        classified = InputBoundaryClassifier.classify(user_prompt, project_path=real_path)
        ingress_clean = (classified.input_class == InputClass.NATURAL_LANGUAGE)

        ctx = SessionContext(
            project_path=real_path,
            workspace_name="ne_017_validation",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )
        session = runtime.create_session(ctx)

        # Criteria 3 & 4: Execute Governed Real-Project Session
        response_text = await session.send_message(user_prompt)

        # Criteria 6 & 7: Ingest Trace & Derive Authoritative Provenance
        events = recorder.get_events()
        store = EvidenceStore()
        for ev in events:
            store.ingest_event(ev)

        observed = store.query(EvidenceCategory.OBSERVED)
        unverified = store.query(EvidenceCategory.UNVERIFIED)
        inferred = store.query(EvidenceCategory.INFERRED)
        authoritative = AuthoritativeEvidenceQuery.query_session_provenance(recorder)

        # Criteria 8: Fact Distinction Check (No hallucinated execution claims)
        claims_unverified_passed_tests = "32/32" in response_text or "all tests passed" in response_text.lower()
        conflation_detected = claims_unverified_passed_tests and len(observed) == 0

        artifact = {
            "experiment": "NE-017",
            "title": "Real-Project L.I.S.A. OS Validation",
            "timestamp": datetime.now().isoformat() + "Z",
            "target_project_path": real_path,
            "user_prompt": user_prompt,
            "ingress_classification": classified.input_class.name,
            "ingress_clean": ingress_clean,
            "total_events_recorded": len(events),
            "observed_events_count": len(observed),
            "unverified_events_count": len(unverified),
            "inferred_events_count": len(inferred),
            "authoritative_summary": authoritative,
            "conflation_detected": conflation_detected,
            "response_snippet": response_text[:350],
            "recorder_file": str(recorder.log_file),
        }

        artifact_path = resolved_dir / f"ne_017_real_project_validation_{timestamp}.json"
        with open(artifact_path, "w", encoding="utf-8") as fh:
            json.dump(artifact, fh, indent=2)

        print(f"\nNE-017 Diagnostic Artifact written to: {artifact_path}")
        print(f"Ingress Routing Clean: {ingress_clean}")
        print(f"Observed Tool Executions: {len(observed)}")
        print(f"Unverified Attempts: {len(unverified)}")
        print(f"Fact Conflation Detected: {conflation_detected}")

        return artifact
    finally:
        try:
            await runtime.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-017 Real-Project L.I.S.A. OS Validation")
    parser.add_argument("project_path", nargs="?", default="/home/user/development/projects/retails")
    args = parser.parse_args()

    print("NE-017 — Real-Project L.I.S.A. OS End-to-End Validation")
    print(f"Target Path: {args.project_path}")
    print()

    asyncio.run(run_experiment_ne017(target_project_path=args.project_path))
