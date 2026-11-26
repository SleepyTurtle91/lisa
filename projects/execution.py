"""Immutable request and result contracts for governed project execution."""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ExecutionChange:
    """One explicitly scoped UTF-8 file replacement or creation.

    expected_sha256 must match the current file. Use None only when the file
    does not exist yet. Deletions and directory creation are intentionally
    unsupported in CPI-06.
    """
    relative_path: str
    content: str
    expected_sha256: Optional[str] = None


@dataclass(frozen=True)
class ProjectExecutionRequest:
    plan: object
    changes: Tuple[ExecutionChange, ...]
    operator_confirmation: str


@dataclass(frozen=True)
class ProjectExecutionResult:
    success: bool
    execution_id: Optional[str] = None
    changed_files: Tuple[str, ...] = ()
    backup_directory: Optional[str] = None
    audit_path: Optional[str] = None
    validation_required: bool = True
    error: Optional[str] = None
