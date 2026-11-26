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
from lisa.projects import ProjectExecutor, ProjectOperation, ProjectRequest
from lisa.projects.registry import ProjectRegistry
from lisa.projects.profile_executor import ProjectProfileExecutor
from lisa.projects.profile_request import ProjectProfileRequest
from lisa.projects.capability_discovery import CapabilityDiscoveryExecutor
from lisa.projects.capability_request import CapabilityDiscoveryRequest
from lisa.projects.compatibility_executor import ProjectCompatibilityExecutor
from lisa.projects.compatibility_request import ProjectCompatibilityRequest
from lisa.projects.adaptation_planner import ProjectAdaptationPlanner
from lisa.projects.adaptation_request import ProjectAdaptationRequest

PROJECT_REGISTRY_PATH = Path.home() / ".lisa" / "projects.json"


def _project_executor():
    return ProjectExecutor(registry=ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH))


def run_project_command(args):
    if not args or args[0] in ("help", "--help", "-h"):
        print("Usage: lisa project <list|add PATH|use ID|NAME|remove ID>")
        return
    executor = _project_executor()
    action = args[0].lower()
    if action in ("list", "ls"):
        result = executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
        if not result.manifests:
            print("No registered projects. Add one with: lisa project add <path>")
            return
        print("Registered L.I.S.A. projects:")
        for item in result.manifests:
            active = "*" if result.context and result.context.project_id == item.project_id else " "
            tech = ", ".join(item.capabilities) or "unknown stack"
            print(f" {active} {item.name}  [{item.project_id}]  {tech}")
            print(f"    {item.root_path}")
        return
    if action == "plan" and len(args) >= 4:
        listing = executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
        source_matches = [p for p in listing.manifests if p.project_id == args[1] or p.name.casefold() == args[1].casefold()]
        target_matches = [p for p in listing.manifests if p.project_id == args[2] or p.name.casefold() == args[2].casefold()]
        if len(source_matches) != 1 or len(target_matches) != 1:
            print("Source or target not found/ambiguous. Use 'lisa project list' to see project IDs.")
            return
        result = ProjectAdaptationPlanner(
            registry=ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH)
        ).execute(ProjectAdaptationRequest(
            source_project_id=source_matches[0].project_id,
            target_project_id=target_matches[0].project_id,
            capability_query=" ".join(args[3:]),
        ))
        if not result.success:
            print(f"Adaptation planning failed: {result.error}")
            return
        plan = result.plan
        print(f"Adaptation plan {plan.plan_id}: {plan.source_project_name} -> {plan.target_project_name}")
        print(f"Status: {plan.status.value}")
        print(plan.summary)
        for blocker in plan.blockers:
            print(f"Blocker: {blocker}")
        for constraint in plan.target_constraints:
            print(f"Preserve [{constraint.relative_path}]: {constraint.excerpt}")
        for step in plan.steps:
            print(f"{step.order}. {step.title} — {step.description}")
        print(f"Authorization required: {plan.authorization_required}")
        print(f"Execution authorized: {plan.execution_authorized}")
        print("This is a review-only plan. No code was copied, modified, or executed.")
        return
    if action in ("compare", "compatibility") and len(args) >= 3:
        listing = executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
        source_matches = [p for p in listing.manifests if p.project_id == args[1] or p.name.casefold() == args[1].casefold()]
        target_matches = [p for p in listing.manifests if p.project_id == args[2] or p.name.casefold() == args[2].casefold()]
        if len(source_matches) != 1 or len(target_matches) != 1:
            print("Source or target not found/ambiguous. Use 'lisa project list' to see project IDs.")
            return
        query = " ".join(args[3:]).strip() or None
        result = ProjectCompatibilityExecutor(
            registry=ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH)
        ).execute(ProjectCompatibilityRequest(
            source_project_id=source_matches[0].project_id,
            target_project_id=target_matches[0].project_id,
            capability_query=query,
        ))
        if not result.success:
            print(f"Compatibility analysis failed: {result.error}")
            return
        report = result.report
        print(f"Compatibility triage: {report.source_project_name} -> {report.target_project_name}")
        print(f"Status: {report.status.value}")
        print(f"Shared technologies: {', '.join(report.shared_technologies) or '(none)'}")
        if report.capability_query:
            print(f"Capability query: {report.capability_query} (found: {report.source_capability_found})")
            print(f"Matched terms: {', '.join(report.matched_terms) or '(none)'}")
        for flag in report.risk_flags:
            print(f"Risk: {flag}")
        for constraint in report.constraints:
            print(f"Constraint [{constraint.project_role}] {constraint.relative_path}: {constraint.excerpt}")
        print("No code was transferred or modified. Review the evidence before planning an adaptation.")
        return
    if action in ("find", "search") and len(args) >= 2:
        query = " ".join(args[1:])
        discovery = CapabilityDiscoveryExecutor(
            registry=ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH)
        ).execute(CapabilityDiscoveryRequest(query=query))
        if not discovery.success:
            print(f"Capability search failed: {discovery.error}")
            return
        if not discovery.matches:
            print(f"No project evidence matched: {query}")
            return
        print(f"Capability candidates for: {query}")
        for match in discovery.matches:
            print(f"  {match.project_name} [{match.project_id}] — {match.score:.0%} match")
            print(f"    Terms: {', '.join(match.matched_terms)}")
            for evidence in match.evidence:
                print(f"    Evidence: {evidence.relative_path} [{evidence.evidence_kind}; sha256:{evidence.sha256[:12]}]")
            for source_path in match.source_paths:
                print(f"    Source path: {source_path}")
        return
    if action in ("inspect", "profile") and len(args) >= 2:
        identifier = " ".join(args[1:])
        listing = executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
        matches = [p for p in listing.manifests if p.project_id == identifier or p.name.casefold() == identifier.casefold()]
        if len(matches) != 1:
            print("Project not found or name is ambiguous. Use 'lisa project list' to see project IDs.")
            return
        profile_result = ProjectProfileExecutor(
            registry=ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH)
        ).execute(ProjectProfileRequest(project_id=matches[0].project_id))
        if not profile_result.success:
            print(f"Project inspection failed: {profile_result.error}")
            return
        profile = profile_result.profile
        print(f"Project: {profile.name} [{profile.project_id}]")
        print(f"Technologies: {', '.join(profile.technologies) or 'unknown'}")
        print(f"Top-level directories: {', '.join(profile.top_level_directories) or '(none)'}")
        print(f"Source files inventoried: {profile.source_file_count}")
        print("Evidence files:")
        for item in profile.evidence:
            print(f"  - {item.relative_path} [{item.evidence_kind}; sha256:{item.sha256[:12]}]")
        return
    if action == "add" and len(args) >= 2:
        result = executor.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=" ".join(args[1:])
        ))
        if not result.success:
            print(f"Project registration failed: {result.error}")
        else:
            print(f"Registered {result.manifest.name} [{result.manifest.project_id}]")
            print(f"Path: {result.manifest.root_path}")
        return
    if action in ("use", "activate") and len(args) >= 2:
        identifier = " ".join(args[1:])
        listing = executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
        matches = [p for p in listing.manifests if p.project_id == identifier or p.name.casefold() == identifier.casefold()]
        if len(matches) != 1:
            print("Project not found or name is ambiguous. Use 'lisa project list' to see project IDs.")
            return
        result = executor.execute(ProjectRequest(
            operation=ProjectOperation.ACTIVATE, project_id=matches[0].project_id
        ))
        if result.success:
            print(f"Active project set to {result.manifest.name}. Start with: lisa")
        else:
            print(f"Could not activate project: {result.error}")
        return
    if action in ("remove", "unregister") and len(args) >= 2:
        identifier = " ".join(args[1:])
        result = executor.execute(ProjectRequest(
            operation=ProjectOperation.UNREGISTER, project_id=identifier
        ))
        print("Project unregistered." if result.success else f"Could not unregister project: {result.error}")
        return
    print("Invalid project command. Use: lisa project help")

def print_help():
    print("🤖 L.I.S.A. AI Engineering Operating System CLI (v1.1.0)")
    print("===================================================")
    print("Usage:")
    print("  lisa [command|path] [options]")
    print("\nCommands:")
    print("  <path>                 Run interactive AI engineering session on target project directory.")
    print("  doctor [path]          Run platform health diagnostics, architecture & performance gate checks.")
    print("  compare [path]         Analyze historical benchmark flight logs and throughput performance trends.")
    print("  project list           List registered projects.")
    print("  project inspect <id|name> Build a read-only project profile.")
    print("  project find <terms>     Search project evidence for reusable capabilities.")
    print("  project compare <source-id> <target-id> [terms]  Triage reuse compatibility.")
    print("  project plan <source-id> <target-id> <terms>  Create a review-only adaptation plan.")
    print("  project add <path>     Register a project directory.")
    print("  project use <id|name>  Set the default active project.")
    print("  project remove <id>    Unregister a project.")
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
    elif len(sys.argv) > 1 and sys.argv[1] == "project":
        run_project_command(sys.argv[2:])
        return
    elif len(sys.argv) > 1 and sys.argv[1] == "projects":
        run_project_command(["list"])
        return
    elif len(sys.argv) > 1 and sys.argv[1] == "compare":
        target = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
        await run_benchmark_compare(target)
        return

    target_dir = sys.argv[1] if len(sys.argv) > 1 else None
    if target_dir is None:
        active = _project_executor().execute(
            ProjectRequest(operation=ProjectOperation.LIST)
        ).context
        if active is not None:
            target_dir = active.root_path
    await start_repl(target_dir)

def cli_entrypoint():
    asyncio.run(main())

if __name__ == "__main__":
    cli_entrypoint()
