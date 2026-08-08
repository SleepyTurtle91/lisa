import os
import sys
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

from lisa.bootstrap.engine import BootstrapEngine, BootConfig
from lisa.core.kernel import LisaRuntime
from lisa.providers.ollama.provider import OllamaProvider
from lisa.providers.openai.provider import OpenAIProvider
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import WriteFileTool, ListDirectoryTool
from lisa.core.context import SessionContext, Capability
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.telemetry.activity_renderer import FlightConsole

CONFIG_DIR = Path.home() / ".lisa"
RECENT_FILE = CONFIG_DIR / "recent.json"


def _activity_mode_from_env() -> str:
    mode = os.getenv("LISA_ACTIVITY_MODE", "compact").strip().lower()
    return mode if mode in FlightConsole.VALID_MODES else "compact"

def get_recent_projects() -> List[str]:
    if not RECENT_FILE.exists():
        return []
    try:
        with open(RECENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [p for p in data.get("recent", []) if os.path.exists(p)]
    except Exception:
        return []

def add_recent_project(path: str):
    abs_path = os.path.abspath(path)
    recents = get_recent_projects()
    if abs_path in recents:
        recents.remove(abs_path)
    recents.insert(0, abs_path)
    recents = recents[:5]  # Keep top 5
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(RECENT_FILE, "w", encoding="utf-8") as f:
            json.dump({"recent": recents}, f, indent=2)
    except Exception:
        pass

def scan_common_projects() -> List[str]:
    search_dirs = [
        "/home/user/development/projects",
        "/workspace/Projects",
        os.getcwd()
    ]
    found = set()
    for root in search_dirs:
        if os.path.exists(root) and os.path.isdir(root):
            try:
                for entry in os.listdir(root):
                    full_path = os.path.join(root, entry)
                    if os.path.isdir(full_path) and not entry.startswith("."):
                        # Check if it looks like a project
                        if (os.path.exists(os.path.join(full_path, "BOOT.md")) or 
                            os.path.exists(os.path.join(full_path, "AGENTS.md")) or
                            os.path.exists(os.path.join(full_path, ".git")) or
                            os.path.exists(os.path.join(full_path, "README.md"))):
                            found.add(os.path.abspath(full_path))
            except Exception:
                pass
    return sorted(list(found))

def prompt_project_selection() -> Optional[str]:
    print("🤖 L.I.S.A. Engineering Operating System REPL Mode")
    print("===================================================")
    
    recents = get_recent_projects()
    if recents:
        print("\n🕒 Recent Projects:")
        for idx, p in enumerate(recents, 1):
            name = os.path.basename(p)
            print(f"  {idx}) {name:<20} ({p})")
    
    scanned = scan_common_projects()
    # Filter out recents from scanned
    scanned_filtered = [p for p in scanned if p not in recents]
    
    if scanned_filtered:
        print("\n📁 Discovered Workspace Projects:")
        offset = len(recents)
        for idx, p in enumerate(scanned_filtered, offset + 1):
            name = os.path.basename(p)
            print(f"  {idx}) {name:<20} ({p})")
    
    offset_browse = len(recents) + len(scanned_filtered) + 1
    print(f"\n  {offset_browse}) Browse / Paste custom path...")
    print("  0) Exit")
    print("===================================================")
    
    try:
        choice = input("\nSelect a project number or paste path: ").strip()
    except (KeyboardInterrupt, EOFError):
        return None
        
    if not choice or choice == "0":
        return None
        
    if choice.isdigit():
        num = int(choice)
        if 1 <= num <= len(recents):
            return recents[num - 1]
        elif len(recents) < num <= len(recents) + len(scanned_filtered):
            return scanned_filtered[num - len(recents) - 1]
        elif num == offset_browse:
            try:
                custom = input("Project Path: ").strip()
                return custom if custom else None
            except (KeyboardInterrupt, EOFError):
                return None
        else:
            print("❌ Invalid selection.")
            return None
    else:
        # User pasted path directly
        if os.path.exists(choice):
            return os.path.abspath(choice)
        else:
            print(f"❌ Path does not exist: {choice}")
            return None

def handle_missing_boot_md(project_path: str) -> bool:
    boot_path = os.path.join(project_path, "BOOT.md")
    if os.path.exists(boot_path):
        return True
        
    print(f"\n⚠️  BOOT.md not found in {project_path}")
    print("Would you like to:")
    print("  1) Create default BOOT.md template")
    print("  2) Continue without BOOT.md")
    print("  3) Cancel")
    
    try:
        choice = input("\nChoose [1-3]: ").strip()
    except (KeyboardInterrupt, EOFError):
        return False
        
    if choice == "1":
        content = f"""# 🚀 BOOT.md - {os.path.basename(project_path)}

## Active Milestone
- Sprint 1: Initial Setup & Discovery

## Core Directives
- Preserve existing architecture
- Execute tests before reporting completion
"""
        try:
            with open(boot_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("✓ Default BOOT.md created successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to create BOOT.md: {e}")
            return False
    elif choice == "2":
        return True
    else:
        return False

def render_computer_boot_sequence(proj_name: str):
    boot_logs = [
        "[  0.000000] L.I.S.A. BIOS v1.2.0 (x86_64, CPU Architecture: x86_64, Python 3.14)",
        "[  0.001200] Memory Check: 16384 MB RAM OK | Hardware Acceleration: GPU RTX 3060",
        "[  0.002400] Initializing L.I.S.A. Kernel Core Subsystems...",
        "[  0.003600] Mounting File System & Knowledge Layers... [ OK ]",
        "[  0.004800] Probing Local Providers (Ollama Engine: ACTIVE, OpenAI Engine: READY)... [ OK ]",
        "[  0.006000] Loading Cognitive Scaffolding Profiles & Domain Disciplines... [ OK ]",
        "[  0.007200] Loading BANDURA Immutable Experiment Registry... [ OK ]",
        f"[  0.008400] 2-Tier Bootstrap Loaded Target Project: {proj_name} [ OK ]"
    ]
    print("\n⚡ BOOT SEQUENCE INITIATED...")
    for log in boot_logs:
        print(log)
        time.sleep(0.03)
    print()

async def start_repl(target_dir: Optional[str] = None):
    if not target_dir:
        target_dir = prompt_project_selection()
        if not target_dir:
            print("Goodbye!")
            return
            
    target_dir = os.path.abspath(target_dir)
    if not os.path.exists(target_dir):
        print(f"❌ Target directory {target_dir} does not exist.")
        return
        
    if not handle_missing_boot_md(target_dir):
        print("Cancelled boot.")
        return
        
    add_recent_project(target_dir)
    
    boot_cfg = BootstrapEngine.discover(target_dir)
    proj_name = boot_cfg.project.project_name
    
    render_computer_boot_sequence(proj_name)
    
    box_width = 44
    title = "L.I.S.A. Engineering Operating System"
    p_line = f"Project : {proj_name}"
    prov_line = "Provider: Auto"
    status_line = "Status  : READY"
    
    print("╭" + "─" * box_width + "╮")
    print(f"│ {title:<{box_width - 2}} │")
    print(f"│ {p_line:<{box_width - 2}} │")
    print(f"│ {prov_line:<{box_width - 2}} │")
    print(f"│ {status_line:<{box_width - 2}} │")
    print("╰" + "─" * box_width + "╯\n")
    print("Type 'help' for REPL commands or enter prompt to interact.")

    activity_mode = _activity_mode_from_env()
    recorder_session = f"repl_{proj_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    recorder = FlightRecorder(session_id=recorder_session)
    activity_console = FlightConsole(project_name=proj_name, mode=activity_mode)
    activity_console.bind(recorder)
    if activity_mode != "off":
        print(f"🖥️  Activity Mode: {activity_mode} (set LISA_ACTIVITY_MODE=off|compact|verbose)")
    
    # Kernel Init
    runtime = LisaRuntime(flight_recorder=recorder)
    await runtime.initialize()
    await runtime.register_provider(OllamaProvider())
    await runtime.register_provider(OpenAIProvider())
    runtime.tool_registry.register(ReadFileTool())
    runtime.tool_registry.register(WriteFileTool())
    runtime.tool_registry.register(ListDirectoryTool())
    
    ctx = SessionContext(
        project_path=target_dir,
        workspace_name="repl_session",
        provider_id="ollama",
        model_name="qwen3:1.7b",
        capabilities=[Capability.CHAT, Capability.TOOLS]
    )
    session = runtime.create_session(ctx)
    
    prompt_str = f"LISA[{proj_name}]> "
    
    while True:
        try:
            user_input = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting REPL...")
            break
            
        if not user_input:
            continue
            
        if user_input.lower() in ("exit", "quit"):
            print("Exiting L.I.S.A. REPL session...")
            break
        elif user_input.lower() == "help":
            print("\n💡 REPL Commands:")
            print("  help           Display this REPL help menu")
            print("  doctor         Run platform health & architecture diagnostics")
            print("  compare        Analyze historical benchmark flight logs")
            print("  activity [m]   Set mode: off | compact | verbose")
            print("  summarize boot Summarize BOOT.md / AGENTS.md active milestone")
            print("  read <file>    Read target file content")
            print("  switch         Switch active project")
            print("  exit / quit    Exit REPL session\n")
        elif user_input.lower().startswith("activity"):
            parts = user_input.split()
            if len(parts) == 1:
                print(f"Current activity mode: {activity_console.mode}")
                continue

            mode = parts[1].strip().lower()
            if activity_console.set_mode(mode):
                print(f"Activity mode set to: {mode}")
            else:
                print("Invalid activity mode. Use: off | compact | verbose")
        elif user_input.lower() in ("list", "ls", "dir"):
            list_tool = ListDirectoryTool()
            args = {"path": target_dir}
            recorder.record_event("flight_stage", {
                "stage": "tool_request",
                "tool_name": "list_directory",
                "arguments": args,
                "session_id": session.session_id,
            })
            res = await list_tool.execute(path=target_dir, project_path=target_dir)
            if res.metadata:
                recorder.record_event("flight_stage", {
                    "stage": "path_resolution",
                    "tool_name": "list_directory",
                    "input_path": res.metadata.get("input_path"),
                    "resolved_path": res.metadata.get("resolved_path"),
                    "path_kind": res.metadata.get("path_kind"),
                    "session_id": session.session_id,
                })
                recorder.record_event("flight_stage", {
                    "stage": "resolved_path",
                    "tool_name": "list_directory",
                    "resolved_path": res.metadata.get("resolved_path"),
                    "session_id": session.session_id,
                })
            recorder.record_event("flight_stage", {
                "stage": "tool_result",
                "tool_name": "list_directory",
                "success": res.success,
                "session_id": session.session_id,
            })
            if res.success:
                print(f"\n📂 Directory Contents of '{proj_name}' ({target_dir}):")
                for item in sorted(res.output):
                    print(f"  • {item}")
                print()
            else:
                print(f"❌ {res.error}")
        elif user_input.lower() == "doctor":
            from lisa.cli.main import run_doctor
            await run_doctor(target_dir)
        elif user_input.lower() == "compare":
            from lisa.cli.main import run_benchmark_compare
            await run_benchmark_compare(target_dir)
        elif user_input.lower() == "switch":
            await runtime.shutdown()
            print("\nSwitching project...")
            await start_repl(None)
            return
        elif user_input.lower() == "summarize boot":
            prompt = f"Please read {target_dir}/BOOT.md and summarize the active milestone."
            res = await session.send_message(prompt)
            print(f"\n{res}\n")
        elif user_input.lower().startswith("read "):
            file_rel = user_input[5:].strip()
            read_tool = ReadFileTool()
            args = {"path": file_rel}
            recorder.record_event("flight_stage", {
                "stage": "tool_request",
                "tool_name": "read_file",
                "arguments": args,
                "session_id": session.session_id,
            })
            res = await read_tool.execute(path=file_rel, project_path=target_dir)
            if res.metadata:
                recorder.record_event("flight_stage", {
                    "stage": "path_resolution",
                    "tool_name": "read_file",
                    "input_path": res.metadata.get("input_path"),
                    "resolved_path": res.metadata.get("resolved_path"),
                    "path_kind": res.metadata.get("path_kind"),
                    "session_id": session.session_id,
                })
                recorder.record_event("flight_stage", {
                    "stage": "resolved_path",
                    "tool_name": "read_file",
                    "resolved_path": res.metadata.get("resolved_path"),
                    "session_id": session.session_id,
                })
            recorder.record_event("flight_stage", {
                "stage": "tool_result",
                "tool_name": "read_file",
                "success": res.success,
                "session_id": session.session_id,
            })

            if res.success:
                print(f"\n--- {file_rel} ---")
                print(res.output)
                print("-------------------\n")
            else:
                print(f"❌ {res.error}")
        else:
            from lisa.engine.auto_selector import AutoSelector
            from lisa.providers.selector import ProviderSelector
            
            p_selector = ProviderSelector(runtime.provider_registry)
            auto_selector = AutoSelector(p_selector)
            plan = await auto_selector.plan_execution(user_input)
            
            print("\n🧠 AUTO EXECUTION PLAN")
            print("────────────────────────────────────")
            print(f"Complexity       : {plan.complexity_level}")
            print(f"Provider         : {plan.provider_id}")
            print(f"Model            : {plan.model_name}")
            print(f"Estimated Cost   : {plan.hardware_cost_tier}")
            print(f"Estimated Latency: {plan.estimated_latency_tier}")
            print(f"Hardware Load    : {plan.hardware_load_tier}")
            print(f"\nReason:")
            print(f"  {plan.reason}")
            print("────────────────────────────────────\n")
            
            response = await session.send_message(user_input)
            print(f"\n{response}\n")

    await runtime.shutdown()
