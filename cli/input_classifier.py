"""
Input Boundary Classifier for L.I.S.A. (NE-014.1)

Classifies raw user inputs prior to REPL dispatch or LLM inference:
  - DIRECT_COMMAND: Short, literal REPL commands ('read BOOT.md', 'list', 'doctor', 'help', 'switch').
  - PATH_INPUT: Literal file or directory paths ('/workspace/Projects/retails', './docs').
  - NATURAL_LANGUAGE: Compound requests or prose ('read files inside /docs and suggest a plan').

Prevents naive REPL string matching (e.g., startswith("read ")) from hijacking compound natural language inputs.
"""

import os
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple, List


class InputClass(Enum):
    DIRECT_COMMAND = auto()
    PATH_INPUT = auto()
    NATURAL_LANGUAGE = auto()


@dataclass
class ClassificationResult:
    input_class: InputClass
    command: Optional[str]
    target: Optional[str]
    raw_input: str


class InputBoundaryClassifier:
    """Classifies user input deterministically to prevent REPL prefix hijacking."""

    LITERAL_COMMANDS = {"help", "doctor", "compare", "switch", "exit", "quit", "list", "ls", "dir"}

    @classmethod
    def classify(cls, raw_input: str, project_path: Optional[str] = None) -> ClassificationResult:
        text = raw_input.strip()
        if not text:
            return ClassificationResult(InputClass.NATURAL_LANGUAGE, None, None, text)

        text_lower = text.lower()
        words = text.split()

        # 1. Exact Literal Commands ('help', 'doctor', 'list', 'switch', etc.)
        if text_lower in cls.LITERAL_COMMANDS:
            return ClassificationResult(InputClass.DIRECT_COMMAND, text_lower, None, text)

        # 2. Command with Single Short File Target ('read BOOT.md', 'activity compact')
        if len(words) == 2 and words[0].lower() in ("read", "activity"):
            cmd = words[0].lower()
            target = words[1]
            # If target contains prose spaces or compound words, it's natural language, not a single file target
            if " " not in target:
                return ClassificationResult(InputClass.DIRECT_COMMAND, cmd, target, text)

        # 3. Absolute or Relative Path Input ('/workspace/Projects/retails', './docs')
        if (text.startswith("/") or text.startswith("./") or text.startswith("../") or text.startswith("~/")):
            expanded = os.path.expanduser(text)
            if os.path.exists(expanded) or " " not in text:
                return ClassificationResult(InputClass.PATH_INPUT, "inspect_path", text, text)

        # 4. Fallthrough to Natural Language (Compound prose like 'read files inside /docs and suggest a plan')
        return ClassificationResult(InputClass.NATURAL_LANGUAGE, None, None, text)
