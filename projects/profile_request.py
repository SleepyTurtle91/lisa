from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectProfileRequest:
    project_id: str
    max_evidence_files: int = 64
    max_bytes_per_file: int = 65536
    max_source_files: int = 1000
