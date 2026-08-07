from typing import List, Optional
from lisa.core.context import Capability
from lisa.providers.base import BaseProvider
from lisa.providers.registry import ProviderRegistry
from lisa.core.errors import ProviderError

class ProviderSelector:
    def __init__(self, registry: ProviderRegistry):
        self._registry = registry

    def select(self, required_capabilities: List[Capability], preferred_id: Optional[str] = None) -> BaseProvider:
        # 1. If explicit preferred_id requested, check capability & health
        if preferred_id:
            provider = self._registry.get_provider(preferred_id)
            manifest = self._registry.get_manifest(preferred_id)
            if provider and manifest and manifest.healthy:
                if all(cap in manifest.capabilities for cap in required_capabilities):
                    return provider
                raise ProviderError(f"Requested provider '{preferred_id}' lacks required capabilities.")

        # 2. Filter candidates matching ALL requested capabilities & healthy status
        candidates = []
        for manifest in self._registry.list_manifests():
            if manifest.healthy and all(cap in manifest.capabilities for cap in required_capabilities):
                provider = self._registry.get_provider(manifest.id)
                if provider:
                    candidates.append((manifest.priority, provider))

        if not candidates:
            req_str = [c.name for c in required_capabilities]
            raise ProviderError(f"No healthy provider available matching capabilities: {req_str}")

        # 3. Sort by priority (lowest priority number = highest preference)
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
