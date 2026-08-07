from typing import Dict, List, Optional
from lisa.tools.base import BaseTool
from lisa.tools.manifest import ToolManifest, ToolState
from lisa.tools.validator import ToolValidator

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._manifests: Dict[str, ToolManifest] = {}
        self._states: Dict[str, ToolState] = {}

    def register(self, tool: BaseTool) -> ToolManifest:
        ToolValidator.validate_tool(tool, list(self._tools.keys()))
        self._tools[tool.name] = tool
        manifest = tool.manifest
        self._manifests[tool.name] = manifest
        self._states[tool.name] = ToolState.READY
        return manifest

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def get_manifest(self, name: str) -> Optional[ToolManifest]:
        return self._manifests.get(name)

    def get_state(self, name: str) -> Optional[ToolState]:
        return self._states.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def list_manifests(self) -> List[ToolManifest]:
        return list(self._manifests.values())
