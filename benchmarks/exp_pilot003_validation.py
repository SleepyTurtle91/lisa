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
from lisa.engine.analyzer import TaskAnalyzer
from lisa.engine.planner import ExecutionPlanner

async def run_pilot003_validation():
    target_dir = "/home/user/development/projects/extro_pos"
    benchmarks_dir = Path(__file__).resolve().parent
    
    print("==========================================================================================")
    print("🧪 BANDURA PILOT-003: ENGINEERING EVIDENCE MODE BEHAVIORAL VALIDATION FLIGHT")
    print("Prompt: \"Add a simple reusable RetailHeader widget... First inspect existing project structure.\"")
    print(f"Target Project: {target_dir}")
    print("==========================================================================================\n")
    
    runtime = LisaRuntime()
    await runtime.initialize()
    await runtime.register_provider(OllamaProvider())
    
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    
    prompt = "Add a simple reusable RetailHeader widget to the Flutter project. First inspect the existing project structure and relevant UI conventions. Do not modify anything yet. Explain which files would need to change and why."
    
    # 1. Task Analysis & Planning
    profile = TaskAnalyzer.analyze(prompt)
    available_tools = ["read_file", "write_file", "list_directory"]
    plan = ExecutionPlanner.create_plan(profile, "ollama", "qwen3:1.7b", available_tools)
    
    print("------------------------------------------------------------------------------------------")
    print("📋 TASK ANALYSIS & EXECUTION PLAN:")
    print(f"   Intent Detected       : {profile.detected_intent}")
    print(f"   Evidence Gate Required: {profile.requires_evidence_gate}")
    print(f"   Scaffolding Tier      : {plan.scaffolded_env.tier.upper()}")
    print(f"   Instruction Style     : {plan.scaffolded_env.instruction_style}")
    print(f"   Active Rules Count    : {len(plan.scaffolded_env.active_rules)}")
    print("------------------------------------------------------------------------------------------\n")
    
    ctx = SessionContext(
        project_path=target_dir,
        workspace_name="pilot003_validation",
        provider_id="ollama",
        model_name="qwen3:1.7b",
        capabilities=[Capability.CHAT, Capability.TOOLS]
    )
    session = runtime.create_session(ctx)
    
    # Send message with Engineering Evidence System Prompt
    full_prompt = f"{plan.scaffolded_env.scaffolded_system_prompt}\n\nUSER REQUEST:\n{prompt}"
    
    start_t = time.perf_counter()
    resp = await session.send_message(full_prompt)
    dur_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
    tel = session.session_telemetry
    
    tok_sec = round((tel.total_completion_tokens / (dur_ms / 1000.0)), 2) if dur_ms > 0 else 0.0
    tool_calls_made = tel.total_tool_calls
    is_hallucinated = "not accessible" in str(resp).lower() or "not exist" in str(resp).lower()
    
    print("------------------------------------------------------------------------------------------")
    print("📊 PILOT-003 BEHAVIORAL EXECUTION TELEMETRY:")
    print(f"   Latency              : {dur_ms} ms")
    print(f"   Throughput           : {tok_sec} tok/s")
    print(f"   Prompt Tokens        : {tel.total_prompt_tokens}")
    print(f"   Completion Tokens    : {tel.total_completion_tokens}")
    print(f"   Tool Calls Invoked   : {tool_calls_made}")
    print(f"   Hallucination Status : {'NO HALLUCINATION ✅' if not is_hallucinated else 'HALLUCINATED ❌'}")
    print("------------------------------------------------------------------------------------------")
    print("\n📝 RESPONSE EXCERPT:")
    print(str(resp)[:800])
    print("...\n------------------------------------------------------------------------------------------\n")

    val_report = {
        "experiment_id": "PILOT-003-VALIDATION",
        "title": "Engineering Evidence Mode Behavioral Flight",
        "evidence_class": "Empirical Behavioral Flight",
        "confidence_level": "Moderate",
        "timestamp": datetime.now().isoformat(),
        "brain_model": "qwen3:1.7b",
        "intent_detected": profile.detected_intent,
        "requires_evidence_gate": profile.requires_evidence_gate,
        "scaffold_tier": plan.scaffolded_env.tier,
        "instruction_style": plan.scaffolded_env.instruction_style,
        "latency_ms": dur_ms,
        "tok_sec": tok_sec,
        "prompt_tokens": tel.total_prompt_tokens,
        "completion_tokens": tel.total_completion_tokens,
        "tool_calls": tool_calls_made,
        "hallucination": is_hallucinated,
        "response_text": str(resp)
    }
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_file = benchmarks_dir / f"pilot003_artifact_{timestamp_str}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(val_report, f, indent=2)
        
    print(f"✅ PILOT-003 Validation Artifact saved to: {out_file}")
    print("==========================================================================================")
    
    await runtime.shutdown()

if __name__ == "__main__":
    asyncio.run(run_pilot003_validation())
