from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from lisa.core.context import Capability

@dataclass(frozen=True)
class InferenceRequest:
    session_id: str
    messages: List[Dict[str, Any]]
    model_name: Optional[str] = None
    requested_capabilities: List[Capability] = field(default_factory=list)
    tools: Optional[List[Dict[str, Any]]] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None

@dataclass(frozen=True)
class InferenceResponse:
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, int]] = None
    raw_payload: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class InferenceResult:
    success: bool
    response: Optional[InferenceResponse]
    provider_id: str
    model_name: str
    latency_ms: float
    error: Optional[str] = None
