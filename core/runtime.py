from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class SessionConfig:
    project_path: str
    provider_id: str
    active_workflow: str = "default"

class BaseSession(ABC):
    @property
    @abstractmethod
    def session_id(self) -> str:
        pass

    @abstractmethod
    async def send_message(self, message: str) -> str:
        pass

class BaseRuntime(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Deterministic startup and discovery sequence."""
        pass

    @abstractmethod
    async def create_session(self, config: SessionConfig) -> BaseSession:
        """Create and register a new execution session."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully release resources, providers, and state."""
        pass
