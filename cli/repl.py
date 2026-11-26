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
from lisa.cli.input_classifier import InputBoundaryClassifier, InputClass
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

CONFIG_DIR = Path.home() / ".lisa"
RECENT_FILE = CONFIG_DIR / "recent.json"
PROJECT_REGISTRY_FILE = CONFIG_DIR / "projects.json"


def _project_executor():
    return ProjectExecutor(registry=ProjectRegistry(storage_path=PROJECT_REGISTRY_FILE))


def _project_identifier(executor, value):
    result = executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
    matches = [
        item for item in result.manifests
        if item.project_id == value or item.name.casefold() == value.casefold()
    ]
    return matches[0] if len(matches) == 1 else None


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

def _project_search_roots() -> List[Path]:
    """Return portable project-discovery roots.

    Operators can provide roots with LISA_PROJECTS_DIRS, separated using the
    platform's PATH separator. Conventional folders are discovery hints only;
    no single folder is required for L.I.S.A. to run.
    """
    configured = os.getenv("LISA_PROJECTS_DIRS", "")
    roots = [Path(item.strip()).expanduser() for item in configured.split(os.pathsep) if item.strip()]
    home = Path.home()
    roots.extend(
        home / name
        for name in (
            "Projects", "projects", "Development", "development/projects",
            "workspace", "Workspaces", "code", "src",
        )
    )
    roots.append(Path.cwd())

    unique_roots = []
    seen = set()
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved not in seen and resolved.is_dir():
            seen.add(resolved)
            unique_roots.append(resolved)
    return unique_roots


def scan_common_projects(search_dirs: Optional[List[Path]] = None) -> List[str]:
    """Discover projects from configurable, portable workspace roots."""
    roots = search_dirs if search_dirs is not None else _project_search_roots()
    markers = ("BOOT.md", "AGENTS.md", ".git", "README.md")
    found = set()

    for root in roots:
        root_path = Path(root).expanduser()
        if not root_path.is_dir():
            continue
        try:
            for child in root_path.iterdir():
                if not child.is_dir() or child.name.startswith("."):
                    continue
                if any((child / marker).exists() for marker in markers):
                    found.add(str(child.resolve()))
        except OSError:
            continue

    return sorted(found)
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

def _active_project_target(project_executor, force_select: bool = False) -> Optional[str]:
    """Return the active project path unless the operator explicitly requests selection."""
    if force_select:
        return None
    active_context = project_executor.execute(
        ProjectRequest(operation=ProjectOperation.LIST)
    ).context
    return active_context.root_path if active_context is not None else None


async def start_repl(target_dir: Optional[str] = None, force_select: bool = False):
    project_executor = _project_executor()
    if not target_dir:
        target_dir = _active_project_target(project_executor, force_select=force_select)
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

    registration = project_executor.execute(ProjectRequest(
        operation=ProjectOperation.REGISTER, path=target_dir
    ))
    if not registration.success:
        print(f"Project registration failed; refusing to start an unregistered context: {registration.error}")
        return
    activated = project_executor.execute(ProjectRequest(
        operation=ProjectOperation.ACTIVATE,
        project_id=registration.manifest.project_id,
    ))
    if not activated.success:
        print(f"Project activation failed; refusing to start session: {activated.error}")
        return

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
            print("  projects       List registered projects")
            print("  project add <path>   Register another project")
            print("  project use <id|name> Switch to a registered project")
            print("  project remove <id>  Unregister a project")
            print("  project inspect <id|name>  Build a read-only project profile")
            print("  project find <terms>  Search registered projects for capability evidence")
            print("  project compare <source-id> <target-id> [terms]  Triage reuse compatibility")
            print("  project plan <source-id> <target-id> <terms>  Create a review-only adaptation plan")
            print("  exit / quit    Exit REPL session\n")
        classified = InputBoundaryClassifier.classify(user_input, project_path=target_dir)

        if classified.input_class == InputClass.DIRECT_COMMAND:
            cmd = classified.command or ""
            if cmd == "doctor":
                from lisa.cli.main import run_doctor
                await run_doctor(target_dir)
            elif cmd == "compare":
                from lisa.cli.main import run_benchmark_compare
                await run_benchmark_compare(target_dir)
            elif cmd == "projects":
                result = project_executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
                if not result.manifests:
                    print("No registered projects.")
                else:
                    for item in result.manifests:
                        active = "*" if result.context and result.context.project_id == item.project_id else " "
                        print(f" {active} {item.name} [{item.project_id}]")
                        print(f"    {item.root_path}")
            elif cmd == "project":
                parts = (classified.target or "").split()
                action = parts[0].lower() if parts else "help"
                value = " ".join(parts[1:]).strip()
                if action == "add" and value:
                    added = project_executor.execute(ProjectRequest(
                        operation=ProjectOperation.REGISTER, path=value
                    ))
                    if added.success:
                        print(f"Registered {added.manifest.name} [{added.manifest.project_id}]")
                    else:
                        print(f"Registration failed: {added.error}")
                elif action in ("list", "ls"):
                    result = project_executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
                    for item in result.manifests:
                        active = "*" if result.context and result.context.project_id == item.project_id else " "
                        print(f" {active} {item.name} [{item.project_id}] - {item.root_path}")
                elif action == "plan" and len(parts) >= 4:
                    source = _project_identifier(project_executor, parts[1])
                    target = _project_identifier(project_executor, parts[2])
                    if source is None or target is None:
                        print("Source or target not found/ambiguous. Use 'projects' to list IDs.")
                    else:
                        planned = ProjectAdaptationPlanner(
                            registry=ProjectRegistry(storage_path=PROJECT_REGISTRY_FILE)
                        ).execute(ProjectAdaptationRequest(
                            source_project_id=source.project_id,
                            target_project_id=target.project_id,
                            capability_query=" ".join(parts[3:]),
                        ))
                        if not planned.success:
                            print(f"Adaptation planning failed: {planned.error}")
                        else:
                            plan = planned.plan
                            print(f"\nAdaptation plan {plan.plan_id}: {plan.source_project_name} -> {plan.target_project_name}")
                            print(f"Status: {plan.status.value}")
                            print(plan.summary)
                            print(f"Compatibility status: {plan.compatibility_status.value}")
                            print(f"Shared technology markers: {', '.join(plan.shared_technologies) or '(none)'}")
                            for evidence in plan.source_evidence:
                                print(f"Source evidence: {evidence.relative_path} [sha256:{evidence.sha256[:12]}]")
                            for source_path in plan.source_paths:
                                print(f"Source path: {source_path}")
                            for blocker in plan.blockers:
                                print(f"Blocker: {blocker}")
                            for constraint in plan.target_constraints:
                                print(f"Preserve [{constraint.relative_path}]: {constraint.excerpt}")
                            for step in plan.steps:
                                print(f"{step.order}. {step.title} — {step.description}")
                            print(f"Authorization required: {plan.authorization_required}")
                            print(f"Execution authorized: {plan.execution_authorized}")
                            print("This is a review-only plan. No code was copied, modified, or executed.\n")
                elif action in ("compare", "compatibility") and len(parts) >= 3:
                    source = _project_identifier(project_executor, parts[1])
                    target = _project_identifier(project_executor, parts[2])
                    if source is None or target is None:
                        print("Source or target not found/ambiguous. Use 'projects' to list IDs.")
                    else:
                        query = " ".join(parts[3:]).strip() or None
                        compared = ProjectCompatibilityExecutor(
                            registry=ProjectRegistry(storage_path=PROJECT_REGISTRY_FILE)
                        ).execute(ProjectCompatibilityRequest(
                            source_project_id=source.project_id,
                            target_project_id=target.project_id,
                            capability_query=query,
                        ))
                        if not compared.success:
                            print(f"Compatibility analysis failed: {compared.error}")
                        else:
                            report = compared.report
                            print(f"\nCompatibility triage: {report.source_project_name} -> {report.target_project_name}")
                            print(f"Status: {report.status.value}")
                            print(f"Shared technologies: {', '.join(report.shared_technologies) or '(none)'}")
                            if report.capability_query:
                                print(f"Capability query: {report.capability_query} (found: {report.source_capability_found})")
                                print(f"Matched terms: {', '.join(report.matched_terms) or '(none)'}")
                            for flag in report.risk_flags:
                                print(f"Risk: {flag}")
                            for constraint in report.constraints:
                                print(f"Constraint [{constraint.project_role}] {constraint.relative_path}: {constraint.excerpt}")
                            print("No code was transferred or modified. Review the evidence before planning an adaptation.\n")
                elif action in ("find", "search") and value:
                    discovery = CapabilityDiscoveryExecutor(
                        registry=ProjectRegistry(storage_path=PROJECT_REGISTRY_FILE)
                    ).execute(CapabilityDiscoveryRequest(query=value))
                    if not discovery.success:
                        print(f"Capability search failed: {discovery.error}")
                    elif not discovery.matches:
                        print(f"No project evidence matched: {value}")
                    else:
                        print(f"\nCapability candidates for: {value}")
                        for match in discovery.matches:
                            print(f"  {match.project_name} [{match.project_id}] — {match.score:.0%} match")
                            print(f"    Terms: {', '.join(match.matched_terms)}")
                            for evidence in match.evidence:
                                print(f"    Evidence: {evidence.relative_path} [{evidence.evidence_kind}; sha256:{evidence.sha256[:12]}]")
                            for source_path in match.source_paths:
                                print(f"    Source path: {source_path}")
                        print()
                elif action in ("inspect", "profile") and value:
                    selected = _project_identifier(project_executor, value)
                    if selected is None:
                        print("Project not found or ambiguous. Use 'projects' to list IDs.")
                    else:
                        profiled = ProjectProfileExecutor(
                            registry=ProjectRegistry(storage_path=PROJECT_REGISTRY_FILE)
                        ).execute(ProjectProfileRequest(project_id=selected.project_id))
                        if not profiled.success:
                            print(f"Project inspection failed: {profiled.error}")
                        else:
                            profile = profiled.profile
                            print(f"\nProject profile: {profile.name} [{profile.project_id}]")
                            print(f"Technologies: {', '.join(profile.technologies) or 'unknown'}")
                            print(f"Top-level directories: {', '.join(profile.top_level_directories) or '(none)'}")
                            print(f"Source files inventoried: {profile.source_file_count}")
                            print("Evidence:")
                            for item in profile.evidence:
                                print(f"  - {item.relative_path} [{item.evidence_kind}; sha256:{item.sha256[:12]}]")
                            print()
                elif action in ("use", "activate") and value:
                    selected = _project_identifier(project_executor, value)
                    if selected is None:
                        print("Project not found or ambiguous. Use 'projects' to list IDs.")
                    else:
                        await runtime.shutdown()
                        print(f"Switching to {selected.name}...")
                        await start_repl(selected.root_path)
                        return
                elif action in ("remove", "unregister") and value:
                    current = project_executor.execute(ProjectRequest(operation=ProjectOperation.LIST)).context
                    if current and current.project_id == value:
                        print("Cannot unregister the active project from its own session. Switch first.")
                    else:
                        removed = project_executor.execute(ProjectRequest(
                            operation=ProjectOperation.UNREGISTER, project_id=value
                        ))
                        print("Project unregistered." if removed.success else f"Unregister failed: {removed.error}")
                else:
                    print("Usage: project add <path> | project list | project inspect <id|name> | project find <terms> | project compare <source-id> <target-id> [terms] | project plan <source-id> <target-id> <terms> | project use <id|name> | project remove <id>")
            elif cmd == "switch":
                await runtime.shutdown()
                print("\nSwitching project...")
                await start_repl(None, force_select=True)
                return
            elif cmd == "summarize boot":
                prompt = f"Please read {target_dir}/BOOT.md and summarize the active milestone."
                res = await session.send_message(prompt)
                print(f"\n{res}\n")
            elif cmd in ("list", "ls", "dir"):
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
            elif cmd == "read" and classified.target:
                file_rel = classified.target
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
            elif cmd == "activity":
                parts = user_input.split()
                if len(parts) == 1:
                    print(f"Current activity mode: {activity_console.mode}")
                    continue

                mode = parts[1].strip().lower()
                if activity_console.set_mode(mode):
                    print(f"Activity mode set to: {mode}")
                else:
                    print("Invalid activity mode. Use: off | compact | verbose")

        elif classified.input_class == InputClass.PATH_INPUT:
            target_path = classified.target or user_input
            list_tool = ListDirectoryTool()
            res = await list_tool.execute(path=target_path, project_path=target_dir)
            if res.success:
                print(f"\n📂 Deterministic Path Contents ({target_path}):")
                for item in sorted(res.output):
                    print(f"  • {item}")
                print()
            else:
                print(f"❌ Path inspection error: {res.error}")
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
