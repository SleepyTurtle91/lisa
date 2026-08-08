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

TRIALS_PER_LEVEL = 3

SCAFFOLDING_LEVELS = [
    {
        "level": 0,
        "name": "Level 0 (None)",
        "prompt_builder": lambda task: task
    },
    {
        "level": 1,
        "name": "Level 1 (Basic Role)",
        "prompt_builder": lambda task: f"You are L.I.S.A., an AI engineering assistant.\n\nTask:\n{task}"
    },
    {
        "level": 2,
        "name": "Level 2 (Explicit Tool Discipline)",
        "prompt_builder": lambda task: f"You are L.I.S.A., an AI engineering assistant.\nRule: Always inspect files using the read_file tool before answering. Do not guess.\n\nTask:\n{task}"
    },
    {
        "level": 3,
        "name": "Level 3 (Tool + Evidence Verification)",
        "prompt_builder": lambda task: f"You are L.I.S.A., an AI engineering assistant.\nRules:\n1. Always inspect files using the read_file tool before answering.\n2. Base your explanation strictly on actual file evidence.\n3. Verify your findings before concluding.\n\nTask:\n{task}"
    },
    {
        "level": 4,
        "name": "Level 4 (Full Construction Profile)",
        "prompt_builder": lambda task: f"{ModelConstructionEngine.get_profile('qwen3:1.7b').scaffolded_system_prompt}\n\nUSER REQUEST:\n{task}"
    }
]

async def run_exp_003():
    target_dir = "/home/user/development/projects/lisa"
    benchmarks_dir = Path(__file__).resolve().parent
    
    print("==========================================================================================")
    print("🧪 BANDURA EXP-003: MINIMUM EFFECTIVE SCAFFOLDING DOSE-RESPONSE EXPERIMENT")
    print("Pre-defined Target Reliability: >= 90% Tool Adherence & 0% Hallucination")
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
    
    level_results = []
    
    for lvl_info in SCAFFOLDING_LEVELS:
        lvl = lvl_info["level"]
        name = lvl_info["name"]
        builder = lvl_info["prompt_builder"]
        
        print("------------------------------------------------------------------------------------------")
        print(f"📌 TESTING SCAFFOLDING {name} (N={TRIALS_PER_LEVEL})")
        print("------------------------------------------------------------------------------------------")
        
        runs = []
        for i in range(1, TRIALS_PER_LEVEL + 1):
            ctx = SessionContext(
                project_path=target_dir,
                workspace_name=f"exp003_l{lvl}_run{i}",
                provider_id="ollama",
                model_name="qwen3:1.7b",
                capabilities=[Capability.CHAT, Capability.TOOLS]
            )
            session = runtime.create_session(ctx)
            
            prompt_to_send = builder(task_prompt)
            start_t = time.perf_counter()
            resp = await session.send_message(prompt_to_send)
            dur_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            tel = session.session_telemetry
            tok_sec = round((tel.total_completion_tokens / (dur_ms / 1000.0)), 2) if dur_ms > 0 else 0.0
            
            is_hallucinated = "not accessible" in str(resp).lower() or "not exist" in str(resp).lower()
            tool_used = tel.total_tool_calls > 0
            
            rec = {
                "trial": i,
                "latency_ms": dur_ms,
                "tok_sec": tok_sec,
                "tool_calls": tel.total_tool_calls,
                "tool_used": tool_used,
                "hallucination": is_hallucinated,
                "prompt_tokens": tel.total_prompt_tokens,
                "completion_tokens": tel.total_completion_tokens
            }
            runs.append(rec)
            print(f"   [Trial {i}/{TRIALS_PER_LEVEL}] Latency: {dur_ms}ms | Tok/s: {tok_sec} | Tool Used: {tool_used} | Hallucinated: {is_hallucinated}")
            
        avg_lat = round(sum(r["latency_ms"] for r in runs) / len(runs), 2)
        avg_tok_sec = round(sum(r["tok_sec"] for r in runs) / len(runs), 2)
        tool_adherence_pct = round(sum(1 for r in runs if r["tool_used"]) / len(runs) * 100.0, 1)
        hallucination_pct = round(sum(1 for r in runs if r["hallucination"]) / len(runs) * 100.0, 1)
        
        level_summary = {
            "level": lvl,
            "name": name,
            "avg_latency_ms": avg_lat,
            "avg_tok_sec": avg_tok_sec,
            "tool_adherence_pct": tool_adherence_pct,
            "hallucination_pct": hallucination_pct,
            "target_met": tool_adherence_pct >= 90.0 and hallucination_pct == 0.0,
            "runs": runs
        }
        level_results.append(level_summary)
        print(f"   📊 LEVEL {lvl} SUMMARY: Tool Adherence: {tool_adherence_pct}% | Hallucination: {hallucination_pct}% | Avg Latency: {avg_lat}ms | Target Met: {level_summary['target_met']}")
        print("------------------------------------------------------------------------------------------\n")

    # Find Minimum Effective Scaffolding Level
    min_effective = next((l for l in level_results if l["target_met"]), None)
    min_effective_name = min_effective["name"] if min_effective else "None met criteria"

    exp_report = {
        "experiment_id": "EXP-003",
        "title": "Minimum Effective Scaffolding Dose-Response Experiment",
        "evidence_class": "Dose-Response Experiment",
        "confidence_level": "Moderate",
        "timestamp": datetime.now().isoformat(),
        "brain_model": "qwen3:1.7b",
        "target_reliability_criterion": "Tool Adherence >= 90% and Hallucination == 0%",
        "minimum_effective_level": min_effective_name,
        "dose_response_curve": [
            {
                "level": l["level"],
                "name": l["name"],
                "tool_adherence_pct": l["tool_adherence_pct"],
                "hallucination_pct": l["hallucination_pct"],
                "avg_latency_ms": l["avg_latency_ms"],
                "avg_tok_sec": l["avg_tok_sec"],
                "target_met": l["target_met"]
            }
            for l in level_results
        ],
        "full_results": level_results
    }
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_file = benchmarks_dir / f"exp_003_artifact_{timestamp_str}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(exp_report, f, indent=2)
        
    print("\n==========================================================================================")
    print("🏆 EXP-003 DOSE-RESPONSE EXPERIMENT RESULTS")
    print(f"   Target Reliability Criterion : >= 90% Tool Adherence & 0% Hallucination")
    print(f"   🎯 Minimum Effective Level   : {min_effective_name}")
    print("──────────────────────────────────────────────────────────────────────────────────────────")
    for l in level_results:
        status_str = "✅ PASS" if l["target_met"] else "❌ FAIL"
        print(f"   L{l['level']} ({l['name']:<35}): Adherence: {l['tool_adherence_pct']:>5.1f}% | Latency: {l['avg_latency_ms']:>8.1f}ms | {status_str}")
    print("==========================================================================================")
    print(f"✅ EXP-003 Artifact saved to: {out_file}")
    print("==========================================================================================")
    
    await runtime.shutdown()

if __name__ == "__main__":
    asyncio.run(run_exp_003())
