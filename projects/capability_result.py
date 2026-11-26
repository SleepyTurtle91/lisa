from dataclasses import dataclass
from typing import Optional, Tuple

from lisa.projects.capability import CapabilityMatch


@dataclass(frozen=True)
class CapabilityDiscoveryResult:
    success: bool
    matches: Tuple[CapabilityMatch, ...] = ()
    error: Optional[str] = None
