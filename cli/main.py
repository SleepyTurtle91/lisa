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
from lisa.projects.execution import ExecutionChange, ProjectExecutionRequest
from lisa.projects.execution_executor import ProjectExecutionExecutor
from lisa.projects.execution_lifecycle import ProjectExecutionLifecycle
from lisa.projects.execution_history import ProjectExecutionHistory
from lisa.projects.execution_ledger import ProjectExecutionLedger
from lisa.projects.execution_recovery import ProjectExecutionRecovery

PROJECT_REGISTRY_PATH = Path.home() / ".lisa" / "projects.json"
PROJECT_EXECUTION_STATE_PATH = Path.home() / ".lisa" / "executions"


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
    if action == "ledger":
        if len(args) != 2 or args[1] not in ("verify", "migrate", "recover"):
            print("Usage: lisa project ledger <verify|migrate|recover>")
            return
        ledger = ProjectExecutionLedger(PROJECT_EXECUTION_STATE_PATH)
        if args[1] == "recover":
            try:
                digest = ledger.preview_recovery_digest()
            except Exception as exc:
                print(f"Ledger recovery preview failed: {exc}")
                return
            if digest is None:
                print("No pending ledger transaction requires recovery.")
                return
            print("A previously interrupted ledger append is awaiting recovery.")
            print("Recovery will complete only that authenticated, pending event.")
            try:
                confirmation = input(f"Type exactly 'RECOVER {digest}' to authorize recovery: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("Ledger recovery cancelled.")
                return
            result = ledger.recover(confirmation)
            if not result["success"]:
                print(f"Ledger recovery failed: {result['error']}")
                return
            print(f"Ledger transaction recovered: sequence {result['sequence']} ({result['execution_id']})")
            print("Run 'lisa project ledger verify' to confirm the recovered ledger.")
            return
        if args[1] == "verify":
            result = ledger.verify()
            if not result["success"]:
                print(f"Ledger verification FAILED: {result['error']}")
                return
            print(f"Ledger status: {result['status']}")
            print(f"Authenticated events: {result['event_count']}")
            if result.get("head_hash"):
                print(f"Head hash: {result['head_hash']}")
            print("The local key is not an external trust anchor.")
            return
        result = ledger.migrate_legacy()
        if not result["success"]:
            print(f"Legacy migration failed: {result['error']}")
            return
        print(f"Legacy execution snapshots imported: {result['imported']}")
        print("Imported snapshots are anchored from migration time only; prior history is not authenticated.")
        return

    if action == "recover":
        recovery = ProjectExecutionRecovery(
            ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH),
            state_dir=PROJECT_EXECUTION_STATE_PATH,
        )
        if len(args) == 1:
            try:
                pending = recovery.list_pending()
            except Exception as exc:
                print(f"Interrupted execution scan failed: {exc}")
                return
            if not pending:
                print("No interrupted executions require recovery.")
                return
            print("Interrupted executions (recovery rolls back to the exact pre-execution state):")
            for item in pending:
                print(
                    f"{item['execution_id']} | {item['status']} | "
                    f"{item['file_count']} files | {item.get('created_at') or 'unknown'}"
                )
            print("Review one execution with: lisa project recover <execution-id>")
            return
        if len(args) != 2:
            print("Usage: lisa project recover [<execution-id>]")
            return
        try:
            digest = recovery.preview_digest(args[1])
        except Exception as exc:
            print(f"Recovery preview failed: {exc}")
            return
        print(f"Execution: {args[1]}")
        print("L.I.S.A. will restore every affected file to its verified pre-execution state.")
        print("Recovery is refused if any target file has an unknown later version.")
        try:
            confirmation = input(f"Type exactly 'RECOVER {digest}' to authorize rollback: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("Execution recovery cancelled.")
            return
        result = recovery.recover(args[1], confirmation)
        if not result["success"]:
            print(f"Execution recovery refused or failed: {result['error']}")
            return
        print(f"Interrupted execution recovered and rolled back: {result['execution_id']}")
        for path in result["restored_files"]:
            print(f"Restored: {path}")
        if result.get("ledger_warning"):
            print(f"WARNING: target recovery completed but ledger append failed: {result['ledger_warning']}")
        return

    if action == "history":
        project_id = None
        if len(args) == 3 and args[1] == "--project":
            project_id = args[2]
        elif len(args) != 1:
            print("Usage: lisa project history [--project <project-id>]")
            return
        history = ProjectExecutionHistory(
            ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH),
            state_dir=PROJECT_EXECUTION_STATE_PATH,
        )
        try:
            records = history.list_history(project_id=project_id)
        except Exception as exc:
            print(f"Execution history unavailable: {exc}")
            return
        if not records:
            print("No matching cross-project executions found.")
            return
        print("Cross-project execution history (newest first):")
        for record in records:
            print(
                f"{record.get('execution_id')} | "
                f"{record.get('source_project_name')} -> {record.get('target_project_name')} | "
                f"{record.get('lifecycle_status')} | validation: {record.get('validation_status')} | "
                f"files: {record.get('file_count')} | integrity: {record.get('integrity_status')} | ledger: {record.get('ledger_status', 'unknown')}"
            )
            print(f"    Created: {record.get('created_at') or 'unknown'}")
            if record.get("integrity_error"):
                print(f"    Integrity error: {record['integrity_error']}")
        print("History is read-only. See 'lisa project ledger verify' for ledger status.")
        return

    if action == "verify" and len(args) == 2:
        history = ProjectExecutionHistory(
            ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH),
            state_dir=PROJECT_EXECUTION_STATE_PATH,
        )
        result = history.verify(args[1])
        if not result["success"]:
            print(f"Integrity verification FAILED: {result['error']}")
            return
        record = result["record"]
        print(f"Integrity verification: {record['integrity_status']}")
        print(f"Execution: {record['execution_id']}")
        print(f"Projects: {record['source_project_name']} -> {record['target_project_name']}")
        print(f"Lifecycle: {record['lifecycle_status']}")
        print(f"Validation: {record['validation_status']} ({record['validation_integrity']})")
        print(f"Backups: {record['backup_integrity']} ({record['file_count']} changed files)")
        print(f"Trusted ledger: {record.get('ledger_status', 'unknown')} ({record.get('ledger_event_count', 0)} events)")
        print(f"Current target files: {record['target_file_integrity']}")
        for note in record["integrity_notes"]:
            print(f"Note: {note}")
        return

    if action == "rollback" and len(args) == 2:
        registry = ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH)
        lifecycle = ProjectExecutionLifecycle(registry, state_dir=PROJECT_EXECUTION_STATE_PATH)
        try:
            digest = lifecycle.preview_rollback_digest(args[1])
        except Exception as exc:
            print(f"Rollback preview failed: {exc}")
            return
        print(f"Execution: {args[1]}")
        print("L.I.S.A. will restore the exact pre-execution bytes from verified backups.")
        print("Rollback is refused if any affected target file has changed independently.")
        try:
            confirmation = input(f"Type exactly 'ROLLBACK {digest}' to authorize recovery: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("Rollback cancelled.")
            return
        result = lifecycle.rollback(args[1], confirmation)
        if not result["success"]:
            print(f"Rollback refused or failed: {result['error']}")
            return
        print(f"Rollback completed: {result['execution_id']}")
        for path in result["restored_files"]:
            print(f"Restored: {path}")
        if result.get("ledger_warning"):
            print(f"WARNING: rollback completed but ledger append failed: {result['ledger_warning']}")
        return

    if action == "validate" and len(args) >= 2:
        options = {}
        index = 2
        allowed = {"--status", "--command", "--summary", "--evidence"}
        while index < len(args):
            key = args[index]
            if key not in allowed or index + 1 >= len(args) or key in options:
                print("Usage: lisa project validate <execution-id> --status passed|failed --command <description> --summary <result> [--evidence <relative-report-path>]")
                return
            options[key] = args[index + 1]
            index += 2
        if not all(key in options for key in ("--status", "--command", "--summary")):
            print("Validation requires --status, --command, and --summary.")
            return
        registry = ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH)
        lifecycle = ProjectExecutionLifecycle(registry, state_dir=PROJECT_EXECUTION_STATE_PATH)
        try:
            digest = lifecycle.preview_validation_digest(
                args[1], options["--status"], options["--command"],
                options["--summary"], options.get("--evidence"),
            )
        except Exception as exc:
            print(f"Validation preview failed: {exc}")
            return
        print(f"Execution: {args[1]}")
        print(f"Reported test status: {options['--status']}")
        print(f"Test command/description: {options['--command']}")
        print(f"Summary: {options['--summary']}")
        print(f"Evidence file: {options.get('--evidence', '(not supplied; summary only)')}")
        print("L.I.S.A. will record your attestation; it will not run or independently verify the tests.")
        try:
            confirmation = input(f"Type exactly 'RECORD {digest}' to record this validation: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("Validation recording cancelled.")
            return
        result = lifecycle.record_validation(
            args[1], options["--status"], options["--command"],
            options["--summary"], confirmation, options.get("--evidence"),
        )
        if not result["success"]:
            print(f"Validation record refused or failed: {result['error']}")
            return
        print(f"Validation recorded: {result['status']}")
        print(f"Record: {result['validation_path']}")
        print("This is operator-reported evidence, not an independently verified test result.")
        if result.get("ledger_warning"):
            print(f"WARNING: validation recorded but ledger append failed: {result['ledger_warning']}")
        return

    if action == "apply" and len(args) >= 6 and "--patch" in args:
        patch_index = args.index("--patch")
        if patch_index < 4 or patch_index != len(args) - 2:
            print("Usage: lisa project apply <source-id> <target-id> <terms> --patch <patch.json>")
            return
        listing = executor.execute(ProjectRequest(operation=ProjectOperation.LIST))
        source_matches = [p for p in listing.manifests if p.project_id == args[1] or p.name.casefold() == args[1].casefold()]
        target_matches = [p for p in listing.manifests if p.project_id == args[2] or p.name.casefold() == args[2].casefold()]
        if len(source_matches) != 1 or len(target_matches) != 1:
            print("Source or target not found/ambiguous. Use 'lisa project list' to see project IDs.")
            return
        patch_path = Path(args[-1]).expanduser()
        try:
            payload = json.loads(patch_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or set(payload) != {"changes"} or not isinstance(payload["changes"], list):
                raise ValueError("Patch file must be a JSON object containing only a 'changes' list.")
            changes = []
            for item in payload["changes"]:
                if not isinstance(item, dict) or set(item) - {"path", "content", "expected_sha256"}:
                    raise ValueError("Each change may contain only path, content, and expected_sha256.")
                if not isinstance(item.get("path"), str) or not isinstance(item.get("content"), str):
                    raise ValueError("Each change requires string path and content fields.")
                expected = item.get("expected_sha256")
                if expected is not None and not isinstance(expected, str):
                    raise ValueError("expected_sha256 must be a string or null.")
                changes.append(ExecutionChange(
                    relative_path=item["path"],
                    content=item["content"],
                    expected_sha256=expected,
                ))
            if not changes:
                raise ValueError("Patch must contain at least one file change.")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Patch file rejected: {exc}")
            return

        registry = ProjectRegistry(storage_path=PROJECT_REGISTRY_PATH)
        planned = ProjectAdaptationPlanner(registry=registry).execute(ProjectAdaptationRequest(
            source_project_id=source_matches[0].project_id,
            target_project_id=target_matches[0].project_id,
            capability_query=" ".join(args[3:patch_index]),
        ))
        if not planned.success:
            print(f"Adaptation planning failed: {planned.error}")
            return
        plan = planned.plan
        if plan.status.value != "ready_for_review":
            print("Execution refused: the adaptation plan is blocked.")
            for blocker in plan.blockers:
                print(f"Blocker: {blocker}")
            return

        target_root = target_matches[0].root_path
        digest = ProjectExecutionExecutor.approval_digest(plan, changes, target_root)
        print(f"Governed execution preview: {plan.source_project_name} -> {plan.target_project_name}")
        print(f"Plan: {plan.plan_id}")
        print(f"Target root: {target_root}")
        print("Exact proposed changes:")
        for change in changes:
            print(f"--- {change.relative_path} (expected sha256: {change.expected_sha256 or 'NEW FILE'})")
            print(change.content)
        print("No commands or tests will be run by this operation.")
        print("Backups and an audit record will be created outside both project roots.")
        try:
            confirmation = input(f"Type exactly 'APPLY {digest}' to authorize these exact changes: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("Execution cancelled.")
            return
        result = ProjectExecutionExecutor(
            registry=registry,
            state_dir=PROJECT_EXECUTION_STATE_PATH,
        ).execute(ProjectExecutionRequest(
            plan=plan,
            changes=tuple(changes),
            operator_confirmation=confirmation,
        ))
        if not result.success:
            print(f"Execution refused or failed: {result.error}")
            return
        print(f"Execution completed: {result.execution_id}")
        print(f"Changed files: {', '.join(result.changed_files)}")
        print(f"Backup directory: {result.backup_directory}")
        print(f"Audit record: {result.audit_path}")
        print("VALIDATION REQUIRED: run the target project's regression suite before accepting this adaptation.")
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
    print("  project apply <source-id> <target-id> <terms> --patch <patch.json>  Apply an explicitly approved patch.")
    print("  project history [--project <id>]  List cross-project executions (read-only).")
    print("  project verify <execution-id>  Verify audit, backup, and validation evidence integrity.")
    print("  project rollback <execution-id>  Restore verified pre-execution files with explicit approval.")
    print("  project validate <execution-id> --status passed|failed --command <text> --summary <text> [--evidence <path>]  Record operator-reported regression evidence.")
    print("  project add <path>     Register a project directory.")
    print("  project use <id|name>  Set the default active project.")
    print("  project remove <id>    Unregister a project.")
    print("  --help, -h             Display this CLI usage help menu.")
    print("\nExamples:")
    print("  lisa ./my-project")
    print("  lisa doctor ./my-project")
    print("  lisa compare")
    print("  lisa project apply source-id target-id inventory --patch adaptation.json")
    print("  python3 cli/benchmark.py ./my-project qwen3:1.7b")
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
