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
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import WriteFileTool, ListDirectoryTool
from lisa.core.context import SessionContext, Capability
from lisa.engine.construction import ModelConstructionEngine

async def run_ab_experiment():
    target_dir = "/home/user/development/projects/lisa"
    benchmarks_dir = Path(__file__).resolve().parent
    
    print("==========================================================================================")
    print("🧪 PROJECT BANDURA — CONTROLLED A/B EXPERIMENT: MODEL SCAFFOLDING IMPACT")
    print(f"Target Model  : qwen3:1.7b")
    print(f"Target Project: {target_dir}")
    print("==========================================================================================\n")
    
    runtime = LisaRuntime()
    await runtime.initialize()
    await runtime.register_provider(OllamaProvider())
    
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    
    test_task = {
        "id": "AB_T1_debug_analysis",
        "prompt": "Inspect cli/main.py and explain how command options 'doctor' and 'compare' are handled."
    }
    
    # 1. Variant A: Baseline (Without Scaffolding / Generic Instruction)
    print("------------------------------------------------------------------------------------------")
    print("🅰️  VARIANT A: BASELINE (Generic Instruction - No Scaffolding)")
    print(f"Prompt: \"{test_task['prompt']}\"")
    print("------------------------------------------------------------------------------------------")
    
    ctx_a = SessionContext(
        project_path=target_dir,
        workspace_name="ab_baseline",
        provider_id="ollama",
        model_name="qwen3:1.7b",
        capabilities=[Capability.CHAT, Capability.TOOLS]
    )
    session_a = runtime.create_session(ctx_a)
    
    start_a = time.perf_counter()
    resp_a = await session_a.send_message(test_task["prompt"])
    dur_a_ms = round((time.perf_counter() - start_a) * 1000.0, 2)
    tel_a = session_a.session_telemetry
    tok_sec_a = round((tel_a.total_completion_tokens / (dur_a_ms / 1000.0)), 2) if dur_a_ms > 0 else 0.0
    
    print(f"   ⏱️  Latency       : {dur_a_ms} ms")
    print(f"   📊 Tok/sec       : {tok_sec_a}")
    print(f"   🛠️  Tool Calls    : {tel_a.total_tool_calls}")
    print(f"   💬 Prompt Tokens : {tel_a.total_prompt_tokens} | Completion: {tel_a.total_completion_tokens}")
    print(f"   Excerpt          : \"{str(resp_a)[:150].replace('\n', ' ')}...\"")
    print("------------------------------------------------------------------------------------------\n")
    
    # 2. Variant B: Scaffolded (With ModelConstructionProfile Scaffolding)
    print("------------------------------------------------------------------------------------------")
    print("🅱️  VARIANT B: SCAFFOLDED (L.I.S.A. Teacher Scaffolding Profile)")
    print(f"Prompt: \"{test_task['prompt']}\"")
    print("------------------------------------------------------------------------------------------")
    
    scaffold = ModelConstructionEngine.get_profile("qwen3:1.7b")
    print(f"   ✓ Applied Tier: {scaffold.tier.upper()} ({scaffold.instruction_style})")
    print(f"   ✓ Rules       : {', '.join(scaffold.active_rules)}")
    
    scaffolded_prompt = f"{scaffold.scaffolded_system_prompt}\n\nUSER REQUEST:\n{test_task['prompt']}"
    
    ctx_b = SessionContext(
        project_path=target_dir,
        workspace_name="ab_scaffolded",
        provider_id="ollama",
        model_name="qwen3:1.7b",
        capabilities=[Capability.CHAT, Capability.TOOLS]
    )
    session_b = runtime.create_session(ctx_b)
    
    start_b = time.perf_counter()
    resp_b = await session_b.send_message(scaffolded_prompt)
    dur_b_ms = round((time.perf_counter() - start_b) * 1000.0, 2)
    tel_b = session_b.session_telemetry
    tok_sec_b = round((tel_b.total_completion_tokens / (dur_b_ms / 1000.0)), 2) if dur_b_ms > 0 else 0.0
    
    print(f"   ⏱️  Latency       : {dur_b_ms} ms")
    print(f"   📊 Tok/sec       : {tok_sec_b}")
    print(f"   🛠️  Tool Calls    : {tel_b.total_tool_calls}")
    print(f"   💬 Prompt Tokens : {tel_b.total_prompt_tokens} | Completion: {tel_b.total_completion_tokens}")
    print(f"   Excerpt          : \"{str(resp_b)[:150].replace('\n', ' ')}...\"")
    print("------------------------------------------------------------------------------------------\n")
    
    # Save A/B artifact
    ab_report = {
        "timestamp": datetime.now().isoformat(),
        "task_id": test_task["id"],
        "prompt": test_task["prompt"],
        "variant_a_baseline": {
            "model": "qwen3:1.7b",
            "latency_ms": dur_a_ms,
            "tok_sec": tok_sec_a,
            "tool_calls": tel_a.total_tool_calls,
            "prompt_tokens": tel_a.total_prompt_tokens,
            "completion_tokens": tel_a.total_completion_tokens,
            "response_snippet": str(resp_a)[:300]
        },
        "variant_b_scaffolded": {
            "model": "qwen3:1.7b",
            "scaffold_tier": scaffold.tier,
            "latency_ms": dur_b_ms,
            "tok_sec": tok_sec_b,
            "tool_calls": tel_b.total_tool_calls,
            "prompt_tokens": tel_b.total_prompt_tokens,
            "completion_tokens": tel_b.total_completion_tokens,
            "response_snippet": str(resp_b)[:300]
        }
    }
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_file = benchmarks_dir / f"ab_scaffolding_experiment_{timestamp_str}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ab_report, f, indent=2)
        
    print("==========================================================================================")
    print(f"✅ PROJECT BANDURA A/B Experiment Completed! Artifact saved to:\n   {out_file}")
    print("==========================================================================================")
    
    await runtime.shutdown()

if __name__ == "__main__":
    asyncio.run(run_ab_experiment())
