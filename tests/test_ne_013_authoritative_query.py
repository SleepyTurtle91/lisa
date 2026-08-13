"""
Unit tests for AuthoritativeEvidenceQuery (NE-013).
"""

import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.memory.evidence_store import EvidenceStore, EvidenceCategory
from lisa.memory.authoritative_query import AuthoritativeEvidenceQuery


class TestAuthoritativeEvidenceQuery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.recorder = FlightRecorder(session_id="test_ne013", log_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_query_empty_session_provenance(self):
        resp = AuthoritativeEvidenceQuery.format_authoritative_response(self.recorder)
        self.assertIn("No tool executions or verification actions have been OBSERVED", resp)

    def test_query_session_with_read_file_documentation_only(self):
        # Record a file read event containing documented test claims
        self.recorder.record_event("flight_stage", {"stage": "tool_result", "tool_name": "read_file", "success": True, "metadata": {"content": "32/32 tests passed"}})

        prov = AuthoritativeEvidenceQuery.query_session_provenance(self.recorder)
        self.assertEqual(prov["total_observed_events"], 1)
        self.assertEqual(prov["verified_in_this_session"], ["Tool 'read_file' executed successfully"])
        
        # Must NOT claim that tests passed in this session
        self.assertNotIn("32/32 tests passed", prov["verified_in_this_session"])

    def test_format_authoritative_response(self):
        self.recorder.record_event("flight_stage", {"stage": "tool_result", "tool_name": "read_file", "success": True})
        resp = AuthoritativeEvidenceQuery.format_authoritative_response(self.recorder)
        self.assertIn("Authoritative Session Provenance", resp)
        self.assertIn("1. Tool 'read_file' executed successfully", resp)


if __name__ == "__main__":
    unittest.main()
