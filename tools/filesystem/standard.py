import os
from typing import Dict, Any
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
        return "Read absolute or relative file content from local filesystem."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Target file path to read."
                }
            },
            "required": ["path"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
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
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ToolResult(success=True, output=content, error=None, metadata=metadata)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e), metadata=metadata)

class WriteFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write text content to a target file path."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Target path."},
                "content": {"type": "string", "description": "Text content."}
            },
            "required": ["path", "content"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        project_path = kwargs.get("project_path") or os.getcwd()
        full_path = _resolve_path(path, project_path)
        metadata = {
            "input_path": path,
            "resolved_path": full_path,
            "path_kind": "absolute" if os.path.isabs(path) else "relative",
            "project_path": project_path,
        }
        
        try:
            os.makedirs(os.path.dirname(os.path.abspath(full_path)), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(success=True, output=f"File written to {full_path}", error=None, metadata=metadata)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e), metadata=metadata)

class ListDirectoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "List files and directories within a target directory."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path."}
            },
            "required": ["path"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path")
        project_path = kwargs.get("project_path") or os.getcwd()
        path_kind = "absolute" if isinstance(path, str) and os.path.isabs(path) else "relative"
        if not path or path in (".", "./", "", "root"):
            full_path = os.path.normpath(project_path)
            path_kind = "project_root"
        elif not os.path.isabs(path):
            full_path = _resolve_path(path, project_path)
        else:
            full_path = _resolve_path(path, project_path)

        metadata = {
            "input_path": path,
            "resolved_path": full_path,
            "path_kind": path_kind,
            "project_path": project_path,
        }

        if not full_path or not os.path.exists(full_path):
            return ToolResult(success=False, output=None, error=f"Directory not found: {path} (Resolved: {full_path})", metadata=metadata)
        try:
            items = os.listdir(full_path)
            return ToolResult(success=True, output=items, error=None, metadata=metadata)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e), metadata=metadata)
