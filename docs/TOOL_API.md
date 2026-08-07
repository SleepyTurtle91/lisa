# 📜 TOOL API Specification (L.I.S.A. Kernel)

## Overview

The `BaseTool` contract defines executable actions exposed to the runtime and provider.

```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]: ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult: ...
```
