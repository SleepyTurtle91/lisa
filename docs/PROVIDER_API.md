# 📜 PROVIDER API Specification (L.I.S.A. Kernel)

## Overview

The `BaseProvider` interface handles model inference execution in total isolation from tools, workflows, or runtime states.

```python
class BaseProvider(ABC):
    @property
    @abstractmethod
    def id(self) -> str: ...

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse: ...

    @abstractmethod
    async def is_healthy(self) -> bool: ...
```
