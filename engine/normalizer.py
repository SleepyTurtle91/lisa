from typing import Dict, Any, Optional, List
from lisa.engine.models import InferenceResponse, InferenceResult
from lisa.providers.base import ChatResponse

class ResponseNormalizer:
    @staticmethod
    def normalize_chat_response(
        raw_response: ChatResponse,
        provider_id: str,
        model_name: str,
        latency_ms: float
    ) -> InferenceResult:
        """Converts diverse provider ChatResponses into a standardized InferenceResult."""
        norm_response = InferenceResponse(
            content=raw_response.content or "",
            tool_calls=raw_response.tool_calls,
            usage=raw_response.usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )
        
        return InferenceResult(
            success=True,
            response=norm_response,
            provider_id=provider_id,
            model_name=model_name,
            latency_ms=latency_ms,
            error=None
        )

    @staticmethod
    def normalize_error(
        error_message: str,
        provider_id: str,
        model_name: str,
        latency_ms: float
    ) -> InferenceResult:
        """Converts provider failures or timeouts into a standardized InferenceResult error."""
        return InferenceResult(
            success=False,
            response=None,
            provider_id=provider_id,
            model_name=model_name,
            latency_ms=latency_ms,
            error=error_message
        )
