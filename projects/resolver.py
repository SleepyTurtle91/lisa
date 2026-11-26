import hashlib
import os
from pathlib import Path
from typing import Dict, Tuple

from lisa.projects.manifest import ProjectManifest


class ProjectResolver:
    """Resolve a user-selected directory into a deterministic project identity."""

    PROJECT_MARKERS: Tuple[str, ...] = (
        ".git", "AGENTS.md", "BOOT.md", "README.md", "pyproject.toml",
        "setup.py", "package.json", "pubspec.yaml", "Cargo.toml", "go.mod",
        "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
        "settings.gradle.kts",
    )

    CAPABILITY_MARKERS: Dict[str, Tuple[str, ...]] = {
        "python": ("pyproject.toml", "setup.py"),
        "node": ("package.json",),
        "flutter": ("pubspec.yaml",),
        "rust": ("Cargo.toml",),
        "go": ("go.mod",),
        "java": ("pom.xml",),
        "gradle": (
            "build.gradle", "build.gradle.kts",
            "settings.gradle", "settings.gradle.kts",
        ),
        "kotlin": ("build.gradle.kts", "settings.gradle.kts"),
        "git": (".git",),
    }

    def resolve(self, path: str) -> ProjectManifest:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("A non-empty project path is required.")

        candidate = Path(path.strip()).expanduser()
        try:
            root = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"Project path cannot be resolved: {path}") from exc

        if not root.is_dir():
            raise ValueError(f"Project path is not a directory: {root}")

        markers = tuple(marker for marker in self.PROJECT_MARKERS if (root / marker).exists())
        if not markers:
            raise ValueError(
                f"Directory does not contain a recognized project marker: {root}"
            )

        normalized = os.path.normcase(str(root))
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        capabilities = tuple(
            capability
            for capability, names in self.CAPABILITY_MARKERS.items()
            if any(marker in markers for marker in names)
        )
        return ProjectManifest(
            project_id=f"prj_{digest}",
            name=root.name or str(root),
            root_path=str(root),
            markers=markers,
            capabilities=capabilities,
        )
