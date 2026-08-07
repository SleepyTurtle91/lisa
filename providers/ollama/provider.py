from typing import Dict, Any, List
from lisa.core.context import Capability
from lisa.providers.base import BaseProvider
from lisa.providers.manifest import ProviderManifest
from lisa.providers.base import ChatRequest, ChatResponse

class OllamaProvider(BaseProvider):
    def __init__(self, host: str = "http://localhost:11434", default_model: str = "qwen3:4b"):
        self._host = host
        self._default_model = default_model

    @property
    def id(self) -> str:
        return "ollama"

    @property
    def name(self) -> str:
        return "Ollama Local Provider"

    async def handshake(self) -> ProviderManifest:
        healthy = await self.is_healthy()
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="0.3.0",
            healthy=healthy,
            priority=10,
            capabilities=[Capability.CHAT, Capability.TOOLS, Capability.STREAMING, Capability.JSON],
            supported_models=[self._default_model, "llama3.2:latest"],
            configuration={"host": self._host}
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        last_msg = request.messages[-1]["content"] if request.messages else ""
        return ChatResponse(content=f"[Ollama Response] Processed: {last_msg}")
