from dataclasses import dataclass
from typing import Optional

from lisa.projects.adaptation import ProjectAdaptationPlan


@dataclass(frozen=True)
class ProjectAdaptationResult:
    success: bool
    plan: Optional[ProjectAdaptationPlan] = None
    error: Optional[str] = None
