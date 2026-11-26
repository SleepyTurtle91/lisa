from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from lisa.projects.compatibility import ProjectConstraint
from lisa.projects.capability import CapabilityEvidence
from lisa.projects.compatibility import CompatibilityStatus


class AdaptationPlanStatus(Enum):
    BLOCKED = "blocked"
    READY_FOR_REVIEW = "ready_for_review"


@dataclass(frozen=True)
class AdaptationStep:
    order: int
    title: str
    description: str


@dataclass(frozen=True)
class ProjectAdaptationPlan:
    plan_id: str
    source_project_id: str
    source_project_name: str
    target_project_id: str
    target_project_name: str
    capability_query: str
    status: AdaptationPlanStatus
    compatibility_status: CompatibilityStatus
    shared_technologies: Tuple[str, ...]
    summary: str
    source_evidence: Tuple[CapabilityEvidence, ...]
    source_paths: Tuple[str, ...]
    target_constraints: Tuple[ProjectConstraint, ...]
    steps: Tuple[AdaptationStep, ...]
    blockers: Tuple[str, ...]
    authorization_required: bool
    execution_authorized: bool
