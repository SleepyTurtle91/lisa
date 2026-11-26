from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProjectCompatibilityRequest:
    source_project_id: str
    target_project_id: str
    capability_query: Optional[str] = None
