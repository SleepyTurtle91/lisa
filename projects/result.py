from dataclasses import dataclass
from typing import Optional, Tuple

from lisa.projects.context import ProjectContext
from lisa.projects.manifest import ProjectManifest


@dataclass(frozen=True)
class ProjectResult:
    success: bool
    manifest: Optional[ProjectManifest] = None
    manifests: Tuple[ProjectManifest, ...] = ()
    context: Optional[ProjectContext] = None
    error: Optional[str] = None
