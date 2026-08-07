from typing import Any, Dict, Optional

class LisaRuntimeError(Exception):
    """Base exception for all L.I.S.A. runtime errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ProviderError(LisaRuntimeError):
    """Errors originating from AI Provider connections, timeouts, or completions."""
    pass

class ToolError(LisaRuntimeError):
    """Errors occurring during tool validation, compilation, or execution."""
    pass

class ValidationError(LisaRuntimeError):
    """Errors raised when schemas, configurations, or capability manifests fail validation."""
    pass

class BootstrapError(LisaRuntimeError):
    """Errors occurring during project discovery or boot configuration parsing."""
    pass

class WorkflowError(LisaRuntimeError):
    """Errors occurring during workflow execution or step transitions."""
    pass

class SessionError(LisaRuntimeError):
    """Errors occurring during session creation, messaging, or state transitions."""
    pass
