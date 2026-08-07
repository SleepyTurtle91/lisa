from typing import Dict, Any
from lisa.core.states import RuntimeState
from lisa.core.events import EventBus, Event
from lisa.core.context import SessionContext
from lisa.core.errors import ProviderError, SessionError
from lisa.runtime.session import LisaSession
from lisa.providers.base import BaseProvider
from lisa.providers.manifest import ProviderManifest
from lisa.providers.registry import ProviderRegistry
from lisa.providers.selector import ProviderSelector
from lisa.engine.inference import InferenceEngine
from lisa.tools.registry import ToolRegistry

class LisaRuntime:
    def __init__(self):
        self._state = RuntimeState.UNINITIALIZED
        self._event_bus = EventBus()
        self._tool_registry = ToolRegistry()
        self._provider_registry = ProviderRegistry()
        self._provider_selector = ProviderSelector(self._provider_registry)
        self._engine = InferenceEngine(self._provider_selector)

    @property
    def state(self) -> RuntimeState:
        return self._state

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    @property
    def provider_registry(self) -> ProviderRegistry:
        return self._provider_registry

    @property
    def provider_selector(self) -> ProviderSelector:
        return self._provider_selector

    @property
    def engine(self) -> InferenceEngine:
        return self._engine

    async def initialize(self) -> None:
        """Start kernel lifecycle and publish initialization event."""
        self._state = RuntimeState.INITIALIZING
        self._event_bus.publish(Event(name="BOOT_STARTED", payload={}))
        self._state = RuntimeState.READY
        self._event_bus.publish(Event(name="BOOT_FINISHED", payload={"status": "OK"}))

    async def register_provider(self, provider: BaseProvider) -> ProviderManifest:
        """Execute handshake and register provider in ProviderRegistry."""
        try:
            manifest = await self._provider_registry.register(provider)
            self._event_bus.publish(Event(name="PROVIDER_REGISTERED", payload={"provider_id": provider.id}))
            return manifest
        except Exception as e:
            self._event_bus.publish(Event(name="PROVIDER_FAILED", payload={"provider_id": provider.id, "error": str(e)}))
            raise ProviderError(f"Handshake failed for provider '{provider.id}': {str(e)}") from e

    def create_session(self, context: SessionContext) -> LisaSession:
        if self._state != RuntimeState.READY and self._state != RuntimeState.BUSY:
            raise SessionError("LisaRuntime must be in READY state to create sessions.")
            
        session = LisaSession(context, self._engine, self._tool_registry)
        self._event_bus.publish(Event(name="SESSION_CREATED", payload={"session_id": session.session_id}))
        return session

    def health(self) -> Dict[str, Any]:
        """System health API returning runtime status and provider manifests."""
        return {
            "status": "healthy" if self._state == RuntimeState.READY else "degraded",
            "runtime_state": self._state.name,
            "providers": [
                {
                    "id": m.id,
                    "version": m.version,
                    "healthy": m.healthy,
                    "capabilities": [c.name for c in m.capabilities]
                }
                for m in self._provider_registry.list_manifests()
            ],
            "tools": [t.name for t in self._tool_registry.list_tools()]
        }

    async def shutdown(self) -> None:
        """Gracefully release runtime resources and signal shutdown."""
        self._state = RuntimeState.SHUTTING_DOWN
        self._event_bus.publish(Event(name="RUNTIME_SHUTDOWN", payload={"status": "OK"}))
        self._state = RuntimeState.UNINITIALIZED
