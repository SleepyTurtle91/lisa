"""
Epistemic Evidence Store for L.I.S.A. (NE-012.1 Experiment B)

Parses raw FlightRecorder traces into structured, queryable epistemic evidence buckets:
- OBSERVED: Directly executed tool requests and verified successful tool results.
- DOCUMENTED: Text read from inspected files.
- INFERRED: Model deductions and claims.
- UNVERIFIED: Claimed or requested actions without recorded execution evidence.

Provides an authoritative evidence query boundary that answers "what has actually been verified?"
from recorder logs rather than model self-reflection.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class EvidenceCategory(Enum):
    OBSERVED = auto()
    DOCUMENTED = auto()
    INFERRED = auto()
    UNVERIFIED = auto()


@dataclass
class EvidenceItem:
    category: EvidenceCategory
    source_event: str
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)


class EvidenceStore:
    """Indexed epistemic evidence store constructed directly from flight events."""

    def __init__(self):
        self._items: List[EvidenceItem] = []

    @property
    def items(self) -> List[EvidenceItem]:
        return list(self._items)

    def ingest_event(self, event: Dict[str, Any]) -> None:
        etype = event.get("event_type", "")
        payload = event.get("payload") or {}

        if etype == "flight_stage" and payload.get("stage") == "tool_result":
            tool_name = payload.get("tool_name", "unknown_tool")
            success = payload.get("success", False)
            if success:
                self._items.append(
                    EvidenceItem(
                        category=EvidenceCategory.OBSERVED,
                        source_event=etype,
                        summary=f"Tool '{tool_name}' executed successfully",
                        details=payload,
                    )
                )
            else:
                self._items.append(
                    EvidenceItem(
                        category=EvidenceCategory.UNVERIFIED,
                        source_event=etype,
                        summary=f"Tool '{tool_name}' failed execution",
                        details=payload,
                    )
                )

        elif etype == "model_response":
            content = payload.get("content") or ""
            if content:
                self._items.append(
                    EvidenceItem(
                        category=EvidenceCategory.INFERRED,
                        source_event=etype,
                        summary="Model response claim",
                        details={"content": content},
                    )
                )

    def query(self, category: Optional[EvidenceCategory] = None) -> List[EvidenceItem]:
        if category is None:
            return list(self._items)
        return [item for item in self._items if item.category == category]

    def summarize_provenance(self) -> Dict[str, Any]:
        return {
            "OBSERVED_count": len(self.query(EvidenceCategory.OBSERVED)),
            "DOCUMENTED_count": len(self.query(EvidenceCategory.DOCUMENTED)),
            "INFERRED_count": len(self.query(EvidenceCategory.INFERRED)),
            "UNVERIFIED_count": len(self.query(EvidenceCategory.UNVERIFIED)),
            "observed_tools": [i.summary for i in self.query(EvidenceCategory.OBSERVED)],
            "unverified_items": [i.summary for i in self.query(EvidenceCategory.UNVERIFIED)],
        }
