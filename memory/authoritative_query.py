"""
Authoritative Evidence Query Module for L.I.S.A. (NE-013)

Bypasses LLM self-reflection to answer provenance queries ("What has actually been verified?")
directly from the recorder-backed EvidenceStore.

Prevents models from conflating DOCUMENTED file claims (e.g. "32/32 tests passed" in README.md)
with OBSERVED session execution events.
"""

from typing import Dict, Any, List
from lisa.memory.evidence_store import EvidenceStore, EvidenceCategory
from lisa.telemetry.flight_recorder import FlightRecorder


class AuthoritativeEvidenceQuery:
    """Answers provenance queries deterministically from EvidenceStore trace logs."""

    @staticmethod
    def query_session_provenance(recorder: FlightRecorder) -> Dict[str, Any]:
        store = EvidenceStore()
        for event in recorder.get_events():
            store.ingest_event(event)

        observed = store.query(EvidenceCategory.OBSERVED)
        documented = store.query(EvidenceCategory.DOCUMENTED)
        inferred = store.query(EvidenceCategory.INFERRED)
        unverified = store.query(EvidenceCategory.UNVERIFIED)

        return {
            "verified_in_this_session": [item.summary for item in observed],
            "documented_in_files": [item.summary for item in documented],
            "inferred_by_model": [item.summary for item in inferred],
            "unverified_claims": [item.summary for item in unverified],
            "is_provenance_authoritative": True,
            "total_observed_events": len(observed),
        }

    @staticmethod
    def format_authoritative_response(recorder: FlightRecorder) -> str:
        provenance = AuthoritativeEvidenceQuery.query_session_provenance(recorder)
        observed = provenance["verified_in_this_session"]

        if not observed:
            return "Authoritative Session Provenance: No tool executions or verification actions have been OBSERVED in this session."

        lines = ["Authoritative Session Provenance (Recorded Execution Events):"]
        for idx, item in enumerate(observed, 1):
            lines.append(f"{idx}. {item}")
        return "\n".join(lines)
