from abc import ABC, abstractmethod
from typing import List
from lisa.tools.base import BaseTool
from lisa.providers.base import BaseProvider

class BasePlugin(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        """Plugin unique ID."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin display name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version string."""
        pass

    @abstractmethod
    def get_tools(self) -> List[BaseTool]:
        """Return list of custom tools provided by this plugin."""
        return []
