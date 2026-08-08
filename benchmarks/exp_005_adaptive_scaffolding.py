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

EXP_TASKS = [
    {
        "id": "T1_single_file_edit",
        "complexity": "Low",
        "prompt": "Inspect cli/main.py and explain how command options 'doctor' and 'compare' are handled."
    },
    {
        "id": "T2_debugging",
        "complexity": "Medium",
        "prompt": "Diagnose potential unawaited coroutine warnings in provider registry registration loops."
    },
    {
        "id": "T3_multi_file_edit",
        "complexity": "High",
        "prompt": "Design a multi-file refactoring strategy for linking ExecutionPlanner directly into SessionContext."
    }
]

def build_prompt_l2(task: str) -> str:
    return f"You are L.I.S.A., an AI engineering assistant.\nRule: Always inspect files using the read_file tool before answering. Do not guess.\n\nTask:\n{task}"

def build_prompt_l4(task: str) -> str:
    return f"{ModelConstructionEngine.get_profile('qwen3:1.7b').scaffolded_system_prompt}\n\nUSER REQUEST:\n{task}"

async def run_exp_005():
    target_dir = "/home/user/development/projects/lisa"
    benchmarks_dir = Path(__file__).resolve().parent
    
    print("==========================================================================================")
    print("🧪 BANDURA EXP-005: ADAPTIVE ESCALATION VS. FIXED SCAFFOLDING FLIGHT")
    print("Hypothesis: Adaptive escalation matches Fixed L4 reliability at lower latency & token cost.")
    print(f"Target Model  : qwen3:1.7b")
    print(f"Target Project: {target_dir}")
    print("==========================================================================================\n")
    
    runtime = LisaRuntime()
    await runtime.initialize()
    await runtime.register_provider(OllamaProvider())
    
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    
    task_results = []
    
    for t_info in EXP_TASKS:
        t_id = t_info["id"]
        c_lvl = t_info["complexity"]
        prompt = t_info["prompt"]
        
        print("------------------------------------------------------------------------------------------")
        print(f"📌 TASK: {t_id} (Complexity: {c_lvl})")
        print(f"   Prompt: \"{prompt}\"")
        print("------------------------------------------------------------------------------------------")
        
        # 1. Condition A: Fixed L2
        ctx_a = SessionContext(project_path=target_dir, workspace_name=f"exp05_{t_id}_condA", provider_id="ollama", model_name="qwen3:1.7b", capabilities=[Capability.CHAT, Capability.TOOLS])
        session_a = runtime.create_session(ctx_a)
        start_a = time.perf_counter()
        resp_a = await session_a.send_message(build_prompt_l2(prompt))
        dur_a = round((time.perf_counter() - start_a) * 1000.0, 2)
        tel_a = session_a.session_telemetry
        used_tool_a = tel_a.total_tool_calls > 0
        halluc_a = "not accessible" in str(resp_a).lower() or "not exist" in str(resp_a).lower()
        success_a = used_tool_a and not halluc_a
        
        res_a = {
            "condition": "Fixed L2",
            "latency_ms": dur_a,
            "tool_calls": tel_a.total_tool_calls,
            "prompt_tokens": tel_a.total_prompt_tokens,
            "completion_tokens": tel_a.total_completion_tokens,
            "success": success_a,
            "escalated": False
        }
        print(f"   [Condition A - Fixed L2] Latency: {dur_a:>8.1f}ms | Tools: {tel_a.total_tool_calls} | Tokens: {tel_a.total_tokens} | Success: {'✅' if success_a else '❌'}")
        
        # 2. Condition B: Fixed L4
        ctx_b = SessionContext(project_path=target_dir, workspace_name=f"exp05_{t_id}_condB", provider_id="ollama", model_name="qwen3:1.7b", capabilities=[Capability.CHAT, Capability.TOOLS])
        session_b = runtime.create_session(ctx_b)
        start_b = time.perf_counter()
        resp_b = await session_b.send_message(build_prompt_l4(prompt))
        dur_b = round((time.perf_counter() - start_b) * 1000.0, 2)
        tel_b = session_b.session_telemetry
        used_tool_b = tel_b.total_tool_calls > 0
        halluc_b = "not accessible" in str(resp_b).lower() or "not exist" in str(resp_b).lower()
        success_b = used_tool_b and not halluc_b
        
        res_b = {
            "condition": "Fixed L4",
            "latency_ms": dur_b,
            "tool_calls": tel_b.total_tool_calls,
            "prompt_tokens": tel_b.total_prompt_tokens,
            "completion_tokens": tel_b.total_completion_tokens,
            "success": success_b,
            "escalated": False
        }
        print(f"   [Condition B - Fixed L4] Latency: {dur_b:>8.1f}ms | Tools: {tel_b.total_tool_calls} | Tokens: {tel_b.total_tokens} | Success: {'✅' if success_b else '❌'}")

        # 3. Condition C: Adaptive Escalation Policy
        ctx_c = SessionContext(project_path=target_dir, workspace_name=f"exp05_{t_id}_condC", provider_id="ollama", model_name="qwen3:1.7b", capabilities=[Capability.CHAT, Capability.TOOLS])
        session_c = runtime.create_session(ctx_c)
        start_c = time.perf_counter()
        
        # Turn 1: Try L2
        resp_c = await session_c.send_message(build_prompt_l2(prompt))
        tel_c1 = session_c.session_telemetry
        used_tool_c1 = tel_c1.total_tool_calls > 0
        halluc_c1 = "not accessible" in str(resp_c).lower() or "not exist" in str(resp_c).lower()
        
        escalated = False
        if not used_tool_c1 or halluc_c1:
            # Evidence insufficient -> Escalate to L4
            escalated = True
            resp_c = await session_c.send_message(build_prompt_l4(prompt))
            
        dur_c = round((time.perf_counter() - start_c) * 1000.0, 2)
        tel_c_final = session_c.session_telemetry
        used_tool_c = tel_c_final.total_tool_calls > 0
        halluc_c = "not accessible" in str(resp_c).lower() or "not exist" in str(resp_c).lower()
        success_c = used_tool_c and not halluc_c
        
        res_c = {
            "condition": "Adaptive Escalation",
            "latency_ms": dur_c,
            "tool_calls": tel_c_final.total_tool_calls,
            "prompt_tokens": tel_c_final.total_prompt_tokens,
            "completion_tokens": tel_c_final.total_completion_tokens,
            "success": success_c,
            "escalated": escalated
        }
        print(f"   [Condition C - Adaptive ] Latency: {dur_c:>8.1f}ms | Tools: {tel_c_final.total_tool_calls} | Escalated: {escalated} | Success: {'✅' if success_c else '❌'}")
        
        task_results.append({
            "task_id": t_id,
            "complexity": c_lvl,
            "prompt": prompt,
            "fixed_l2": res_a,
            "fixed_l4": res_b,
            "adaptive": res_c
        })
        print("------------------------------------------------------------------------------------------\n")

    # Aggregated Summary
    avg_lat_a = round(sum(t["fixed_l2"]["latency_ms"] for t in task_results) / len(task_results), 2)
    avg_lat_b = round(sum(t["fixed_l4"]["latency_ms"] for t in task_results) / len(task_results), 2)
    avg_lat_c = round(sum(t["adaptive"]["latency_ms"] for t in task_results) / len(task_results), 2)
    
    total_tokens_a = sum(t["fixed_l2"]["prompt_tokens"] + t["fixed_l2"]["completion_tokens"] for t in task_results)
    total_tokens_b = sum(t["fixed_l4"]["prompt_tokens"] + t["fixed_l4"]["completion_tokens"] for t in task_results)
    total_tokens_c = sum(t["adaptive"]["prompt_tokens"] + t["adaptive"]["completion_tokens"] for t in task_results)
    
    success_rate_a = sum(1 for t in task_results if t["fixed_l2"]["success"]) / len(task_results) * 100.0
    success_rate_b = sum(1 for t in task_results if t["fixed_l4"]["success"]) / len(task_results) * 100.0
    success_rate_c = sum(1 for t in task_results if t["adaptive"]["success"]) / len(task_results) * 100.0

    exp_report = {
        "experiment_id": "EXP-005",
        "title": "Adaptive Escalation vs Fixed Scaffolding Flight",
        "evidence_class": "Adaptive Escalation Flight",
        "confidence_level": "Moderate",
        "timestamp": datetime.now().isoformat(),
        "brain_model": "qwen3:1.7b",
        "aggregated_summary": {
            "fixed_l2": {"success_rate_pct": success_rate_a, "avg_latency_ms": avg_lat_a, "total_tokens": total_tokens_a},
            "fixed_l4": {"success_rate_pct": success_rate_b, "avg_latency_ms": avg_lat_b, "total_tokens": total_tokens_b},
            "adaptive": {"success_rate_pct": success_rate_c, "avg_latency_ms": avg_lat_c, "total_tokens": total_tokens_c},
            "adaptive_savings_vs_fixed_l4": {
                "latency_reduction_pct": round(((avg_lat_b - avg_lat_c) / avg_lat_b) * 100.0, 2),
                "token_savings_pct": round(((total_tokens_b - total_tokens_c) / total_tokens_b) * 100.0, 2)
            }
        },
        "task_breakdown": task_results
    }
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_file = benchmarks_dir / f"exp_005_artifact_{timestamp_str}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(exp_report, f, indent=2)
        
    print("\n==========================================================================================")
    print("🏆 EXP-005 ADAPTIVE ESCALATION FLIGHT RESULTS")
    print("==========================================================================================")
    print(f"Condition A (Fixed L2) : Success Rate: {success_rate_a:>5.1f}% | Avg Latency: {avg_lat_a:>8.1f}ms | Tokens: {total_tokens_a}")
    print(f"Condition B (Fixed L4) : Success Rate: {success_rate_b:>5.1f}% | Avg Latency: {avg_lat_b:>8.1f}ms | Tokens: {total_tokens_b}")
    print(f"Condition C (Adaptive) : Success Rate: {success_rate_c:>5.1f}% | Avg Latency: {avg_lat_c:>8.1f}ms | Tokens: {total_tokens_c}")
    print("------------------------------------------------------------------------------------------")
    print(f"✓ Adaptive Latency Reduction vs Fixed L4 : {exp_report['aggregated_summary']['adaptive_savings_vs_fixed_l4']['latency_reduction_pct']}%")
    print(f"✓ Adaptive Token Savings vs Fixed L4     : {exp_report['aggregated_summary']['adaptive_savings_vs_fixed_l4']['token_savings_pct']}%")
    print("==========================================================================================")
    print(f"✅ EXP-005 Artifact saved to: {out_file}")
    print("==========================================================================================")
    
    await runtime.shutdown()

if __name__ == "__main__":
    asyncio.run(run_exp_005())
