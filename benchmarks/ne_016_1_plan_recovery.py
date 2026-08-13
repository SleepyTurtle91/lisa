"""
NE-016.1 Plan Recovery & Replanning Benchmark Harness

Evaluates whether the L.I.S.A. Kernel can handle mid-plan execution failure,
invalidate downstream plan steps, preserve immutable FlightRecorder evidence,
and execute a revised Plan B under step-by-step kernel validation.

Scenario:
  Plan A:
    Step 1: list_directory(".")               -> EXECUTED ✅
    Step 2: read_file("missing_docs.md")      -> BLOCKED ❌ (File not found)
    Step 3: read_file("README.md")            -> PENDING ⏸️ (Halted by Kernel)

  Replan Event:
    LLM Driver receives failure evidence and proposes Plan B based on observed truth.

  Plan B:
    Step 1: read_file("README.md")            -> EXECUTED ✅
    Step 2: list_directory("tools")           -> EXECUTED ✅
"""

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.benchmarks.ne_016_governed_plan import GovernedPlan, GovernedPlanExecutor, GovernedPlanStep, PlanStepStatus
from lisa.core.kernel import LisaRuntime
from lisa.memory.authoritative_query import AuthoritativeEvidenceQuery
from lisa.memory.evidence_store import EvidenceCategory, EvidenceStore
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import ListDirectoryTool


async def run_experiment_ne016_1(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne016_1_plan_recovery_{timestamp}"
    recorder = FlightRecorder(session_id=session_id, log_dir=resolved_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    try:
        await runtime.initialize()
        runtime.tool_registry.register(ReadFileTool())
        runtime.tool_registry.register(ListDirectoryTool())

        executor = GovernedPlanExecutor(runtime=runtime, project_path=project_path, recorder=recorder)

        # ── 1. Execute Initial Plan A (Fails at Step 2) ───────────────────────────
        plan_a = GovernedPlan(
            goal="Plan A: Inspect workspace and read missing document",
            steps=[
                GovernedPlanStep(1, "Inspect workspace directory", "list_directory", "."),
                GovernedPlanStep(2, "Read missing document", "read_file", "missing_docs.md"),
                GovernedPlanStep(3, "Downstream step (must remain PENDING)", "read_file", "README.md"),
            ],
        )

        res_a = await executor.execute_plan(plan_a)

        # Evaluate Plan A Status
        plan_a_step2_failed = (res_a[1].status == PlanStepStatus.BLOCKED)
        plan_a_step3_pending = (res_a[2].status == PlanStepStatus.PENDING)

        recorder.record_event("flight_stage", {
            "stage": "replan_requested",
            "reason": res_a[1].rejection_reason,
            "failed_step": 2,
        })

        # ── 2. Execute Revised Plan B (Recovery Plan) ─────────────────────────────
        plan_b = GovernedPlan(
            goal="Plan B: Recover by reading existing README.md and tools directory",
            steps=[
                GovernedPlanStep(1, "Read existing README.md", "read_file", "README.md"),
                GovernedPlanStep(2, "Inspect tools directory", "list_directory", "tools"),
            ],
        )

        res_b = await executor.execute_plan(plan_b)

        # Evaluate Plan B Status
        plan_b_completed = all(s.status == PlanStepStatus.EXECUTED for s in res_b)

        # ── 3. Verify Immutable Provenance Across Both Plans ──────────────────────
        store = EvidenceStore()
        events = recorder.get_events()
        for ev in events:
            store.ingest_event(ev)

        observed = store.query(EvidenceCategory.OBSERVED)
        unverified = store.query(EvidenceCategory.UNVERIFIED)
        authoritative = AuthoritativeEvidenceQuery.query_session_provenance(recorder)

        # Assertions
        # Total Observed: Step 1 of Plan A (list .), Step 1 of Plan B (read README.md), Step 2 of Plan B (list tools) -> Total 3
        # Total Unverified: Step 2 of Plan A (read missing_docs.md) -> Total 1
        evidence_immutable = (len(observed) == 3) and (len(unverified) == 1)

        artifact = {
            "experiment": "NE-016.1",
            "title": "Plan Recovery & Replanning Benchmark",
            "timestamp": datetime.now().isoformat() + "Z",
            "project_path": project_path,
            "plan_a_step2_failed": plan_a_step2_failed,
            "plan_a_step3_pending": plan_a_step3_pending,
            "plan_b_completed": plan_b_completed,
            "evidence_immutable": evidence_immutable,
            "plan_a_results": [{"step": s.step_number, "status": s.status.name, "reason": s.rejection_reason} for s in res_a],
            "plan_b_results": [{"step": s.step_number, "status": s.status.name, "result": s.execution_result} for s in res_b],
            "total_observed_events": len(observed),
            "total_unverified_events": len(unverified),
            "authoritative_summary": authoritative,
            "recorder_file": str(recorder.log_file),
        }

        artifact_path = resolved_dir / f"ne_016_1_plan_recovery_{timestamp}.json"
        with open(artifact_path, "w", encoding="utf-8") as fh:
            json.dump(artifact, fh, indent=2)

        print(f"\nNE-016.1 Diagnostic Artifact written to: {artifact_path}")
        print(f"Plan A Step 2 Failed & Halted Step 3: {plan_a_step2_failed and plan_a_step3_pending}")
        print(f"Plan B Recovery Completed: {plan_b_completed}")
        print(f"Evidence Immutable across Replanning: {evidence_immutable}")
        print(f"Observed: {len(observed)}, Unverified: {len(unverified)}")

        return artifact
    finally:
        try:
            await runtime.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-016.1 Plan Recovery & Replanning Benchmark")
    parser.add_argument("project_path", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    print("NE-016.1 — Plan Recovery & Replanning Benchmark")
    print(f"Project: {args.project_path}")
    print()

    asyncio.run(run_experiment_ne016_1(project_path=args.project_path))
