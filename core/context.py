from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional

class Capability(Enum):
    # Core Capabilities
    CHAT = auto()
    TOOLS = auto()
    STREAMING = auto()
    JSON = auto()
    VISION = auto()
    EMBEDDINGS = auto()
    IMAGE = auto()
    AUDIO = auto()
    CODE_EXECUTION = auto()

    # Advanced Capabilities (Reserved)
    FUNCTION_CALLING = auto()
    STRUCTURED_OUTPUT = auto()
    LONG_CONTEXT = auto()
    MULTIMODAL = auto()

@dataclass
class SessionContext:
    project_path: str
    workspace_name: str
    provider_id: Optional[str]
    model_name: str
    capabilities: List[Capability] = field(default_factory=list)
