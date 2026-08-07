#!/usr/bin/env python3
import sys
import os
import time
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lisa.core.kernel import LisaRuntime
from lisa.bootstrap.engine import BootstrapEngine
from lisa.providers.ollama.provider import OllamaProvider
from lisa.providers.openai.provider import OpenAIProvider
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import WriteFileTool, ListDirectoryTool
from lisa.core.context import SessionContext, Capability

async def run_benchmark(target_dir: str, model_name: str = "qwen3:1.7b", save_history: bool = True):
    boot_start = time.perf_counter()
    
    # 1. Discovery & Boot
    boot = BootstrapEngine.discover(target_dir)
    runtime = LisaRuntime()
    await runtime.initialize()
    await runtime.register_provider(OllamaProvider())
    await runtime.register_provider(OpenAIProvider())
    
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    
    boot_latency_ms = (time.perf_counter() - boot_start) * 1000.0

    # 2. Session Setup
    ctx = SessionContext(
        project_path=target_dir,
        workspace_name="benchmark_run",
        provider_id="ollama",
        model_name=model_name,
        capabilities=[Capability.CHAT, Capability.TOOLS]
    )
    session = runtime.create_session(ctx)
    prompt = f"Please read the file {target_dir}/BOOT.md and tell me what the active milestone is."

    # 3. Session Execution
    exec_start = time.perf_counter()
    response = await session.send_message(prompt)
    exec_latency_ms = (time.perf_counter() - exec_start) * 1000.0

    tel = session.session_telemetry
    await runtime.shutdown()

    hit_rate = (tel.cache_hits / (tel.cache_hits + tel.cache_misses) * 100.0) if (tel.cache_hits + tel.cache_misses) > 0 else 0.0
    throughput_tokens_per_sec = (tel.total_completion_tokens / (tel.provider_inference_ms / 1000.0)) if tel.provider_inference_ms > 0 else 0.0

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "project_path": target_dir,
        "provider_id": "ollama",
        "model_name": model_name,
        "boot_latency_ms": round(boot_latency_ms, 2),
        "provider_inference_ms": round(tel.provider_inference_ms, 2),
        "tool_execution_ms": round(tel.tool_execution_ms, 2),
        "total_session_time_ms": round(exec_latency_ms, 2),
        "generation_throughput_tok_sec": round(throughput_tokens_per_sec, 2),
        "turns": tel.total_turns,
        "tool_calls": tel.total_tool_calls,
        "prompt_tokens": tel.total_prompt_tokens,
        "completion_tokens": tel.total_completion_tokens,
        "total_tokens": tel.total_tokens,
        "cache_hits": tel.cache_hits,
        "cache_misses": tel.cache_misses,
        "cache_hit_rate_pct": round(hit_rate, 1)
    }

    print("📊 L.I.S.A. Benchmark Flight Recorder Output")
    print("===================================================")
    print(f"Project Path      : {target_dir}")
    print(f"Provider          : ollama ({model_name})")
    print("---------------------------------------------------")
    print(f"Boot Latency      : {report_data['boot_latency_ms']} ms")
    print(f"Provider Inference: {report_data['provider_inference_ms']} ms")
    print(f"Tool Execution    : {report_data['tool_execution_ms']} ms")
    print(f"Total Session Time: {report_data['total_session_time_ms']} ms")
    print(f"Throughput Rate   : {report_data['generation_throughput_tok_sec']} tok/sec")
    print("---------------------------------------------------")
    print(f"Reasoning Turns   : {tel.total_turns}")
    print(f"Tool Calls Made   : {tel.total_tool_calls}")
    print(f"Prompt Tokens     : {tel.total_prompt_tokens}")
    print(f"Completion Tokens : {tel.total_completion_tokens}")
    print(f"Total Tokens      : {tel.total_tokens}")
    print(f"Schema Cache Hits : {tel.cache_hits}")
    print(f"Schema Cache Miss : {tel.cache_misses}")
    print(f"Cache Hit Rate    : {hit_rate:.1f}%")
    print("===================================================")

    if save_history:
        bench_dir = Path(target_dir).parent / "lisa" / "benchmarks"
        os.makedirs(bench_dir, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{model_name.replace(':', '_')}.json"
        history_file = bench_dir / filename
        with open(history_file, "w", encoding="utf-8") as f:
            json.dumps(report_data, f, indent=2)
        print(f"💾 Benchmark artifact recorded to: {history_file}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen3:1.7b"
    asyncio.run(run_benchmark(target, model))
