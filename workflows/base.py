from abc import ABC, abstractmethod
from typing import Any, Dict, List
from dataclasses import dataclass

@dataclass
class WorkflowState:
    name: str
    step_index: int
    context: Dict[str, Any]

class BaseWorkflow(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Workflow identifier (e.g. 'boot', 'review', 'code', 'audit')."""
        pass

    @abstractmethod
    async def execute_step(self, state: WorkflowState) -> WorkflowState:
        """Deterministic step execution."""
        pass
