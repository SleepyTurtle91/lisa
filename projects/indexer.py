import hashlib
import os
import re
from itertools import islice
from pathlib import Path
from typing import Iterable, List, Set, Tuple

from lisa.projects.manifest import ProjectManifest
from lisa.projects.profile import ProjectEvidence, ProjectProfile


class ProjectProfileIndexer:
    """Read-only, bounded project profiler.

    It reads documentation and build descriptors only. Source code is inventoried
    by path and extension; source contents are not ingested at this stage.
    """

    MAX_SCANNED_FILES = 20000
    MAX_WALK_DEPTH = 4

    IGNORED_DIRS: Set[str] = {
        ".git", ".hg", ".svn", ".idea", ".gradle", ".dart_tool",
        ".venv", "venv", "env", "__pycache__", ".pytest_cache",
        "node_modules", "vendor", "build", "dist", "target",
        "out", ".next", ".nuxt", ".turbo", "coverage",
    }

    DOCUMENT_NAMES: Set[str] = {
        "README.md", "AGENTS.md", "BOOT.md", "ARCHITECTURE.md",
        "CONTRIBUTING.md", "DEVELOPMENT.md", "BUSINESS_RULES.md",
        "AI_CONTEXT.md", "AI_INSTRUCTIONS.md",
    }

    BUILD_NAMES: Set[str] = {
        "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
        "package.json", "pubspec.yaml", "Cargo.toml", "go.mod",
        "pom.xml", "build.gradle", "build.gradle.kts",
        "settings.gradle", "settings.gradle.kts", "gradle.properties",
        "CMakeLists.txt", "Makefile",
    }

    SECRET_ASSIGNMENT = re.compile(
        r'''(?im)(["']?\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|password|passwd|secret|private[_-]?key)\b["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,;]+)'''
    )
    PRIVATE_KEY_BLOCK = re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL,
    )

    SOURCE_SUFFIXES: Set[str] = {
        ".py", ".kt", ".kts", ".java", ".dart", ".ts", ".tsx", ".js",
        ".jsx", ".go", ".rs", ".cs", ".swift", ".php", ".rb", ".cpp",
        ".c", ".h", ".hpp", ".scala", ".sql",
    }

    def _walk(self, root: Path, max_depth: int) -> Iterable[Path]:
        for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current)
            depth = len(current_path.relative_to(root).parts)
            dirs[:] = sorted(
                name for name in dirs
                if name not in self.IGNORED_DIRS
                and not name.startswith(".")
                and not (current_path / name).is_symlink()
                and depth < max_depth
            )
            for name in sorted(files):
                path = current_path / name
                if path.is_symlink() or not path.is_file():
                    continue
                yield path

    @classmethod
    def _redact_excerpt(cls, text: str) -> Tuple[str, bool]:
        redacted, assignment_count = cls.SECRET_ASSIGNMENT.subn(
            lambda match: match.group(1) + "[REDACTED]", text
        )
        redacted, key_count = cls.PRIVATE_KEY_BLOCK.subn(
            "[PRIVATE KEY REDACTED]", redacted
        )
        return redacted, bool(assignment_count or key_count)

    def index(
        self,
        manifest: ProjectManifest,
        max_evidence_files: int = 64,
        max_bytes_per_file: int = 65536,
        max_source_files: int = 1000,
    ) -> ProjectProfile:
        root = Path(manifest.root_path).resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"Registered project root is not a directory: {root}")

        walked_files = list(islice(
            self._walk(root, max_depth=self.MAX_WALK_DEPTH),
            self.MAX_SCANNED_FILES + 1,
        ))
        inventory_truncated = len(walked_files) > self.MAX_SCANNED_FILES
        all_files = sorted(
            walked_files[:self.MAX_SCANNED_FILES],
            key=lambda path: path.relative_to(root).as_posix(),
        )
        evidence_candidates: List[Tuple[Path, str]] = []
        source_paths: List[str] = []
        technologies = set(manifest.capabilities)

        for path in all_files:
            relative = path.relative_to(root)
            name = path.name
            parts = relative.parts
            if name in self.DOCUMENT_NAMES and (
                len(parts) == 1 or (parts[0] == "docs" and len(parts) <= 2)
            ):
                evidence_candidates.append((path, "project_document"))
            elif name in self.BUILD_NAMES and len(parts) <= 3:
                evidence_candidates.append((path, "build_descriptor"))

            suffix = path.suffix.lower()
            if suffix in self.SOURCE_SUFFIXES and name not in self.BUILD_NAMES:
                source_paths.append(relative.as_posix())
                if suffix in (".kt", ".kts"):
                    technologies.add("kotlin")
                elif suffix == ".dart":
                    technologies.add("flutter")
                elif suffix == ".py":
                    technologies.add("python")
                elif suffix in (".ts", ".tsx", ".js", ".jsx"):
                    technologies.add("node")
                elif suffix == ".rs":
                    technologies.add("rust")
                elif suffix == ".go":
                    technologies.add("go")
                elif suffix == ".java":
                    technologies.add("java")
                elif suffix == ".cs":
                    technologies.add("csharp")
                elif suffix == ".swift":
                    technologies.add("swift")
                elif suffix == ".php":
                    technologies.add("php")
                elif suffix == ".rb":
                    technologies.add("ruby")
                elif suffix in (".cpp", ".hpp"):
                    technologies.add("cpp")
                elif suffix in (".c", ".h"):
                    technologies.add("c")
                elif suffix == ".scala":
                    technologies.add("scala")
                elif suffix == ".sql":
                    technologies.add("sql")

            if name == "AndroidManifest.xml":
                technologies.add("android")

        evidence: List[ProjectEvidence] = []
        for path, kind in evidence_candidates[:max_evidence_files]:
            try:
                with path.open("rb") as handle:
                    raw = handle.read(max_bytes_per_file + 1)
            except OSError:
                continue
            truncated = len(raw) > max_bytes_per_file
            inspected = raw[:max_bytes_per_file]
            digest = hashlib.sha256(inspected).hexdigest()
            excerpt = inspected.decode("utf-8", errors="replace")
            excerpt, redactions_applied = self._redact_excerpt(excerpt)
            if truncated:
                excerpt += "\n[Excerpt truncated at configured byte limit.]"
            evidence.append(ProjectEvidence(
                relative_path=path.relative_to(root).as_posix(),
                evidence_kind=kind,
                sha256=digest,
                bytes_inspected=len(inspected),
                excerpt=excerpt,
                truncated=truncated,
                redactions_applied=redactions_applied,
            ))

        top_level = tuple(sorted(
            path.name for path in root.iterdir()
            if path.is_dir()
            and not path.is_symlink()
            and not path.name.startswith(".")
            and path.name not in self.IGNORED_DIRS
        ))

        return ProjectProfile(
            project_id=manifest.project_id,
            name=manifest.name,
            root_path=str(root),
            technologies=tuple(sorted(technologies)),
            top_level_directories=top_level,
            source_file_count=len(source_paths),
            inventory_truncated=inventory_truncated,
            source_files_sample=tuple(source_paths[:max_source_files]),
            evidence=tuple(evidence),
        )
