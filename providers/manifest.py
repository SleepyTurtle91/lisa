from dataclasses import dataclass, field
from typing import List, Dict, Any
from lisa.core.context import Capability

@dataclass
class ProviderManifest:
    id: str
    name: str
    version: str
    healthy: bool
    priority: int = 100
    capabilities: List[Capability] = field(default_factory=list)
    supported_models: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    limits: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
