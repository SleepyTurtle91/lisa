"""
Unit tests for EvidenceStore (NE-012.1 Experiment B).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.memory.evidence_store import EvidenceStore, EvidenceCategory


class TestEvidenceStore(unittest.TestCase):
    def test_ingest_observed_tool_result(self):
        store = EvidenceStore()
        event = {
            "event_type": "flight_stage",
            "payload": {"stage": "tool_result", "tool_name": "read_file", "success": True},
        }
        store.ingest_event(event)

        observed = store.query(EvidenceCategory.OBSERVED)
        self.assertEqual(len(observed), 1)
        self.assertIn("read_file", observed[0].summary)

    def test_ingest_failed_tool_as_unverified(self):
        store = EvidenceStore()
        event = {
            "event_type": "flight_stage",
            "payload": {"stage": "tool_result", "tool_name": "list_directory", "success": False},
        }
        store.ingest_event(event)

        unverified = store.query(EvidenceCategory.UNVERIFIED)
        self.assertEqual(len(unverified), 1)
        self.assertIn("list_directory", unverified[0].summary)

    def test_ingest_inferred_model_response(self):
        store = EvidenceStore()
        event = {
            "event_type": "model_response",
            "payload": {"content": "The project uses Flutter."},
        }
        store.ingest_event(event)

        inferred = store.query(EvidenceCategory.INFERRED)
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0].details["content"], "The project uses Flutter.")

    def test_summarize_provenance(self):
        store = EvidenceStore()
        store.ingest_event({"event_type": "flight_stage", "payload": {"stage": "tool_result", "tool_name": "read_file", "success": True}})
        store.ingest_event({"event_type": "model_response", "payload": {"content": "Claim"}})

        summary = store.summarize_provenance()
        self.assertEqual(summary["OBSERVED_count"], 1)
        self.assertEqual(summary["INFERRED_count"], 1)
        self.assertEqual(summary["UNVERIFIED_count"], 0)


if __name__ == "__main__":
    unittest.main()
