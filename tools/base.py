from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from lisa.tools.manifest import ToolManifest, ToolState

@dataclass(frozen=True)
class ToolRequest:
    tool_name: str
    arguments: Dict[str, Any]
    session_id: Optional[str] = None
    timeout_seconds: float = 30.0

@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: float = 0.0
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        pass

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name=self.name,
            version="1.0.0",
            description=self.description
        )

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass
