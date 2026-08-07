import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class BootConfig:
    project_path: str
    agents_md_present: bool
    boot_md_present: bool
    lisa_config_present: bool

class BootstrapEngine:
    @staticmethod
    def discover(project_path: str) -> BootConfig:
        agents_path = os.path.join(project_path, "AGENTS.md")
        boot_path = os.path.join(project_path, "BOOT.md")
        config_path = os.path.join(project_path, ".lisa", "config.json")

        return BootConfig(
            project_path=project_path,
            agents_md_present=os.path.exists(agents_path),
            boot_md_present=os.path.exists(boot_path),
            lisa_config_present=os.path.exists(config_path)
        )
