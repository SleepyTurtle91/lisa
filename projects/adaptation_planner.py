import hashlib

from lisa.projects.adaptation import (
    AdaptationPlanStatus,
    AdaptationStep,
    ProjectAdaptationPlan,
)
from lisa.projects.adaptation_request import ProjectAdaptationRequest
from lisa.projects.adaptation_result import ProjectAdaptationResult
from lisa.projects.compatibility import CompatibilityStatus
from lisa.projects.compatibility_executor import ProjectCompatibilityExecutor
from lisa.projects.compatibility_request import ProjectCompatibilityRequest
from lisa.projects.registry import ProjectRegistry


class ProjectAdaptationPlanner:
    """Creates a review-only plan. It has no filesystem write or execution path."""

    def __init__(self, registry=None, compatibility_executor=None):
        self._registry = registry or ProjectRegistry()
        self._compatibility = compatibility_executor or ProjectCompatibilityExecutor(
            registry=self._registry
        )

    def execute(self, request: ProjectAdaptationRequest) -> ProjectAdaptationResult:
        if not isinstance(request, ProjectAdaptationRequest):
            return ProjectAdaptationResult(
                success=False, error="A valid ProjectAdaptationRequest is required."
            )
        if not isinstance(request.capability_query, str) or not request.capability_query.strip():
            return ProjectAdaptationResult(
                success=False, error="A non-empty capability query is required."
            )

        compared = self._compatibility.execute(ProjectCompatibilityRequest(
            source_project_id=request.source_project_id,
            target_project_id=request.target_project_id,
            capability_query=request.capability_query,
        ))
        if not compared.success:
            return ProjectAdaptationResult(success=False, error=compared.error)

        report = compared.report
        blockers = []
        if report.status == CompatibilityStatus.INSUFFICIENT_EVIDENCE:
            blockers.extend(report.risk_flags)
        if report.source_capability_found is False:
            blockers.append("Source capability evidence must be located before an adaptation plan can be approved.")
        if not any(item.project_role == "target" for item in report.constraints):
            blockers.append(
                "No explicit target architecture/business-rule constraints were extracted; inspect and document target constraints before approval."
            )

        status = AdaptationPlanStatus.BLOCKED if blockers else AdaptationPlanStatus.READY_FOR_REVIEW
        source_manifest = self._registry.get(report.source_project_id)
        target_manifest = self._registry.get(report.target_project_id)
        identity = "|".join((
            report.source_project_id,
            report.target_project_id,
            request.capability_query.strip().casefold(),
        ))
        plan_id = "plan_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]

        steps = (
            AdaptationStep(
                1,
                "Verify the source capability",
                "Open the referenced source documentation, implementation paths, and tests. Confirm the actual behavior and business rules.",
            ),
            AdaptationStep(
                2,
                "Map target architecture boundaries",
                "Review every target constraint listed in this plan. Identify the target module, domain, repository, and service boundaries that must remain authoritative.",
            ),
            AdaptationStep(
                3,
                "Compare data and persistence contracts",
                "Map source entities, identifiers, financial precision, transactions, persistence, synchronization, and error semantics to target equivalents. Record unresolved differences as blockers.",
            ),
            AdaptationStep(
                4,
                "Design a target-native adaptation",
                "Prefer a target-owned domain contract and adapter. Do not transplant source UI, storage, or framework assumptions without explicit compatibility evidence.",
            ),
            AdaptationStep(
                5,
                "Define regression coverage",
                "Specify unit, integration, migration, offline/online, and end-to-end tests that prove the target behavior remains intact.",
            ),
            AdaptationStep(
                6,
                "Request operator authorization",
                "Present the final file scope, implementation plan, risks, and test strategy. No target changes are permitted until the operator explicitly approves a separate execution request.",
            ),
        )

        if status == AdaptationPlanStatus.BLOCKED:
            summary = "Planning is blocked because the available project evidence is insufficient. Resolve the blockers before proposing implementation."
        elif report.status == CompatibilityStatus.ADAPTATION_REQUIRED:
            summary = "A candidate capability was found, but no shared technology markers were detected. Treat this as a porting/adaptation project, not code reuse."
        else:
            summary = "A candidate capability and shared technology markers were found. This is a reviewable proposal, not permission to copy or modify code."

        plan = ProjectAdaptationPlan(
            plan_id=plan_id,
            source_project_id=source_manifest.project_id,
            source_project_name=source_manifest.name,
            target_project_id=target_manifest.project_id,
            target_project_name=target_manifest.name,
            capability_query=request.capability_query.strip(),
            status=status,
            summary=summary,
            source_evidence=report.source_evidence,
            source_paths=report.source_paths,
            target_constraints=tuple(
                item for item in report.constraints if item.project_role == "target"
            ),
            steps=steps,
            blockers=tuple(blockers),
            authorization_required=True,
            execution_authorized=False,
        )
        return ProjectAdaptationResult(success=True, plan=plan)
