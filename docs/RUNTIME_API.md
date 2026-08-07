# 📜 RUNTIME API Specification (L.I.S.A. Kernel)

## Overview

The `Runtime` contract governs the core lifecycle, dependency injection, session creation, and shutdown sequences of the L.I.S.A. platform.

```python
class BaseRuntime(ABC):
    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def create_session(self, config: SessionConfig) -> BaseSession: ...

    @abstractmethod
    async def shutdown(self) -> None: ...
```
