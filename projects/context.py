from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectContext:
    """Immutable scope for an operation against exactly one project."""

    project_id: str
    root_path: str
