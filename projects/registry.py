import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from lisa.projects.context import ProjectContext
from lisa.projects.manifest import ProjectManifest
from lisa.projects.state import ProjectState


class ProjectRegistry:
    """Project registry with optional atomic JSON persistence.

    Pass no storage_path for an isolated in-memory registry (useful for tests).
    """

    STORAGE_VERSION = 1
    NON_TECHNICAL_CAPABILITIES = {"git", "hg", "svn", "vcs"}

    def __init__(self, storage_path=None):
        self._projects: Dict[str, ProjectManifest] = {}
        self._states: Dict[str, ProjectState] = {}
        self._active_project_id: Optional[str] = None
        self._storage_path = Path(storage_path).expanduser() if storage_path else None
        if self._storage_path is not None:
            self._load()

    @staticmethod
    def _identity_for(root_path: str) -> str:
        normalized = os.path.normcase(str(Path(root_path).resolve()))
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        return f"prj_{digest}"

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Project registry root must be a JSON object.")
            if data.get("schema_version") != self.STORAGE_VERSION:
                raise ValueError("Unsupported project registry schema version.")
            projects = data.get("projects")
            if not isinstance(projects, list):
                raise ValueError("Project registry 'projects' must be a list.")
            for item in projects:
                if not isinstance(item, dict):
                    raise ValueError("Invalid project registry entry.")
                root = item["root_path"]
                project_id = item["project_id"]
                if not isinstance(root, str) or not isinstance(project_id, str):
                    raise ValueError("Invalid project identity fields.")
                if self._identity_for(root) != project_id:
                    raise ValueError(f"Project identity integrity check failed: {project_id}")
                manifest = ProjectManifest(
                    project_id=project_id,
                    name=str(item["name"]),
                    root_path=str(Path(root).resolve()),
                    markers=tuple(str(v) for v in item["markers"]),
                    capabilities=tuple(
                        str(value) for value in item["capabilities"]
                        if str(value).casefold() not in self.NON_TECHNICAL_CAPABILITIES
                    ),
                )
                if project_id in self._projects:
                    raise ValueError(f"Duplicate project identity: {project_id}")
                self._projects[project_id] = manifest
                self._states[project_id] = ProjectState.REGISTERED

            active_id = data.get("active_project_id")
            if active_id is not None:
                if active_id not in self._projects:
                    raise ValueError("Active project is not present in the registry.")
                active_root = self._projects[active_id].root_path
                if Path(active_root).is_dir():
                    self._active_project_id = active_id
                    self._states[active_id] = ProjectState.ACTIVE
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError(f"Unable to read project registry at {self._storage_path}: {exc}") from exc

    def _persist(self) -> None:
        if self._storage_path is None:
            return
        parent = self._storage_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self.STORAGE_VERSION,
            "active_project_id": self._active_project_id,
            "projects": [
                {
                    "project_id": item.project_id,
                    "name": item.name,
                    "root_path": item.root_path,
                    "markers": list(item.markers),
                    "capabilities": list(item.capabilities),
                }
                for item in self.list_manifests()
            ],
        }
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=str(parent),
                prefix=f".{self._storage_path.name}.", suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(payload, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(str(temp_path), str(self._storage_path))
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def register(self, manifest: ProjectManifest) -> ProjectManifest:
        existing = self._projects.get(manifest.project_id)
        if existing is not None:
            if existing.root_path != manifest.root_path:
                raise ValueError("Project identity collision detected.")
            return existing
        self._projects[manifest.project_id] = manifest
        self._states[manifest.project_id] = ProjectState.REGISTERED
        try:
            self._persist()
        except Exception:
            self._projects.pop(manifest.project_id, None)
            self._states.pop(manifest.project_id, None)
            raise
        return manifest

    def get(self, project_id: str) -> Optional[ProjectManifest]:
        return self._projects.get(project_id)

    def list_manifests(self) -> List[ProjectManifest]:
        return sorted(
            self._projects.values(),
            key=lambda item: (item.name.casefold(), item.project_id),
        )

    def get_state(self, project_id: str) -> Optional[ProjectState]:
        return self._states.get(project_id)

    def activate(self, project_id: str) -> ProjectContext:
        manifest = self._projects.get(project_id)
        if manifest is None:
            raise KeyError(f"Project is not registered: {project_id}")
        if not Path(manifest.root_path).is_dir():
            raise ValueError(f"Registered project directory is no longer available: {manifest.root_path}")
        previous_active = self._active_project_id
        if previous_active is not None:
            self._states[previous_active] = ProjectState.REGISTERED
        self._active_project_id = project_id
        self._states[project_id] = ProjectState.ACTIVE
        try:
            self._persist()
        except Exception:
            self._active_project_id = previous_active
            self._states[project_id] = ProjectState.REGISTERED
            if previous_active is not None:
                self._states[previous_active] = ProjectState.ACTIVE
            raise
        return ProjectContext(project_id=project_id, root_path=manifest.root_path)

    def deactivate(self) -> None:
        previous_active = self._active_project_id
        if previous_active is None:
            return
        self._states[previous_active] = ProjectState.REGISTERED
        self._active_project_id = None
        try:
            self._persist()
        except Exception:
            self._active_project_id = previous_active
            self._states[previous_active] = ProjectState.ACTIVE
            raise

    def active_context(self) -> Optional[ProjectContext]:
        if self._active_project_id is None:
            return None
        manifest = self._projects[self._active_project_id]
        return ProjectContext(project_id=manifest.project_id, root_path=manifest.root_path)

    def unregister(self, project_id: str) -> bool:
        if project_id not in self._projects:
            return False
        manifest = self._projects[project_id]
        previous_state = self._states[project_id]
        was_active = self._active_project_id == project_id
        if was_active:
            self._active_project_id = None
        del self._projects[project_id]
        del self._states[project_id]
        try:
            self._persist()
        except Exception:
            self._projects[project_id] = manifest
            self._states[project_id] = previous_state
            if was_active:
                self._active_project_id = project_id
            raise
        return True
