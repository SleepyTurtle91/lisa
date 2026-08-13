"""
Target Grounding & Type Inspection Module for L.I.S.A. (NE-012.1 Experiment A)

Inspects candidate filesystem targets before tool execution to determine:
1. Resolved absolute path
2. Filesystem type (FILE, DIRECTORY, MISSING)
3. Operation validity (e.g. rejecting list_directory on FILE or read_file on DIRECTORY)

Prevents dispatcher tool execution on invalid target/operation combinations and eliminates
silent model fallback paths (such as list_directory("/")).
"""

import os
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any


class TargetType(Enum):
    FILE = auto()
    DIRECTORY = auto()
    MISSING = auto()


@dataclass
class TargetInspection:
    raw_path: str
    resolved_path: str
    target_type: TargetType
    is_absolute: bool


class TargetInspector:
    """Inspects filesystem target types deterministically without LLM inference."""

    @staticmethod
    def inspect(path: str, project_path: Optional[str] = None) -> TargetInspection:
        if not path:
            resolved = os.path.normpath(project_path or os.getcwd())
            return TargetInspection(
                raw_path=path,
                resolved_path=resolved,
                target_type=TargetType.DIRECTORY if os.path.isdir(resolved) else TargetType.MISSING,
                is_absolute=False,
            )

        is_abs = os.path.isabs(path)
        if is_abs:
            resolved = os.path.normpath(path)
        else:
            base = project_path or os.getcwd()
            resolved = os.path.normpath(os.path.join(base, path))

        if not os.path.exists(resolved):
            t_type = TargetType.MISSING
        elif os.path.isdir(resolved):
            t_type = TargetType.DIRECTORY
        elif os.path.isfile(resolved):
            t_type = TargetType.FILE
        else:
            t_type = TargetType.MISSING

        return TargetInspection(
            raw_path=path,
            resolved_path=resolved,
            target_type=t_type,
            is_absolute=is_abs,
        )

    @staticmethod
    def validate_tool_operation(tool_name: str, inspection: TargetInspection) -> Tuple[bool, Optional[str]]:
        """
        Validates whether tool_name is a legal operation for the given target inspection.
        Returns (is_valid, rejection_reason).
        """
        # If target is MISSING, let the underlying tool handle file-not-found and case suggestions natively
        if inspection.target_type == TargetType.MISSING:
            return True, None

        if tool_name == "list_directory":
            if inspection.target_type == TargetType.FILE:
                return False, f"Cannot execute list_directory on FILE target '{inspection.raw_path}' (Resolved: {inspection.resolved_path}). Target is a file, not a directory."
            elif inspection.target_type != TargetType.DIRECTORY:
                return False, f"Target '{inspection.raw_path}' is not a directory."

        elif tool_name == "read_file":
            if inspection.target_type == TargetType.DIRECTORY:
                return False, f"Cannot execute read_file on DIRECTORY target '{inspection.raw_path}' (Resolved: {inspection.resolved_path}). Target is a directory, not a file."
            elif inspection.target_type != TargetType.FILE:
                return False, f"Target '{inspection.raw_path}' is not a readable file."

        return True, None

    @staticmethod
    def validate_target_identity(user_prompt: Optional[str], requested_path: str, project_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validates whether requested_path binds to the intended target in user_prompt (NE-012.3).
        Prevents substituting unrelated targets (such as '/' or '.') when the user explicitly specified a file/directory candidate.
        """
        if not user_prompt:
            return True, None

        prompt_clean = user_prompt.strip()
        tokens = prompt_clean.split()
        if len(tokens) >= 2:
            candidate_target = tokens[-1].strip("`'\"")
            if candidate_target and candidate_target not in ("/", ".", "./") and "." in candidate_target:
                req_norm = os.path.normpath(requested_path) if requested_path else ""
                if req_norm in ("/", ".", ""):
                    return False, f"Target Identity Mismatch: User objective specified '{candidate_target}', but tool requested fallback target '{requested_path}'"

        return True, None
