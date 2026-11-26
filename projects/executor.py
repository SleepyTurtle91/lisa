from lisa.projects.registry import ProjectRegistry
from lisa.projects.request import ProjectOperation, ProjectRequest
from lisa.projects.resolver import ProjectResolver
from lisa.projects.result import ProjectResult


class ProjectExecutor:
    """The sole request/result boundary for project registry operations."""

    def __init__(self, registry=None, resolver=None):
        self._registry = registry or ProjectRegistry()
        self._resolver = resolver or ProjectResolver()

    def execute(self, request: ProjectRequest) -> ProjectResult:
        if not isinstance(request, ProjectRequest):
            return ProjectResult(success=False, error="A valid ProjectRequest is required.")
        try:
            if request.operation == ProjectOperation.REGISTER:
                manifest = self._resolver.resolve(request.path)
                manifest = self._registry.register(manifest)
                return ProjectResult(success=True, manifest=manifest)

            if request.operation == ProjectOperation.LIST:
                return ProjectResult(
                    success=True,
                    manifests=tuple(self._registry.list_manifests()),
                    context=self._registry.active_context(),
                )

            if request.operation == ProjectOperation.GET:
                manifest = self._registry.get(request.project_id or "")
                if manifest is None:
                    return ProjectResult(
                        success=False,
                        error=f"Project is not registered: {request.project_id}",
                    )
                return ProjectResult(success=True, manifest=manifest)

            if request.operation == ProjectOperation.ACTIVATE:
                context = self._registry.activate(request.project_id or "")
                return ProjectResult(
                    success=True,
                    manifest=self._registry.get(context.project_id),
                    context=context,
                )

            if request.operation == ProjectOperation.DEACTIVATE:
                self._registry.deactivate()
                return ProjectResult(success=True)

            if request.operation == ProjectOperation.UNREGISTER:
                if not self._registry.unregister(request.project_id or ""):
                    return ProjectResult(
                        success=False,
                        error=f"Project is not registered: {request.project_id}",
                    )
                return ProjectResult(success=True)

            return ProjectResult(success=False, error="Unsupported project operation.")
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            return ProjectResult(success=False, error=str(exc))
