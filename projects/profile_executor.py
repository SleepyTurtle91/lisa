from lisa.projects.indexer import ProjectProfileIndexer
from lisa.projects.profile_request import ProjectProfileRequest
from lisa.projects.profile_result import ProjectProfileResult
from lisa.projects.registry import ProjectRegistry


class ProjectProfileExecutor:
    """Request/result boundary for read-only project profiling."""

    def __init__(self, registry=None, indexer=None):
        self._registry = registry or ProjectRegistry()
        self._indexer = indexer or ProjectProfileIndexer()

    def execute(self, request: ProjectProfileRequest) -> ProjectProfileResult:
        if not isinstance(request, ProjectProfileRequest):
            return ProjectProfileResult(
                success=False, error="A valid ProjectProfileRequest is required."
            )
        if not isinstance(request.project_id, str) or not request.project_id.strip():
            return ProjectProfileResult(success=False, error="A project ID is required.")
        if not 1 <= request.max_evidence_files <= 256:
            return ProjectProfileResult(success=False, error="max_evidence_files must be between 1 and 256.")
        if not 1024 <= request.max_bytes_per_file <= 1048576:
            return ProjectProfileResult(success=False, error="max_bytes_per_file must be between 1024 and 1048576.")
        if not 0 <= request.max_source_files <= 10000:
            return ProjectProfileResult(success=False, error="max_source_files must be between 0 and 10000.")

        manifest = self._registry.get(request.project_id)
        if manifest is None:
            return ProjectProfileResult(
                success=False,
                error=f"Project is not registered: {request.project_id}",
            )
        try:
            profile = self._indexer.index(
                manifest,
                max_evidence_files=request.max_evidence_files,
                max_bytes_per_file=request.max_bytes_per_file,
                max_source_files=request.max_source_files,
            )
            return ProjectProfileResult(success=True, profile=profile)
        except (OSError, RuntimeError, ValueError) as exc:
            return ProjectProfileResult(success=False, error=str(exc))
