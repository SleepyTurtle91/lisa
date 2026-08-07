import time
import logging
from typing import Dict, Any, Optional
from lisa.engine.models import InferenceRequest, InferenceResult
from lisa.engine.normalizer import ResponseNormalizer
from lisa.providers.selector import ProviderSelector
from lisa.providers.base import ChatRequest
from lisa.core.errors import ProviderError

logger = logging.getLogger(__name__)

class InferenceEngine:
    def __init__(self, selector: ProviderSelector, max_retries: int = 1):
        self._selector = selector
        self._max_retries = max_retries

    async def execute(self, request: InferenceRequest, preferred_provider_id: Optional[str] = None) -> InferenceResult:
        """Executes inference via selected provider with normalization & 1-shot retry."""
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
            tools=request.tools,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        last_error = None
        for attempt in range(self._max_retries + 1):
            attempt_start = time.perf_counter()
            try:
                raw_resp = await provider.chat(chat_req)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                manifest = await provider.handshake()
                model_name = manifest.supported_models[0] if manifest.supported_models else "default"
                return ResponseNormalizer.normalize_chat_response(
                    raw_response=raw_resp,
                    provider_id=provider.id,
                    model_name=model_name,
                    latency_ms=elapsed_ms
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Inference attempt {attempt + 1}/{self._max_retries + 1} failed on provider '{provider.id}': {str(e)}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        manifest = await provider.handshake() if provider else None
        model_name = manifest.supported_models[0] if manifest and manifest.supported_models else "unknown"
        return ResponseNormalizer.normalize_error(
            error_message=f"Inference execution failed after {self._max_retries + 1} attempts: {last_error}",
            provider_id=provider.id if provider else "unknown",
            model_name=model_name,
            latency_ms=elapsed_ms
        )
