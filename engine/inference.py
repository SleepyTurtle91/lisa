import time
import logging
from typing import Dict, Any, Optional
from lisa.engine.models import InferenceRequest, InferenceResult, ExecutionTelemetry
from lisa.engine.normalizer import ResponseNormalizer
from lisa.providers.selector import ProviderSelector
from lisa.providers.base import ChatRequest
from lisa.core.errors import ProviderError
from lisa.telemetry.flight_recorder import FlightRecorder

logger = logging.getLogger(__name__)

class InferenceEngine:
    def __init__(self, selector: ProviderSelector, max_retries: int = 1, flight_recorder: Optional[FlightRecorder] = None):
        self._selector = selector
        self._max_retries = max_retries
        self._flight_recorder = flight_recorder

    async def execute(self, request: InferenceRequest, preferred_provider_id: Optional[str] = None) -> InferenceResult:
        """Executes inference via selected provider with normalization, retries, and telemetry recording."""
        start_time = time.perf_counter()
        
        try:
            provider = self._selector.select(
                required_capabilities=request.requested_capabilities,
                preferred_id=preferred_provider_id
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ResponseNormalizer.normalize_error(
                error_message=f"Provider Selection Failed: {str(e)}",
                provider_id=preferred_provider_id or "unknown",
                model_name="unknown",
                latency_ms=elapsed_ms
            )

        chat_req = ChatRequest(
            messages=request.messages,
            model=request.model_name,
            tools=request.tools,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        if self._flight_recorder is not None:
            self._flight_recorder.record_event("model_request", {
                "provider_id": provider.id,
                "model_name": request.model_name,
                "messages": request.messages,
                "tools": request.tools,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            })

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                raw_resp = await provider.chat(chat_req)
                if self._flight_recorder is not None:
                    self._flight_recorder.record_event("model_response", {
                        "provider_id": provider.id,
                        "model_name": request.model_name,
                        "content": getattr(raw_resp, "content", None),
                        "tool_calls": getattr(raw_resp, "tool_calls", None),
                        "usage": getattr(raw_resp, "usage", None),
                    })
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                manifest = await provider.handshake()
                model_name = request.model_name or (manifest.supported_models[0] if manifest.supported_models else "default")
                
                usage = raw_resp.usage or {}
                telemetry = ExecutionTelemetry(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    tool_calls_count=len(raw_resp.tool_calls) if raw_resp.tool_calls else 0,
                    tools_exposed_count=len(request.tools) if request.tools else 0,
                    retries_count=attempt
                )

                return ResponseNormalizer.normalize_chat_response(
                    raw_response=raw_resp,
                    provider_id=provider.id,
                    model_name=model_name,
                    latency_ms=elapsed_ms,
                    telemetry=telemetry
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Inference attempt {attempt + 1}/{self._max_retries + 1} failed on provider '{provider.id}': {str(e)}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        manifest = await provider.handshake() if provider else None
        model_name = request.model_name or (manifest.supported_models[0] if manifest and manifest.supported_models else "unknown")
        
        telemetry = ExecutionTelemetry(
            tools_exposed_count=len(request.tools) if request.tools else 0,
            retries_count=self._max_retries
        )

        return ResponseNormalizer.normalize_error(
            error_message=f"Inference execution failed after {self._max_retries + 1} attempts: {last_error}",
            provider_id=provider.id if provider else "unknown",
            model_name=model_name,
            latency_ms=elapsed_ms,
            telemetry=telemetry
        )
