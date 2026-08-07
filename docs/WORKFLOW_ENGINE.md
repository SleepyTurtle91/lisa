# 📜 WORKFLOW ENGINE Specification (L.I.S.A. Kernel)

## Overview

Workflows in L.I.S.A. are deterministic state machines (e.g. Boot, Code, Audit, Release), not probabilistic AI prompts.

```python
class BaseWorkflow(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def execute_step(self, state: WorkflowState) -> WorkflowState: ...
```
