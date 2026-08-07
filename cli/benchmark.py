#!/usr/bin/env python3
import sys
import os
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lisa.core.kernel import LisaRuntime
from lisa.bootstrap.engine import BootstrapEngine
from lisa.providers.ollama.provider import OllamaProvider
from lisa.providers.openai.provider import OpenAIProvider
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import WriteFileTool, ListDirectoryTool
from lisa.core.context import SessionContext, Capability

async def run_benchmark(target_dir: str, model_name: str = "qwen3:1.7b"):
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

    print("📊 L.I.S.A. Benchmark Flight Recorder Output")
    print("===================================================")
    print(f"Project Path      : {target_dir}")
    print(f"Provider          : ollama ({model_name})")
    print("---------------------------------------------------")
    print(f"Boot Latency      : {boot_latency_ms:.2f} ms")
    print(f"Provider Inference: {tel.provider_inference_ms:.2f} ms")
    print(f"Tool Execution    : {tel.tool_execution_ms:.2f} ms")
    print(f"Total Session Time: {exec_latency_ms:.2f} ms")
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

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen3:1.7b"
    asyncio.run(run_benchmark(target, model))
