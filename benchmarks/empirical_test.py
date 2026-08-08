import sys
import os
import time
import asyncio
from pathlib import Path

# Add project root and parent to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.bootstrap.engine import BootstrapEngine
from lisa.core.kernel import LisaRuntime
from lisa.providers.ollama.provider import OllamaProvider
from lisa.providers.openai.provider import OpenAIProvider
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import WriteFileTool, ListDirectoryTool
from lisa.core.context import SessionContext, Capability
from lisa.engine.auto_selector import AutoSelector
from lisa.providers.selector import ProviderSelector

async def run_empirical_tests():
    target_dir = "/home/user/development/projects/extro_pos"
    
    print("==========================================================================================")
    print("🧪 L.I.S.A. EMPIRICAL TEST FLIGHT — ADAPTIVE EXECUTION PLANNING & ROUTING")
    print(f"Target Project: {target_dir}")
    print("==========================================================================================\n")
    
    runtime = LisaRuntime()
    await runtime.initialize()
    await runtime.register_provider(OllamaProvider())
    await runtime.register_provider(OpenAIProvider())
    
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    
    ctx = SessionContext(
        project_path=target_dir,
        workspace_name="empirical_test",
        provider_id="ollama",
        model_name="qwen3:1.7b",
        capabilities=[Capability.CHAT, Capability.TOOLS]
    )
    session = runtime.create_session(ctx)
    
    p_selector = ProviderSelector(runtime.provider_registry)
    auto_selector = AutoSelector(p_selector)
    
    test_prompts = [
        ("🟢 Test 1 (Trivial)", "Read BOOT.md and tell me the active milestone."),
        ("🟡 Test 2 (Medium)", "Inspect the ExtroPOS repository and identify where inventory transactions are implemented. Do not modify anything."),
        ("🔴 Test 3 (Complex)", "Analyze the current ExtroPOS inventory architecture and propose a safe offline-first synchronization strategy. Do not modify code.")
    ]
    
    for label, prompt in test_prompts:
        print(f"------------------------------------------------------------------------------------------")
        print(f"📌 {label}")
        print(f"User Prompt: \"{prompt}\"")
        
        plan = await auto_selector.plan_execution(prompt)
        
        print("\n🧠 AUTO EXECUTION PLAN")
        print("────────────────────────────────────")
        print(f"Complexity       : {plan.complexity_level}")
        print(f"Provider         : {plan.provider_id}")
        print(f"Model            : {plan.model_name}")
        print(f"Estimated Cost   : {plan.hardware_cost_tier}")
        print(f"Estimated Latency: {plan.estimated_latency_tier}")
        print(f"Hardware Load    : {plan.hardware_load_tier}")
        print(f"Reason           : {plan.reason}")
        print("────────────────────────────────────")
        
        start_t = time.perf_counter()
        response = await session.send_message(prompt)
        dur_ms = (time.perf_counter() - start_t) * 1000.0
        
        tel = session.session_telemetry
        print(f"\n⏱️  Execution Latency: {dur_ms:.2f} ms")
        print(f"📊 Response Excerpt (First 200 chars):")
        excerpt = str(response)[:200].replace("\n", " ")
        print(f"   \"{excerpt}...\"")
        print(f"------------------------------------------------------------------------------------------\n")
        
    await runtime.shutdown()

if __name__ == "__main__":
    asyncio.run(run_empirical_tests())
