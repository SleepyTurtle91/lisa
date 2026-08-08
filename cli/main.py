#!/usr/bin/env python3
import sys
import os
import time
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add project root and parent to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.core.kernel import LisaRuntime
from lisa.bootstrap.engine import BootstrapEngine
from lisa.providers.ollama.provider import OllamaProvider
from lisa.providers.openai.provider import OpenAIProvider
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import WriteFileTool, ListDirectoryTool
from lisa.tools.compiler import ToolCompiler
from lisa.core.context import SessionContext, Capability
from lisa.cli.repl import start_repl

def print_help():
    print("🤖 L.I.S.A. AI Engineering Operating System CLI (v1.1.0)")
    print("===================================================")
    print("Usage:")
    print("  lisa [command|path] [options]")
    print("\nCommands:")
    print("  <path>                 Run interactive AI engineering session on target project directory.")
    print("  doctor [path]          Run platform health diagnostics, architecture & performance gate checks.")
    print("  compare [path]         Analyze historical benchmark flight logs and throughput performance trends.")
    print("  --help, -h             Display this CLI usage help menu.")
    print("\nExamples:")
    print("  lisa /home/user/development/projects/extro_pos")
    print("  lisa doctor /home/user/development/projects/extro_pos")
    print("  lisa compare")
    print("  python3 cli/benchmark.py /home/user/development/projects/extro_pos qwen3:1.7b")
    print("===================================================")

async def run_doctor(target_dir: str):
    print("🩺 L.I.S.A. Platform Diagnostics & Health Doctor (v1.1.0)")
    print("===================================================")
    
    start_time = time.perf_counter()
    boot = BootstrapEngine.discover(target_dir)
    
    runtime = LisaRuntime()
    await runtime.initialize()
    
    ollama = await runtime.register_provider(OllamaProvider())
    openai = await runtime.register_provider(OpenAIProvider())
    
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    
    boot_latency_ms = (time.perf_counter() - start_time) * 1000.0

    # Cache compilation test
    compile_start = time.perf_counter()
    ToolCompiler.clear_cache()
    for t in runtime.tool_registry.list_tools():
        ToolCompiler.compile_schema(t, "ollama")
    compile_latency_ms = (time.perf_counter() - compile_start) * 1000.0

    # Grade evaluation
    p_cfg = boot.project
    s_cfg = boot.system
    arch_grade = "A+" if (p_cfg.boot_md_present and p_cfg.agents_md_present) else ("A" if p_cfg.agents_md_present else "B")
    perf_grade = "A+" if (boot_latency_ms < 15.0 and compile_latency_ms < 2.0) else "B"

    # Inspect historical benchmark artifacts
    bench_dir = Path(__file__).resolve().parent.parent / "benchmarks"
    history_count = len(list(bench_dir.glob("*.json"))) if bench_dir.exists() else 0

    print(f"🖥️ System Environment  : {s_cfg.os_name} ({s_cfg.architecture}, Python {s_cfg.python_version}, Git: {s_cfg.git_present})")
    print(f"📁 Target Project Path: {p_cfg.project_name} ({p_cfg.project_path})")
    print("---------------------------------------------------")
    print(f"🏆 Architecture Grade  : {arch_grade} (BOOT: {p_cfg.boot_md_present}, AGENTS: {p_cfg.agents_md_present})")
    print(f"⚡ Performance Grade   : {perf_grade} (Boot Gate <15ms, Compile Gate <2ms)")
    print("---------------------------------------------------")
    print(f"🚀 Framework Boot Time : {boot_latency_ms:.2f} ms")
    print(f"🛠️  Schema Compile Time: {compile_latency_ms:.2f} ms")
    print(f"🔌 Registered Providers: {len(runtime.provider_registry.list_providers())} (Ollama: {ollama.healthy}, OpenAI: {openai.healthy})")
    print(f"🛠️  Discovered Capabilities: {', '.join(p_cfg.discovered_capabilities)}")
    print(f"💾 Historical Benchmarks: {history_count} run artifacts recorded in lisa/benchmarks/")
    print("===================================================")

    await runtime.shutdown()

async def run_benchmark_compare(target_dir: str):
    bench_dir = Path(__file__).resolve().parent.parent / "benchmarks"
    if not bench_dir.exists():
        print("⚠️ No benchmark history artifacts found in lisa/benchmarks/")
        return

    artifacts = sorted(list(bench_dir.glob("*.json")))
    if not artifacts:
        print("⚠️ No benchmark history artifacts found in lisa/benchmarks/")
        return

    print("📊 L.I.S.A. Historical Benchmark Trend Analysis")
    print("=========================================================================================================")
    print(f"{'Timestamp':<20} | {'Model':<15} | {'Overhead (ms)':<15} | {'Inference (ms)':<15} | {'Tokens':<10} | {'Tok/Sec':<10} | {'Cache Hit %':<10}")
    print("---------------------------------------------------------------------------------------------------------")
    
    for art in artifacts:
        try:
            with open(art, "r", encoding="utf-8") as f:
                data = json.load(f)
                ts = datetime.fromisoformat(data["timestamp"]).strftime("%Y-%m-%d %H:%M")
                model = data["model_name"]
                overhead = round(data["boot_latency_ms"] + data["tool_execution_ms"], 2)
                inf_ms = data["provider_inference_ms"]
                tokens = data["total_tokens"]
                tok_sec = data.get("generation_throughput_tok_sec", 0.0)
                hit_pct = data.get("cache_hit_rate_pct", 0.0)
                print(f"{ts:<20} | {model:<15} | {overhead:<15} | {inf_ms:<15} | {tokens:<10} | {tok_sec:<10} | {hit_pct:<10}")
        except Exception as e:
            continue
    print("=========================================================================================================")

async def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print_help()
        return
    elif len(sys.argv) > 1 and sys.argv[1] == "doctor":
        target = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
        await run_doctor(target)
        return
    elif len(sys.argv) > 1 and sys.argv[1] == "compare":
        target = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
        await run_benchmark_compare(target)
        return

    target_dir = sys.argv[1] if len(sys.argv) > 1 else None
    await start_repl(target_dir)

def cli_entrypoint():
    asyncio.run(main())

if __name__ == "__main__":
    cli_entrypoint()
