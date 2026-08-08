import os
from typing import Any, Dict
from lisa.tools.base import BaseTool, ToolResult


def _resolve_path(path: str, project_path: str) -> str:
    """Resolve path deterministically while preserving absolute paths unchanged."""
    if os.path.isabs(path):
        return os.path.normpath(path)
    return os.path.normpath(os.path.join(project_path, path))


def _case_sensitive_suggestion(full_path: str) -> str:
    """Return a same-directory case variant suggestion without changing the path."""
    parent_dir, target_name = os.path.split(full_path)
    if not parent_dir or not target_name or not os.path.isdir(parent_dir):
        return ""

    try:
        for entry in os.listdir(parent_dir):
            if entry == target_name:
                return ""
            if entry.lower() == target_name.lower():
                return entry
    except Exception:
        return ""

    return ""

class ReadFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a specified file relative to the project workspace."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the target file."
                }
            },
            "required": ["path"]
        }

    async def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            project_path = kwargs.get("project_path") or os.getcwd()
            full_path = _resolve_path(path, project_path)
            metadata = {
                "input_path": path,
                "resolved_path": full_path,
                "path_kind": "absolute" if os.path.isabs(path) else "relative",
                "project_path": project_path,
            }
            
            if not full_path or not os.path.exists(full_path):
                error = f"File not found: {path} (Resolved: {full_path})"
                suggestion = _case_sensitive_suggestion(full_path)
                if suggestion:
                    error = f"{error}. Did you mean '{suggestion}'?"
                return ToolResult(success=False, output=None, error=error, metadata=metadata)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ToolResult(success=True, output=content, metadata=metadata)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
