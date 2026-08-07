from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class ToolPermission(Enum):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    NETWORK = auto()
    DATABASE = auto()
    GIT = auto()

class ToolState(Enum):
    DISCOVERED = auto()
    REGISTERED = auto()
    VALIDATED = auto()
    READY = auto()
    RUNNING = auto()
    FAILED = auto()
    DISABLED = auto()

@dataclass(frozen=True)
class ToolManifest:
    name: str
    version: str
    description: str
    permissions: List[ToolPermission] = field(default_factory=list)
    timeout_seconds: float = 30.0
    dangerous: bool = False
    experimental: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ToolContext:
    working_directory: str
    session_id: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    permissions: List[ToolPermission] = field(default_factory=list)
