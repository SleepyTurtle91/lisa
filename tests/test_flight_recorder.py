import os
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.telemetry.flight_recorder import FlightRecorder

class TestFlightRecorder(unittest.TestCase):
    def test_flight_recorder_event_stream(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = FlightRecorder(session_id="test_session_123", log_dir=Path(tmpdir))
            
            recorder.record_event("session_start", {"project_path": "/test/project"})
            recorder.record_event("task_received", {"prompt": "Fix bug"})
            recorder.record_event("tool_call", {"tool": "read_file", "path": "BOOT.md"})
            recorder.record_event("session_end", {"status": "SUCCESS"})
            
            events = recorder.get_events()
            self.assertEqual(len(events), 4)
            self.assertEqual(events[0]["event_type"], "session_start")
            self.assertEqual(events[1]["event_type"], "task_received")
            self.assertEqual(events[2]["event_type"], "tool_call")
            self.assertEqual(events[3]["event_type"], "session_end")

    def test_flight_recorder_preserves_payloads_and_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = FlightRecorder(session_id="test_session_456", log_dir=Path(tmpdir))

            recorder.record_event("task_start", {"step": 1, "target": "runtime_contract"})
            recorder.record_event("task_end", {"step": 2, "result": "verified"})

            events = recorder.get_events()
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]["payload"]["target"], "runtime_contract")
            self.assertEqual(events[1]["payload"]["result"], "verified")
            self.assertEqual(events[0]["session_id"], "test_session_456")

    def test_subscriber_receives_live_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = FlightRecorder(session_id="test_session_sub", log_dir=Path(tmpdir))
            received = []

            def on_event(event):
                received.append(event)

            recorder.subscribe(on_event)
            recorder.record_event("tool_call", {"tool": "read_file", "path": "AGENTS.md"})

            self.assertEqual(len(received), 1)
            self.assertEqual(received[0]["event_type"], "tool_call")
            self.assertEqual(received[0]["payload"]["path"], "AGENTS.md")

            recorder.unsubscribe(on_event)
            recorder.record_event("tool_result", {"success": True})
            self.assertEqual(len(received), 1)

if __name__ == "__main__":
    unittest.main()
