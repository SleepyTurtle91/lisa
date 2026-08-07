from typing import Optional
from lisa.tools.base import BaseTool
from lisa.tools.registry import ToolRegistry
from lisa.tools.manifest import ToolState
from lisa.core.errors import ToolError

class ToolResolver:
    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    def resolve(self, tool_name: str) -> BaseTool:
        tool = self._registry.get(tool_name)
        if not tool:
            raise ToolError(f"Tool '{tool_name}' not found in ToolRegistry.")
            
        state = self._registry.get_state(tool_name)
        if state != ToolState.READY and state != ToolState.RUNNING:
            raise ToolError(f"Tool '{tool_name}' is in non-executable state '{state}'.")
            
        return tool
