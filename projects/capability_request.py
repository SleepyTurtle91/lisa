from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class CapabilityDiscoveryRequest:
    query: str
    project_ids: Tuple[str, ...] = ()
    max_results: int = 20
