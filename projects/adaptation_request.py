from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectAdaptationRequest:
    source_project_id: str
    target_project_id: str
    capability_query: str
