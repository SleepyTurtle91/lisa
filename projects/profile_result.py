from dataclasses import dataclass
from typing import Optional

from lisa.projects.profile import ProjectProfile


@dataclass(frozen=True)
class ProjectProfileResult:
    success: bool
    profile: Optional[ProjectProfile] = None
    error: Optional[str] = None
