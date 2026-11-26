from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProjectOperation(Enum):
    REGISTER = "register"
    LIST = "list"
    GET = "get"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    UNREGISTER = "unregister"


@dataclass(frozen=True)
class ProjectRequest:
    operation: ProjectOperation
    path: Optional[str] = None
    project_id: Optional[str] = None
