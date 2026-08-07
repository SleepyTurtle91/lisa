# 📜 PLUGIN API Specification (L.I.S.A. Kernel)

## Overview

The `BasePlugin` interface allows extending the runtime with domain tools, workflows, and prompts without mutating core code.

```python
class BasePlugin(ABC):
    @property
    @abstractmethod
    def id(self) -> str: ...

    @abstractmethod
    def get_tools(self) -> List[BaseTool]: ...
```
