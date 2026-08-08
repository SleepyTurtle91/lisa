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

MATRIX_TASKS = [
    {
        "task_id": "T1_file_retrieval",
        "complexity": "Low",
        "prompt": "Read AGENTS.md in the current project and tell me the primary operating mode rules."
    },
    {
        "task_id": "T2_single_file_edit",
        "complexity": "Low",
        "prompt": "Inspect cli/main.py and explain how command options 'doctor' and 'compare' are handled."
    },
    {
        "task_id": "T3_debugging",
        "complexity": "Medium",
        "prompt": "Diagnose potential unawaited coroutine warnings in provider registry registration loops."
    },
    {
        "task_id": "T4_repo_exploration",
        "complexity": "Medium",
        "prompt": "List and inspect the main directories of the LISA codebase and identify core modules."
    },
    {
        "task_id": "T5_multi_file_edit",
        "complexity": "High",
        "prompt": "Design a multi-file refactoring strategy for linking ExecutionPlanner directly into SessionContext."
    },
    {
        "task_id": "T6_architecture",
        "complexity": "High",
        "prompt": "Analyze L.I.S.A. system architecture and evaluate decoupling between InferenceEngine and ProviderSelector."
    }
]

MATRIX_LEVELS = [
    {
        "level": 0,
        "name": "L0 (None)",
        "builder": lambda task: task
    },
    {
        "level": 2,
        "name": "L2 (Explicit Tool Discipline)",
        "builder": lambda task: f"You are L.I.S.A., an AI engineering assistant.\nRule: Always inspect files using the read_file tool before answering. Do not guess.\n\nTask:\n{task}"
    },
    {
        "level": 4,
        "name": "L4 (Full Construction Profile)",
        "builder": lambda task: f"{ModelConstructionEngine.get_profile('qwen3:1.7b').scaffolded_system_prompt}\n\nUSER REQUEST:\n{task}"
    }
]

async def run_exp_004():
    target_dir = "/home/user/development/projects/lisa"
    benchmarks_dir = Path(__file__).resolve().parent
    
    print("==========================================================================================")
    print("🧪 BANDURA EXP-004: TASK COMPLEXITY × SCAFFOLDING MATRIX (RESPONSE SURFACE DISCOVERY)")
    print("Hypothesis: Minimum Effective Scaffolding (MES) scales with Task Complexity.")
    print(f"Target Model  : qwen3:1.7b")
    print(f"Target Project: {target_dir}")
    print("==========================================================================================\n")
    
    runtime = LisaRuntime()
    await runtime.initialize()
    await runtime.register_provider(OllamaProvider())
    
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    
    matrix_results = []
    
    for task_info in MATRIX_TASKS:
        t_id = task_info["task_id"]
        c_lvl = task_info["complexity"]
        prompt = task_info["prompt"]
        
        print(f"------------------------------------------------------------------------------------------")
        print(f"📌 TASK: {t_id} (Complexity: {c_lvl})")
        print(f"   Prompt: \"{prompt}\"")
        print("------------------------------------------------------------------------------------------")
        
        task_matrix_entry = {
            "task_id": t_id,
            "complexity": c_lvl,
            "prompt": prompt,
            "levels": {}
        }
        
        for lvl_info in MATRIX_LEVELS:
            lvl = lvl_info["level"]
            lvl_name = lvl_info["name"]
            builder = lvl_info["builder"]
            
            ctx = SessionContext(
                project_path=target_dir,
                workspace_name=f"exp04_{t_id}_l{lvl}",
                provider_id="ollama",
                model_name="qwen3:1.7b",
                capabilities=[Capability.CHAT, Capability.TOOLS]
            )
            session = runtime.create_session(ctx)
            
            prompt_to_send = builder(prompt)
            start_t = time.perf_counter()
            resp = await session.send_message(prompt_to_send)
            dur_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            tel = session.session_telemetry
            tok_sec = round((tel.total_completion_tokens / (dur_ms / 1000.0)), 2) if dur_ms > 0 else 0.0
            
            is_hallucinated = "not accessible" in str(resp).lower() or "not exist" in str(resp).lower()
            tool_used = tel.total_tool_calls > 0
            
            res_data = {
                "level": lvl,
                "name": lvl_name,
                "latency_ms": dur_ms,
                "tok_sec": tok_sec,
                "tool_calls": tel.total_tool_calls,
                "tool_used": tool_used,
                "hallucination": is_hallucinated,
                "prompt_tokens": tel.total_prompt_tokens,
                "completion_tokens": tel.total_completion_tokens
            }
            task_matrix_entry["levels"][f"L{lvl}"] = res_data
            status_symbol = "✅" if tool_used and not is_hallucinated else "❌"
            print(f"   [{lvl_name:<30}] Latency: {dur_ms:>8.1f}ms | Tok/s: {tok_sec:>5.1f} | Tool Calls: {tel.total_tool_calls} | {status_symbol}")
            
        matrix_results.append(task_matrix_entry)
        print("------------------------------------------------------------------------------------------\n")

    exp_report = {
        "experiment_id": "EXP-004",
        "title": "Task Complexity x Scaffolding Response Surface Discovery Matrix",
        "evidence_class": "Task Complexity x Scaffolding Surface Matrix",
        "confidence_level": "Moderate",
        "timestamp": datetime.now().isoformat(),
        "brain_model": "qwen3:1.7b",
        "task_count": len(MATRIX_TASKS),
        "levels_tested": [l["name"] for l in MATRIX_LEVELS],
        "matrix_data": matrix_results
    }
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_file = benchmarks_dir / f"exp_004_artifact_{timestamp_str}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(exp_report, f, indent=2)
        
    print("\n==========================================================================================")
    print("🏆 EXP-004 RESPONSE SURFACE DISCOVERY MATRIX RESULTS")
    print("==========================================================================================")
    print(f"{'Task ID':<22} | {'Complexity':<10} | {'L0 Tool Used':<12} | {'L2 Tool Used':<12} | {'L4 Tool Used':<12}")
    print("------------------------------------------------------------------------------------------")
    for entry in matrix_results:
        t_id = entry["task_id"]
        c_lvl = entry["complexity"]
        l0_u = "YES ✅" if entry["levels"]["L0"]["tool_used"] else "NO ❌"
        l2_u = "YES ✅" if entry["levels"]["L2"]["tool_used"] else "NO ❌"
        l4_u = "YES ✅" if entry["levels"]["L4"]["tool_used"] else "NO ❌"
        print(f"{t_id:<22} | {c_lvl:<10} | {l0_u:<12} | {l2_u:<12} | {l4_u:<12}")
    print("==========================================================================================")
    print(f"✅ EXP-004 Artifact saved to: {out_file}")
    print("==========================================================================================")
    
    await runtime.shutdown()

if __name__ == "__main__":
    asyncio.run(run_exp_004())
