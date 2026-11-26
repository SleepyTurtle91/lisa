from dataclasses import dataclass
from typing import Optional

from lisa.projects.compatibility import ProjectCompatibilityReport


@dataclass(frozen=True)
class ProjectCompatibilityResult:
    success: bool
    report: Optional[ProjectCompatibilityReport] = None
    error: Optional[str] = None
