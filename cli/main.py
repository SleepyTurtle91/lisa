#!/usr/bin/env python3
import sys
import os
import asyncio
import json
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

async def main():
    print("🤖 L.I.S.A. Engineering Operating System (v1.1.0)")
    print("===================================================")
    
    target_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    print(f"🔍 Discovering project at: {target_dir}")
    
    # 1. Bootstrap Discovery
    boot = BootstrapEngine.discover(target_dir)
    print(f"   ✓ BOOT.md present  : {boot.boot_md_present}")
    print(f"   ✓ AGENTS.md present: {boot.agents_md_present}")
    
    # 2. Kernel Initialization
    print("\n⚡ Initializing L.I.S.A. Kernel...")
    runtime = LisaRuntime()
    await runtime.initialize()
    print(f"   ✓ State: {runtime.state.name}")
    
    # 3. Register Providers
    print("\n🔌 Registering Providers...")
    ollama_manifest = await runtime.register_provider(OllamaProvider())
    print(f"   ✓ Registered: {ollama_manifest.id} (Capabilities: {[c.name for c in ollama_manifest.capabilities]})")
    
    openai_manifest = await runtime.register_provider(OpenAIProvider())
    print(f"   ✓ Registered: {openai_manifest.id} (Capabilities: {[c.name for c in openai_manifest.capabilities]})")
    
    # 4. Register Standard Tools
    print("\n🛠️  Registering Tools...")
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    for t in runtime.tool_registry.list_tools():
        print(f"   ✓ Tool: {t.name}")

    # 5. Check Health API
    print("\n🏥 System Health Snapshot:")
    print(json.dumps(runtime.health(), indent=2))

    # 6. Create Session
    print("\n💬 Creating Execution Session...")
    ctx = SessionContext(
        project_path=target_dir,
        workspace_name="cli_demo",
        provider_id="ollama",
        model_name="qwen3:1.7b",
        capabilities=[Capability.CHAT, Capability.TOOLS]
    )
    session = runtime.create_session(ctx)
    print(f"   ✓ Session ID: {session.session_id}")
    print(f"   ✓ Session State: {session.state.name}")

    # 7. Execute Interactive Prompt / Tool Invocation
    print("\n🚀 Executing Sample Prompt through Inference Engine + Tool Executor...")
    prompt = f"Please read the file {target_dir}/BOOT.md and tell me what the active milestone is."
    if not boot.boot_md_present and os.path.exists(os.path.join(target_dir, "AGENTS.md")):
        prompt = f"Please read the file {target_dir}/AGENTS.md and summarize the main objective."
    elif not boot.boot_md_present and not boot.agents_md_present:
        prompt = f"Please list the files in the directory {target_dir}."

    print(f"   ► User Prompt: {prompt}")
    response = await session.send_message(prompt)
    
    print("\n📥 Assistant Response:")
    print("---------------------------------------------------")
    print(response)
    print("---------------------------------------------------")

    # 8. Cumulative Session Telemetry & Schema Cache Stats Report
    tel = session.session_telemetry
    print("\n📊 Cumulative Session Telemetry Baseline:")
    print(f"   ✓ Total Latency    : {tel.total_latency_ms:.2f} ms")
    print(f"   ✓ Total Turns      : {tel.total_turns}")
    print(f"   ✓ Total Tool Calls : {tel.total_tool_calls}")
    print(f"   ✓ Prompt Tokens    : {tel.total_prompt_tokens}")
    print(f"   ✓ Completion Tokens: {tel.total_completion_tokens}")
    print(f"   ✓ Total Tokens     : {tel.total_tokens}")
    print(f"   ✓ Schema Cache Hits: {tel.cache_hits}")
    print(f"   ✓ Schema Cache Misses: {tel.cache_misses}")
    hit_rate = (tel.cache_hits / (tel.cache_hits + tel.cache_misses) * 100.0) if (tel.cache_hits + tel.cache_misses) > 0 else 0.0
    print(f"   ✓ Cache Hit Rate   : {hit_rate:.1f}%")

    # 9. Shutdown
    await runtime.shutdown()
    print(f"\n🛑 Kernel Shutdown complete. State: {runtime.state.name}")

if __name__ == "__main__":
    asyncio.run(main())
