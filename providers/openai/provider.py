from typing import Dict, Any, List
from lisa.core.context import Capability
from lisa.providers.base import BaseProvider
from lisa.providers.manifest import ProviderManifest
from lisa.providers.base import ChatRequest, ChatResponse

class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str = "mock-key", default_model: str = "gpt-4o"):
        self._api_key = api_key
        self._default_model = default_model

    @property
    def id(self) -> str:
        return "openai"

    @property
    def name(self) -> str:
        return "OpenAI Cloud Provider"

    async def handshake(self) -> ProviderManifest:
        healthy = await self.is_healthy()
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=healthy,
            priority=20,
            capabilities=[Capability.CHAT, Capability.TOOLS, Capability.STREAMING, Capability.JSON, Capability.VISION],
            supported_models=[self._default_model, "gpt-4o-mini"],
            configuration={"model": self._default_model}
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        last_msg = request.messages[-1]["content"] if request.messages else ""
        return ChatResponse(content=f"[OpenAI Response] Processed: {last_msg}")
