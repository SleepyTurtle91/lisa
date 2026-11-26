from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class CapabilityEvidence:
    relative_path: str
    evidence_kind: str
    sha256: Optional[str] = None


@dataclass(frozen=True)
class CapabilityMatch:
    project_id: str
    project_name: str
    score: float
    matched_terms: Tuple[str, ...]
    evidence: Tuple[CapabilityEvidence, ...]
    source_paths: Tuple[str, ...]
