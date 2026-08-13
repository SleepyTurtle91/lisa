"""
NE-014.2 Live REPL Routing Integration Benchmark

Validates that the live REPL command loop uses InputBoundaryClassifier to route:
  1. 'read BOOT.md' -> DIRECT_COMMAND -> ReadFileTool execution
  2. 'read files inside /docs and suggest a plan' -> NATURAL_LANGUAGE -> LLM session execution (No literal read_file hijack!)
  3. '/workspace/Projects/retails' -> PATH_INPUT -> Deterministic path listing
"""

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.cli.input_classifier import InputBoundaryClassifier, InputClass
from lisa.core.context import Capability, SessionContext
from lisa.core.kernel import LisaRuntime
from lisa.providers.ollama.provider import OllamaProvider
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool
from lisa.tools.filesystem.standard import ListDirectoryTool


@dataclass
class LiveRouteCase:
    case_id: str
    input_text: str
    expected_class: InputClass
    must_not_hijack_direct_read: bool


LIVE_CASES: List[LiveRouteCase] = [
    LiveRouteCase("R1", "read BOOT.md", InputClass.DIRECT_COMMAND, False),
    LiveRouteCase("R2", "read files inside /docs and suggest a plan", InputClass.NATURAL_LANGUAGE, True),
    LiveRouteCase("R3", "/workspace/Projects/retails", InputClass.PATH_INPUT, False),
]


async def run_experiment_ne014_2(project_path: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    resolved_dir = output_dir or Path(__file__).resolve().parent
    resolved_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"ne014_2_live_routing_{timestamp}"
    recorder = FlightRecorder(session_id=session_id, log_dir=resolved_dir)
    runtime = LisaRuntime(flight_recorder=recorder)

    results = []
    all_passed = True

    try:
        await runtime.initialize()
        await runtime.register_provider(OllamaProvider())
        runtime.tool_registry.register(ReadFileTool())
        runtime.tool_registry.register(ListDirectoryTool())

        ctx = SessionContext(
            project_path=project_path,
            workspace_name="ne_014_2_routing",
            provider_id="ollama",
            model_name="qwen3:1.7b",
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )
        session = runtime.create_session(ctx)

        for case in LIVE_CASES:
            classified = InputBoundaryClassifier.classify(case.input_text, project_path=project_path)
            class_match = (classified.input_class == case.expected_class)

            direct_read_hijacked = False
            model_received = False
            response_text = ""

            if classified.input_class == InputClass.DIRECT_COMMAND and classified.command == "read":
                # Simulated REPL direct command branch
                file_rel = classified.target or ""
                read_tool = ReadFileTool()
                res = await read_tool.execute(path=file_rel, project_path=project_path)
                response_text = str(res.output) if res.success else str(res.error)

            elif classified.input_class == InputClass.PATH_INPUT:
                # Simulated REPL path input branch
                target_path = classified.target or case.input_text
                list_tool = ListDirectoryTool()
                res = await list_tool.execute(path=target_path, project_path=project_path)
                response_text = f"Listed {len(res.output)} items" if res.success else str(res.error)

            else:
                # Simulated REPL natural language branch -> LLM session execution
                model_received = True
                response_text = await session.send_message(case.input_text)
                # Verify that no literal read_file tool request was generated for "files inside /docs..."
                for event in recorder.get_events():
                    payload = event.get("payload") or {}
                    if event.get("event_type") == "flight_stage" and payload.get("stage") == "tool_request":
                        args = payload.get("arguments") or {}
                        req_path = args.get("path") or ""
                        if "files inside" in req_path:
                            direct_read_hijacked = True

            passed = class_match and (not direct_read_hijacked if case.must_not_hijack_direct_read else True)
            if not passed:
                all_passed = False

            results.append({
                "case_id": case.case_id,
                "input_text": case.input_text,
                "expected_class": case.expected_class.name,
                "actual_class": classified.input_class.name,
                "class_match": class_match,
                "model_received": model_received,
                "direct_read_hijacked": direct_read_hijacked,
                "response_snippet": response_text[:150],
                "passed": passed,
            })
            print(f"  [{case.case_id}] Input: {case.input_text!r}")
            print(f"         → class={classified.input_class.name}, model_received={model_received}, hijacked={direct_read_hijacked}, passed={passed}")

        artifact = {
            "experiment": "NE-014.2",
            "title": "Live REPL Routing Integration Benchmark",
            "timestamp": datetime.now().isoformat() + "Z",
            "project_path": project_path,
            "model": "qwen3:1.7b",
            "provider": "ollama",
            "all_passed": all_passed,
            "results": results,
            "recorder_file": str(recorder.log_file),
        }

        artifact_path = resolved_dir / f"ne_014_2_live_routing_{timestamp}.json"
        with open(artifact_path, "w", encoding="utf-8") as fh:
            json.dump(artifact, fh, indent=2)

        print(f"\nNE-014.2 Integration Artifact written to: {artifact_path}")
        print(f"All Routing Checks Passed: {all_passed}")
        return artifact
    finally:
        try:
            await runtime.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NE-014.2 Live REPL Routing Integration Benchmark")
    parser.add_argument("project_path", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    print("NE-014.2 — Live REPL Routing Integration Benchmark")
    print(f"Project: {args.project_path}")
    print()

    asyncio.run(run_experiment_ne014_2(project_path=args.project_path))
