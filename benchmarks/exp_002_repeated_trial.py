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

NUM_TRIALS_PER_VARIANT = 5  # Total N=10 trials

async def run_exp_002():
    target_dir = "/home/user/development/projects/lisa"
    benchmarks_dir = Path(__file__).resolve().parent
    
    print("==========================================================================================")
    print("🧪 BANDURA EXP-002: REPEATED CONTROLLED TRIAL (N=10 Runs)")
    print("Hypothesis: Cognitive scaffolding consistently enforces tool use and reduces latency.")
    print(f"Target Model  : qwen3:1.7b")
    print(f"Target Project: {target_dir}")
    print("==========================================================================================\n")
    
    runtime = LisaRuntime()
    await runtime.initialize()
    await runtime.register_provider(OllamaProvider())
    
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    
    task_prompt = "Inspect cli/main.py and explain how command options 'doctor' and 'compare' are handled."
    
    variant_a_runs = []
    variant_b_runs = []
    
    # 1. Run Variant A Trials (Baseline - Generic Instruction)
    print("------------------------------------------------------------------------------------------")
    print(f"🅰️  RUNNING VARIANT A (Baseline - N={NUM_TRIALS_PER_VARIANT})")
    print("------------------------------------------------------------------------------------------")
    for i in range(1, NUM_TRIALS_PER_VARIANT + 1):
        print(f"   [Run {i}/{NUM_TRIALS_PER_VARIANT}] Executing Baseline prompt...")
        ctx_a = SessionContext(
            project_path=target_dir,
            workspace_name=f"exp002_a_run{i}",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS]
        )
        session_a = runtime.create_session(ctx_a)
        
        start_t = time.perf_counter()
        resp_a = await session_a.send_message(task_prompt)
        dur_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        tel_a = session_a.session_telemetry
        tok_sec = round((tel_a.total_completion_tokens / (dur_ms / 1000.0)), 2) if dur_ms > 0 else 0.0
        
        record = {
            "trial": i,
            "latency_ms": dur_ms,
            "tok_sec": tok_sec,
            "tool_calls": tel_a.total_tool_calls,
            "prompt_tokens": tel_a.total_prompt_tokens,
            "completion_tokens": tel_a.total_completion_tokens,
            "hallucination_detected": "not accessible" in str(resp_a).lower() or "not exist" in str(resp_a).lower()
        }
        variant_a_runs.append(record)
        print(f"       -> Latency: {dur_ms}ms | Tok/sec: {tok_sec} | Tool Calls: {tel_a.total_tool_calls} | Hallucinated: {record['hallucination_detected']}")

    # 2. Run Variant B Trials (Scaffolded - L.I.S.A. Teacher Profile)
    print("\n------------------------------------------------------------------------------------------")
    print(f"🅱️  RUNNING VARIANT B (Scaffolded - N={NUM_TRIALS_PER_VARIANT})")
    print("------------------------------------------------------------------------------------------")
    scaffold = ModelConstructionEngine.get_profile("qwen3:1.7b")
    scaffolded_prompt = f"{scaffold.scaffolded_system_prompt}\n\nUSER REQUEST:\n{task_prompt}"
    
    for i in range(1, NUM_TRIALS_PER_VARIANT + 1):
        print(f"   [Run {i}/{NUM_TRIALS_PER_VARIANT}] Executing Scaffolded prompt...")
        ctx_b = SessionContext(
            project_path=target_dir,
            workspace_name=f"exp002_b_run{i}",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS]
        )
        session_b = runtime.create_session(ctx_b)
        
        start_t = time.perf_counter()
        resp_b = await session_b.send_message(scaffolded_prompt)
        dur_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        tel_b = session_b.session_telemetry
        tok_sec = round((tel_b.total_completion_tokens / (dur_ms / 1000.0)), 2) if dur_ms > 0 else 0.0
        
        record = {
            "trial": i,
            "latency_ms": dur_ms,
            "tok_sec": tok_sec,
            "tool_calls": tel_b.total_tool_calls,
            "prompt_tokens": tel_b.total_prompt_tokens,
            "completion_tokens": tel_b.total_completion_tokens,
            "hallucination_detected": "not accessible" in str(resp_b).lower() or "not exist" in str(resp_b).lower()
        }
        variant_b_runs.append(record)
        print(f"       -> Latency: {dur_ms}ms | Tok/sec: {tok_sec} | Tool Calls: {tel_b.total_tool_calls} | Hallucinated: {record['hallucination_detected']}")

    # Calculate Aggregated Statistics
    avg_lat_a = round(sum(r["latency_ms"] for r in variant_a_runs) / len(variant_a_runs), 2)
    avg_lat_b = round(sum(r["latency_ms"] for r in variant_b_runs) / len(variant_b_runs), 2)
    
    avg_tok_sec_a = round(sum(r["tok_sec"] for r in variant_a_runs) / len(variant_a_runs), 2)
    avg_tok_sec_b = round(sum(r["tok_sec"] for r in variant_b_runs) / len(variant_b_runs), 2)
    
    tool_success_a = sum(1 for r in variant_a_runs if r["tool_calls"] > 0) / len(variant_a_runs) * 100.0
    tool_success_b = sum(1 for r in variant_b_runs if r["tool_calls"] > 0) / len(variant_b_runs) * 100.0
    
    exp_report = {
        "experiment_id": "EXP-002",
        "title": "Repeated Controlled Trial of Model Cognitive Scaffolding",
        "evidence_class": "Repeated Controlled Trial",
        "confidence_level": "Moderate",
        "timestamp": datetime.now().isoformat(),
        "brain_model": "qwen3:1.7b",
        "sample_size": f"N={len(variant_a_runs) + len(variant_b_runs)}",
        "pre_defined_success_criteria": {
            "variant_b_tool_call_rate_target": ">= 80%",
            "variant_b_hallucination_rate_target": "< 20%"
        },
        "aggregated_metrics": {
            "variant_a_baseline": {
                "avg_latency_ms": avg_lat_a,
                "avg_tok_sec": avg_tok_sec_a,
                "tool_call_rate_pct": tool_success_a
            },
            "variant_b_scaffolded": {
                "avg_latency_ms": avg_lat_b,
                "avg_tok_sec": avg_tok_sec_b,
                "tool_call_rate_pct": tool_success_b
            },
            "performance_deltas": {
                "latency_reduction_pct": round(((avg_lat_a - avg_lat_b) / avg_lat_a) * 100.0, 2),
                "throughput_boost_pct": round(((avg_tok_sec_b - avg_tok_sec_a) / avg_tok_sec_a) * 100.0, 2)
            }
        },
        "raw_trials": {
            "variant_a": variant_a_runs,
            "variant_b": variant_b_runs
        }
    }
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_file = benchmarks_dir / f"exp_002_artifact_{timestamp_str}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(exp_report, f, indent=2)
        
    print("\n==========================================================================================")
    print("📊 EXP-002 SUMMARY METRICS")
    print(f"   Variant A (Baseline)  : Avg Latency: {avg_lat_a} ms | Tok/sec: {avg_tok_sec_a} | Tool Call Rate: {tool_success_a:.1f}%")
    print(f"   Variant B (Scaffolded): Avg Latency: {avg_lat_b} ms | Tok/sec: {avg_tok_sec_b} | Tool Call Rate: {tool_success_b:.1f}%")
    print(f"   ✓ Latency Delta       : {exp_report['aggregated_metrics']['performance_deltas']['latency_reduction_pct']}%")
    print(f"   ✓ Throughput Delta    : +{exp_report['aggregated_metrics']['performance_deltas']['throughput_boost_pct']}%")
    print(f"✅ EXP-002 Artifact saved to: {out_file}")
    print("==========================================================================================")
    
    await runtime.shutdown()

if __name__ == "__main__":
    asyncio.run(run_exp_002())
