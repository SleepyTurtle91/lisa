from typing import Dict, List, Optional
from lisa.providers.base import BaseProvider
from lisa.providers.manifest import ProviderManifest
from lisa.core.errors import ProviderError

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._manifests: Dict[str, ProviderManifest] = {}

    async def register(self, provider: BaseProvider) -> ProviderManifest:
        manifest = await provider.handshake()
        if not manifest.healthy:
            raise ProviderError(f"Provider '{provider.id}' reported unhealthy manifest.")
        if provider.id in self._providers or provider.id in self._manifests:
            raise ProviderError(f"Provider '{provider.id}' is already registered.")
        self._providers[provider.id] = provider
        self._manifests[provider.id] = manifest
        return manifest

    def get_provider(self, provider_id: str) -> Optional[BaseProvider]:
        return self._providers.get(provider_id)

    def get_manifest(self, provider_id: str) -> Optional[ProviderManifest]:
        return self._manifests.get(provider_id)

    def list_manifests(self) -> List[ProviderManifest]:
        return list(self._manifests.values())

    def list_providers(self) -> List[BaseProvider]:
        return list(self._providers.values())
