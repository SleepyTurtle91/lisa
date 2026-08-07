from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from lisa.core.context import Capability

@dataclass
class ProviderContext:
    session_id: str
    requested_capabilities: List[Capability]
    selected_model: str
    tool_schemas: Optional[List[Dict[str, Any]]] = None
    token_budget: Optional[int] = None
    temperature: float = 0.7
    system_prompt: Optional[str] = None
