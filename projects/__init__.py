"""Project identity, isolation, and profiling contracts for L.I.S.A."""

from lisa.projects.capability import CapabilityEvidence, CapabilityMatch
from lisa.projects.capability_discovery import CapabilityDiscoveryExecutor
from lisa.projects.capability_request import CapabilityDiscoveryRequest
from lisa.projects.capability_result import CapabilityDiscoveryResult
from lisa.projects.adaptation import AdaptationPlanStatus, AdaptationStep, ProjectAdaptationPlan
from lisa.projects.adaptation_planner import ProjectAdaptationPlanner
from lisa.projects.adaptation_request import ProjectAdaptationRequest
from lisa.projects.adaptation_result import ProjectAdaptationResult
from lisa.projects.compatibility import CompatibilityStatus, ProjectCompatibilityReport, ProjectConstraint
from lisa.projects.compatibility_executor import ProjectCompatibilityExecutor
from lisa.projects.compatibility_request import ProjectCompatibilityRequest
from lisa.projects.compatibility_result import ProjectCompatibilityResult
from lisa.projects.context import ProjectContext
from lisa.projects.executor import ProjectExecutor
from lisa.projects.manifest import ProjectManifest
from lisa.projects.profile import ProjectEvidence, ProjectProfile
from lisa.projects.profile_executor import ProjectProfileExecutor
from lisa.projects.profile_request import ProjectProfileRequest
from lisa.projects.profile_result import ProjectProfileResult
from lisa.projects.registry import ProjectRegistry
from lisa.projects.request import ProjectOperation, ProjectRequest
from lisa.projects.resolver import ProjectResolver
from lisa.projects.result import ProjectResult
from lisa.projects.state import ProjectState

__all__ = [
    "AdaptationPlanStatus", "AdaptationStep", "ProjectAdaptationPlan",
    "ProjectAdaptationPlanner", "ProjectAdaptationRequest", "ProjectAdaptationResult",
    "CapabilityDiscoveryExecutor", "CapabilityDiscoveryRequest",
    "CapabilityDiscoveryResult", "CapabilityEvidence", "CapabilityMatch",
    "CompatibilityStatus", "ProjectCompatibilityExecutor",
    "ProjectCompatibilityReport", "ProjectCompatibilityRequest",
    "ProjectCompatibilityResult", "ProjectConstraint",
    "ProjectContext", "ProjectEvidence", "ProjectExecutor", "ProjectManifest",
    "ProjectOperation", "ProjectProfile", "ProjectProfileExecutor",
    "ProjectProfileRequest", "ProjectProfileResult", "ProjectRegistry",
    "ProjectRequest", "ProjectResolver", "ProjectResult", "ProjectState",
]
