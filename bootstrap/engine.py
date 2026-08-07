import os
import platform
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class SystemBootConfig:
    os_name: str
    architecture: str
    python_version: str
    git_present: bool

@dataclass
class ProjectBootConfig:
    project_path: str
    project_name: str
    agents_md_present: bool
    boot_md_present: bool
    lisa_config_present: bool
    discovered_capabilities: List[str] = field(default_factory=list)

@dataclass
class BootConfig:
    system: SystemBootConfig
    project: ProjectBootConfig

class BootstrapEngine:
    @staticmethod
    def discover_system() -> SystemBootConfig:
        """System Boot: Runs once to inspect environment capabilities."""
        return SystemBootConfig(
            os_name=platform.system(),
            architecture=platform.machine(),
            python_version=platform.python_version(),
            git_present=os.system("git --version > /dev/null 2>&1") == 0
        )

    @staticmethod
    def discover_project(project_path: str) -> ProjectBootConfig:
        """Project Boot: Discovers project-specific AGENTS.md, BOOT.md, and capabilities."""
        agents_path = os.path.join(project_path, "AGENTS.md")
        boot_path = os.path.join(project_path, "BOOT.md")
        config_path = os.path.join(project_path, ".lisa", "config.json")

        project_name = os.path.basename(os.path.abspath(project_path))

        capabilities = ["read_file", "write_file", "list_directory"]
        if os.path.exists(os.path.join(project_path, "pubspec.yaml")):
            capabilities.append("flutter")
        if os.path.exists(os.path.join(project_path, "pom.xml")) or os.path.exists(os.path.join(project_path, "build.gradle")):
            capabilities.append("java_gradle")

        return ProjectBootConfig(
            project_path=project_path,
            project_name=project_name,
            agents_md_present=os.path.exists(agents_path),
            boot_md_present=os.path.exists(boot_path),
            lisa_config_present=os.path.exists(config_path),
            discovered_capabilities=capabilities
        )

    @classmethod
    def discover(cls, project_path: str) -> BootConfig:
        """2-Tier Boot Discovery Engine."""
        return BootConfig(
            system=cls.discover_system(),
            project=cls.discover_project(project_path)
        )
