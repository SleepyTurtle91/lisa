import time
import logging
from typing import Any, Dict, Optional
from lisa.tools.registry import ToolRegistry
from lisa.tools.resolver import ToolResolver
from lisa.tools.base import ToolRequest, ToolResult

logger = logging.getLogger(__name__)

class ToolExecutor:
    def __init__(self, registry: ToolRegistry, max_retries: int = 1):
        self._registry = registry
        self._resolver = ToolResolver(registry)
        self._max_retries = max_retries

    async def execute_request(self, request: ToolRequest, project_path: Optional[str] = None) -> ToolResult:
        start_time = time.perf_counter()
        
        try:
            tool = self._resolver.resolve(request.tool_name)
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                duration_ms=elapsed_ms
            )
        
        exec_args = dict(request.arguments)
        if project_path and "project_path" not in exec_args:
            exec_args["project_path"] = project_path

        # Pre-invocation Target Grounding Validation (NE-012.1 Experiment A & NE-012.3)
        if request.tool_name in ("read_file", "list_directory") and "path" in exec_args:
            from lisa.tools.filesystem.target_grounding import TargetInspector
            target_path = exec_args.get("path") or ""
            user_prompt = exec_args.get("user_prompt")

            # Validate Target Identity Binding (NE-012.3)
            id_valid, id_reason = TargetInspector.validate_target_identity(user_prompt, target_path, project_path=project_path)
            if not id_valid:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Pre-invocation Grounding Guard Rejected Tool: {id_reason}",
                    duration_ms=elapsed_ms,
                    metadata={
                        "input_path": target_path,
                        "rejected_before_execution": True,
                        "identity_mismatch": True,
                    }
                )

            inspection = TargetInspector.inspect(target_path, project_path=project_path)
            valid, reason = TargetInspector.validate_tool_operation(request.tool_name, inspection)
            if not valid:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Pre-invocation Grounding Guard Rejected Tool: {reason}",
                    duration_ms=elapsed_ms,
                    metadata={
                        "input_path": target_path,
                        "resolved_path": inspection.resolved_path,
                        "target_type": inspection.target_type.name,
                        "rejected_before_execution": True,
                    }
                )

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                raw_res = await tool.execute(**exec_args)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return ToolResult(
                    success=raw_res.success,
                    output=raw_res.output,
                    error=raw_res.error,
                    duration_ms=elapsed_ms,
                    artifacts=raw_res.artifacts,
                    metadata=raw_res.metadata
                )
            except Exception as e:
                last_error = f"Execution failed (attempt {attempt + 1}/{self._max_retries + 1}): {str(e)}"
                logger.warning(f"Tool '{request.tool_name}' error: {last_error}")
                
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return ToolResult(
            success=False,
            output=None,
            error=last_error,
            duration_ms=elapsed_ms
        )

# Alias for backwards compatibility during migration
ToolDispatcher = ToolExecutor
