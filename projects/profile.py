from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ProjectEvidence:
    """A bounded, content-hashed excerpt from one inspected project file."""

    relative_path: str
    evidence_kind: str
    sha256: str
    bytes_inspected: int
    excerpt: str
    truncated: bool
    redactions_applied: bool = False


@dataclass(frozen=True)
class ProjectProfile:
    """Deterministic read-only profile of one registered project."""

    project_id: str
    name: str
    root_path: str
    technologies: Tuple[str, ...]
    top_level_directories: Tuple[str, ...]
    source_file_count: int
    inventory_truncated: bool
    source_files_sample: Tuple[str, ...]
    evidence: Tuple[ProjectEvidence, ...]
