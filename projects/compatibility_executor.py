import re
from typing import List, Tuple

from lisa.projects.capability_discovery import CapabilityDiscoveryExecutor
from lisa.projects.capability_request import CapabilityDiscoveryRequest
from lisa.projects.compatibility import (
    CompatibilityStatus,
    ProjectCompatibilityReport,
    ProjectConstraint,
)
from lisa.projects.compatibility_request import ProjectCompatibilityRequest
from lisa.projects.compatibility_result import ProjectCompatibilityResult
from lisa.projects.profile_executor import ProjectProfileExecutor
from lisa.projects.profile_request import ProjectProfileRequest
from lisa.projects.registry import ProjectRegistry


class ProjectCompatibilityExecutor:
    """Evidence-bounded compatibility triage; never authorizes code changes."""

    CONSTRAINT_PATTERN = re.compile(
        r"\b(must not|must|never|shall|should|required|forbidden|do not|cannot|"
        r"offline[- ]first|bigdecimal|decimal|float|double|room|sqlite|dependency)\b",
        re.IGNORECASE,
    )

    def __init__(self, registry=None, profile_executor=None, discovery_executor=None):
        self._registry = registry or ProjectRegistry()
        self._profiles = profile_executor or ProjectProfileExecutor(registry=self._registry)
        self._discovery = discovery_executor or CapabilityDiscoveryExecutor(registry=self._registry)

    @classmethod
    def _constraints(cls, profile, role: str) -> Tuple[ProjectConstraint, ...]:
        found: List[ProjectConstraint] = []
        seen = set()
        for evidence in profile.evidence:
            for line in evidence.excerpt.splitlines():
                candidate = line.strip()
                if not candidate or not cls.CONSTRAINT_PATTERN.search(candidate):
                    continue
                key = (evidence.relative_path, candidate)
                if key in seen:
                    continue
                seen.add(key)
                found.append(ProjectConstraint(
                    project_role=role,
                    relative_path=evidence.relative_path,
                    sha256=evidence.sha256,
                    excerpt=candidate[:400],
                ))
                if len(found) >= 100:
                    return tuple(found)
        return tuple(found)

    def execute(self, request: ProjectCompatibilityRequest) -> ProjectCompatibilityResult:
        if not isinstance(request, ProjectCompatibilityRequest):
            return ProjectCompatibilityResult(
                success=False, error="A valid ProjectCompatibilityRequest is required."
            )
        if not isinstance(request.source_project_id, str) or not request.source_project_id.strip():
            return ProjectCompatibilityResult(success=False, error="A source project ID is required.")
        if not isinstance(request.target_project_id, str) or not request.target_project_id.strip():
            return ProjectCompatibilityResult(success=False, error="A target project ID is required.")
        if request.capability_query is not None and (
            not isinstance(request.capability_query, str)
            or not request.capability_query.strip()
        ):
            return ProjectCompatibilityResult(
                success=False, error="capability_query must be non-empty when supplied."
            )
        if request.source_project_id == request.target_project_id:
            return ProjectCompatibilityResult(
                success=False, error="Source and target projects must be different."
            )

        source_manifest = self._registry.get(request.source_project_id)
        target_manifest = self._registry.get(request.target_project_id)
        if source_manifest is None or target_manifest is None:
            missing = []
            if source_manifest is None:
                missing.append(request.source_project_id)
            if target_manifest is None:
                missing.append(request.target_project_id)
            return ProjectCompatibilityResult(
                success=False,
                error=f"Projects are not registered: {', '.join(missing)}",
            )

        source_result = self._profiles.execute(
            ProjectProfileRequest(project_id=source_manifest.project_id)
        )
        target_result = self._profiles.execute(
            ProjectProfileRequest(project_id=target_manifest.project_id)
        )
        if not source_result.success:
            return ProjectCompatibilityResult(success=False, error=f"Source profile failed: {source_result.error}")
        if not target_result.success:
            return ProjectCompatibilityResult(success=False, error=f"Target profile failed: {target_result.error}")

        source = source_result.profile
        target = target_result.profile
        source_tech = set(source.technologies)
        target_tech = set(target.technologies)
        shared = tuple(sorted(source_tech & target_tech))
        source_only = tuple(sorted(source_tech - target_tech))
        target_only = tuple(sorted(target_tech - source_tech))

        capability_found = None
        matched_terms = ()
        source_evidence = ()
        source_paths = ()
        if request.capability_query and request.capability_query.strip():
            discovery = self._discovery.execute(CapabilityDiscoveryRequest(
                query=request.capability_query,
                project_ids=(source_manifest.project_id,),
            ))
            if not discovery.success:
                return ProjectCompatibilityResult(success=False, error=discovery.error)
            capability_found = bool(discovery.matches)
            if discovery.matches:
                candidate = discovery.matches[0]
                matched_terms = candidate.matched_terms
                source_evidence = candidate.evidence
                source_paths = candidate.source_paths

        constraints = (
            self._constraints(source, "source")
            + self._constraints(target, "target")
        )
        risk_flags = []
        notes = [
            "This is a preliminary evidence-based triage, not proof of implementation compatibility.",
            "Source code contents were not read; only project documentation, build descriptors, and file paths were inspected.",
            "No files were copied, modified, or executed.",
        ]

        if not source_tech or not target_tech:
            status = CompatibilityStatus.INSUFFICIENT_EVIDENCE
            risk_flags.append("One or both projects have insufficient technology markers.")
        elif shared:
            status = CompatibilityStatus.POTENTIAL_REUSE
            notes.append(f"Shared technology markers: {', '.join(shared)}.")
        else:
            status = CompatibilityStatus.ADAPTATION_REQUIRED
            risk_flags.append("No shared technology markers were detected; porting or an adapter may be required.")

        if capability_found is False:
            status = CompatibilityStatus.INSUFFICIENT_EVIDENCE
            risk_flags.append("The requested capability was not located in the source project's indexed evidence.")
        elif capability_found is True:
            notes.append("The requested capability has matching source-project evidence; inspect the referenced files before reuse.")

        if constraints:
            risk_flags.append("Architecture and business-rule constraints were found and must be reviewed before adaptation.")
        else:
            risk_flags.append("No explicit architecture constraints were extracted; absence of evidence is not evidence of absence.")

        report = ProjectCompatibilityReport(
            source_project_id=source.project_id,
            source_project_name=source.name,
            target_project_id=target.project_id,
            target_project_name=target.name,
            status=status,
            shared_technologies=shared,
            source_only_technologies=source_only,
            target_only_technologies=target_only,
            capability_query=request.capability_query,
            source_capability_found=capability_found,
            matched_terms=matched_terms,
            source_evidence=source_evidence,
            source_paths=source_paths,
            constraints=constraints,
            risk_flags=tuple(risk_flags),
            notes=tuple(notes),
        )
        return ProjectCompatibilityResult(success=True, report=report)
