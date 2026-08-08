import sys
import os
import time
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add project root and parent to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.core.kernel import LisaRuntime
from lisa.providers.ollama.provider import OllamaProvider
from lisa.providers.openai.provider import OpenAIProvider
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import WriteFileTool, ListDirectoryTool
from lisa.core.context import SessionContext, Capability
from lisa.engine.auto_selector import AutoSelector
from lisa.providers.selector import ProviderSelector

CALIBRATION_TASKS = [
    {
        "id": "T1_file_read",
        "category": "file_reading",
        "prompt": "Read AGENTS.md in the current project and tell me the primary operating mode rules."
    },
    {
        "id": "T2_code_explain",
        "category": "code_explanation",
        "prompt": "Explain the role of BootstrapEngine and how system boot vs project boot is handled."
    },
    {
        "id": "T3_single_file_edit",
        "category": "single_file_edit",
        "prompt": "Analyze how to add a new helper method to TaskAnalyzer to compute prompt token density."
    },
    {
        "id": "T4_multi_file_edit",
        "category": "multi_file_edit",
        "prompt": "Design a multi-file refactoring strategy for linking ExecutionPlanner directly into SessionContext."
    },
    {
        "id": "T5_repo_explore",
        "category": "repo_exploration",
        "prompt": "List and inspect the main directories of the LISA codebase and identify core modules."
    },
    {
        "id": "T6_architecture",
        "category": "architecture_analysis",
        "prompt": "Analyze L.I.S.A. system architecture and evaluate decoupling between InferenceEngine and ProviderSelector."
    },
    {
        "id": "T7_debugging",
        "category": "difficult_debugging",
        "prompt": "Diagnose potential memory leak risks or unawaited coroutine warnings in provider registry registration loops."
    }
]

async def run_calibration_matrix():
    target_dir = "/home/user/development/projects/lisa"
    benchmarks_dir = Path(__file__).resolve().parent
    
    print("==========================================================================================")
    print("🧪 L.I.S.A. EMPIRICAL HARDWARE & TASK CALIBRATION SUITE")
    print(f"Target Project: {target_dir}")
    print("==========================================================================================\n")
    
    runtime = LisaRuntime()
    await runtime.initialize()
    await runtime.register_provider(OllamaProvider())
    await runtime.register_provider(OpenAIProvider())
    
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    
    p_selector = ProviderSelector(runtime.provider_registry)
    auto_selector = AutoSelector(p_selector)
    
    ctx = SessionContext(
        project_path=target_dir,
        workspace_name="calibration_flight",
        provider_id="ollama",
        model_name="qwen3:1.7b",
        capabilities=[Capability.CHAT, Capability.TOOLS]
    )
    session = runtime.create_session(ctx)
    
    results_summary = []
    
    for task in CALIBRATION_TASKS:
        t_id = task["id"]
        cat = task["category"]
        prompt = task["prompt"]
        
        print(f"📌 Task: {t_id} ({cat})")
        print(f"   Prompt: \"{prompt}\"")
        
        plan = await auto_selector.plan_execution(prompt)
        
        start_t = time.perf_counter()
        response = await session.send_message(prompt)
        dur_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        
        tel = session.session_telemetry
        tok_sec = round((tel.total_completion_tokens / (dur_ms / 1000.0)), 2) if dur_ms > 0 else 0.0
        
        record = {
            "task_id": t_id,
            "category": cat,
            "complexity": plan.complexity_level,
            "provider_id": plan.provider_id,
            "model_name": plan.model_name,
            "hardware_score": plan.hardware_score,
            "hardware_load": plan.hardware_load_tier,
            "latency_ms": dur_ms,
            "prompt_tokens": tel.total_prompt_tokens,
            "completion_tokens": tel.total_completion_tokens,
            "total_tokens": tel.total_tokens,
            "tok_sec": tok_sec,
            "reason": plan.reason
        }
        results_summary.append(record)
        
        print(f"   ✓ Plan: {plan.complexity_level} | Model: {plan.model_name} | Latency: {dur_ms} ms | Tok/sec: {tok_sec}")
        print("──────────────────────────────────────────────────────────────────────────────────────────\n")

    # Save summary artifact
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_file = benchmarks_dir / f"calibration_matrix_{timestamp_str}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"calibration_runs": results_summary}, f, indent=2)
        
    print("==========================================================================================")
    print(f"✅ Calibration flight completed successfully! Saved artifact to:\n   {out_file}")
    print("==========================================================================================")
    
    await runtime.shutdown()

if __name__ == "__main__":
    asyncio.run(run_calibration_matrix())
