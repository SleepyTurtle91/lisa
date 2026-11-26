from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ProjectManifest:
    """Evidence-backed identity for one locally registered project."""

    project_id: str
    name: str
    root_path: str
    markers: Tuple[str, ...]
    capabilities: Tuple[str, ...]
