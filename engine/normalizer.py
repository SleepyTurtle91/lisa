from typing import Dict, Any, Optional, List
from lisa.engine.models import InferenceResponse, InferenceResult, ExecutionTelemetry
from lisa.providers.base import ChatResponse

class ResponseNormalizer:
    @staticmethod
    def normalize_chat_response(
        raw_response: ChatResponse,
        provider_id: str,
        model_name: str,
        latency_ms: float,
        telemetry: Optional[ExecutionTelemetry] = None
    ) -> InferenceResult:
        """Converts diverse provider ChatResponses into a standardized InferenceResult with Telemetry."""
        usage = raw_response.usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        norm_response = InferenceResponse(
            content=raw_response.content or "",
            tool_calls=raw_response.tool_calls,
            usage=usage
        )

        final_telemetry = telemetry or ExecutionTelemetry(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            tool_calls_count=len(raw_response.tool_calls) if raw_response.tool_calls else 0
        )
        
        return InferenceResult(
            success=True,
            response=norm_response,
            provider_id=provider_id,
            model_name=model_name,
            latency_ms=latency_ms,
            telemetry=final_telemetry,
            error=None
        )

    @staticmethod
    def normalize_error(
        error_message: str,
        provider_id: str,
        model_name: str,
        latency_ms: float,
        telemetry: Optional[ExecutionTelemetry] = None
    ) -> InferenceResult:
        """Converts provider failures or timeouts into a standardized InferenceResult error."""
        return InferenceResult(
            success=False,
            response=None,
            provider_id=provider_id,
            model_name=model_name,
            latency_ms=latency_ms,
            telemetry=telemetry or ExecutionTelemetry(),
            error=error_message
        )
