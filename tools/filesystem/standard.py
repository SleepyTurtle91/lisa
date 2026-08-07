import os
from typing import Dict, Any
from lisa.tools.base import BaseTool, ToolResult

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
        path = kwargs.get("path")
        if not path or not os.path.exists(path):
            return ToolResult(success=False, output=None, error=f"File not found: {path}")
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return ToolResult(success=True, output=content, error=None)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

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
        path = kwargs.get("path")
        content = kwargs.get("content", "")
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(success=True, output=f"File written to {path}", error=None)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

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
        if not path or not os.path.exists(path):
            return ToolResult(success=False, output=None, error=f"Directory not found: {path}")
        try:
            items = os.listdir(path)
            return ToolResult(success=True, output=items, error=None)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
