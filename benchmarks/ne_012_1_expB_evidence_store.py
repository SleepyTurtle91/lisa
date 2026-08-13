"""
NE-012.1 Experiment B: Epistemic Evidence Store Benchmark Harness

Runs a session flight with recorder ingestion to verify that asking
"What has actually been verified in this session?" can be evaluated directly
from EvidenceStore provenance query output (OBSERVED vs DOCUMENTED vs INFERRED vs UNVERIFIED)
rather than depending on model self-reflection.
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


async def run_experiment_b(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne012_1_expB_{timestamp}"
    recorder = FlightRecorder(session_id=session_id, log_dir=resolved_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    try:
        await runtime.initialize()
        await runtime.register_provider(OllamaProvider())
        runtime.tool_registry.register(ReadFileTool())
        runtime.tool_registry.register(ListDirectoryTool())

        ctx = SessionContext(
            project_path=project_path,
            workspace_name="ne_012_1_expB",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )
        session = runtime.create_session(ctx)

        # Step 1: Execute a real tool call to populate recorder evidence
        step1_res = await session.send_message("read README.md")

        # Step 2: Ingest recorder events into EvidenceStore
        store = EvidenceStore()
        for event in recorder.get_events():
            store.ingest_event(event)

        # Step 3: Query EvidenceStore for provenance
        provenance = store.summarize_provenance()

        artifact = {
            "experiment": "NE-012.1-ExperimentB",
            "title": "Epistemic Evidence Store Provenance Isolation",
            "timestamp": datetime.now().isoformat() + "Z",
            "project_path": project_path,
            "step1_prompt": "read README.md",
            "step1_response": step1_res,
            "provenance_summary": provenance,
            "observed_items": [i.summary for i in store.query(EvidenceCategory.OBSERVED)],
            "inferred_items_count": len(store.query(EvidenceCategory.INFERRED)),
            "unverified_items_count": len(store.query(EvidenceCategory.UNVERIFIED)),
            "recorder_file": str(recorder.log_file),
        }

        artifact_path = resolved_dir / f"ne_012_1_expB_evidence_store_{timestamp}.json"
        with open(artifact_path, "w", encoding="utf-8") as fh:
            json.dump(artifact, fh, indent=2)

        print(f"Artifact written to: {artifact_path}")
        print(f"Observed count: {provenance['OBSERVED_count']}")
        print(f"Observed tools: {provenance['observed_tools']}")

        return artifact
    finally:
        try:
            await runtime.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-012.1 Experiment B Epistemic Evidence Store Benchmark")
    parser.add_argument("project_path", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    asyncio.run(run_experiment_b(project_path=args.project_path))
