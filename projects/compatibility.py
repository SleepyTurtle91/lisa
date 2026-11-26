from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from lisa.projects.capability import CapabilityEvidence


class CompatibilityStatus(Enum):
    POTENTIAL_REUSE = "potential_reuse"
    ADAPTATION_REQUIRED = "adaptation_required"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class ProjectConstraint:
    project_role: str
    relative_path: str
    sha256: str
    excerpt: str


@dataclass(frozen=True)
class ProjectCompatibilityReport:
    source_project_id: str
    source_project_name: str
    target_project_id: str
    target_project_name: str
    status: CompatibilityStatus
    shared_technologies: Tuple[str, ...]
    source_only_technologies: Tuple[str, ...]
    target_only_technologies: Tuple[str, ...]
    capability_query: Optional[str]
    source_capability_found: Optional[bool]
    matched_terms: Tuple[str, ...]
    source_evidence: Tuple[CapabilityEvidence, ...]
    source_paths: Tuple[str, ...]
    constraints: Tuple[ProjectConstraint, ...]
    risk_flags: Tuple[str, ...]
    notes: Tuple[str, ...]
