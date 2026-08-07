import json
import urllib.request
import urllib.error
from typing import Dict, Any, List
from lisa.core.context import Capability
from lisa.providers.base import BaseProvider
from lisa.providers.manifest import ProviderManifest
from lisa.providers.base import ChatRequest, ChatResponse
from lisa.core.errors import ProviderError

class OllamaProvider(BaseProvider):
    def __init__(self, host: str = "http://localhost:11434", default_model: str = "qwen3:4b", timeout_seconds: float = 300.0):
        self._host = host.rstrip("/")
        self._default_model = default_model
        self._timeout_seconds = timeout_seconds

    @property
    def id(self) -> str:
        return "ollama"

    @property
    def name(self) -> str:
        return "Ollama Local Provider"

    async def handshake(self) -> ProviderManifest:
        healthy = await self.is_healthy()
        models = self._list_models() if healthy else [self._default_model]
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="0.3.0",
            healthy=healthy,
            priority=10,
            capabilities=[Capability.CHAT, Capability.TOOLS, Capability.STREAMING, Capability.JSON],
            supported_models=models,
            configuration={"host": self._host}
        )

    async def is_healthy(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _list_models(self) -> List[str]:
        try:
            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return [self._default_model]

    async def chat(self, request: ChatRequest) -> ChatResponse:
        url = f"{self._host}/api/chat"
        payload = {
            "model": request.model if request.model else self._default_model,
            "messages": request.messages,
            "stream": False,
            "options": {
                "temperature": request.temperature
            }
        }
        if request.tools:
            payload["tools"] = request.tools

        body_bytes = json.dumps(payload).encode("utf-8")
        http_req = urllib.request.Request(
            url,
            data=body_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(http_req, timeout=self._timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg = data.get("message", {})
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls")
                
                eval_count = data.get("eval_count", 0)
                prompt_eval_count = data.get("prompt_eval_count", 0)
                usage = {
                    "prompt_tokens": prompt_eval_count,
                    "completion_tokens": eval_count,
                    "total_tokens": prompt_eval_count + eval_count
                }
                
                return ChatResponse(
                    content=content,
                    tool_calls=tool_calls,
                    usage=usage
                )
        except Exception as e:
            raise ProviderError(f"Ollama API chat failure: {str(e)}") from e
