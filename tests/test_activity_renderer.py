import io
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.telemetry.activity_renderer import FlightConsole
from lisa.telemetry.flight_recorder import FlightRecorder


class TestActivityRenderer(unittest.TestCase):
    def test_compact_mode_renders_real_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = io.StringIO()
            recorder = FlightRecorder(session_id="activity_renderer_test", log_dir=Path(tmpdir))
            console = FlightConsole(project_name="retails", mode="compact", stream=output)
            console.bind(recorder)

            recorder.record_event("flight_stage", {"stage": "task_received", "message": "inspect architecture"})
            recorder.record_event("flight_stage", {"stage": "project_context", "project_path": "/workspace/Projects/retails"})
            recorder.record_event("model_request", {"model_name": "qwen3:4b"})
            recorder.record_event("flight_stage", {
                "stage": "tool_request",
                "tool_name": "read_file",
                "arguments": {"path": "/workspace/Projects/retails/AGENTS.md"},
            })
            recorder.record_event("flight_stage", {"stage": "tool_result", "tool_name": "read_file", "success": True})
            recorder.record_event("flight_stage", {"stage": "final_conclusion", "content": "done"})

            text = output.getvalue()
            self.assertIn("L.I.S.A. ACTIVE", text)
            self.assertIn("Orienting", text)
            self.assertIn("Thinking", text)
            self.assertIn("Provider response", text)
            self.assertIn("Using", text)
            self.assertIn("Tool result", text)
            self.assertIn("Tool result received", text)
            self.assertIn("Completed", text)
            self.assertEqual(console.semantic_state, "COMPLETED")

    def test_guarding_and_blocked_are_rendered_from_real_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = io.StringIO()
            recorder = FlightRecorder(session_id="activity_renderer_guard_test", log_dir=Path(tmpdir))
            console = FlightConsole(project_name="retails", mode="compact", stream=output)
            console.bind(recorder)

            recorder.record_event("model_response", {"content": "No appropriate tool is available.", "tool_calls": []})
            recorder.record_event("flight_stage", {"stage": "guarding_decision", "reason": "unsupported action"})
            recorder.record_event("flight_stage", {"stage": "blocked", "reason": "Insufficient capability"})

            text = output.getvalue()
            self.assertIn("Guarding", text)
            self.assertIn("Blocked", text)
            self.assertIn("Insufficient capability", text)
            self.assertEqual(console.semantic_state, "BLOCKED")

    def test_model_only_refusal_classifies_guarding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = io.StringIO()
            recorder = FlightRecorder(session_id="activity_renderer_refusal_test", log_dir=Path(tmpdir))
            console = FlightConsole(project_name="retails", mode="compact", stream=output)
            console.bind(recorder)

            recorder.record_event("model_request", {"model_name": "qwen3:1.7b", "provider_id": "ollama"})
            recorder.record_event("model_response", {
                "content": "I am not able to complete this operation with current capabilities.",
                "tool_calls": None,
            })

            self.assertEqual(console.semantic_state, "GUARDING")
            self.assertIn("Guarding", output.getvalue())

    def test_blocked_stage_precedence_overrides_later_model_prose(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = io.StringIO()
            recorder = FlightRecorder(session_id="activity_renderer_precedence_test", log_dir=Path(tmpdir))
            console = FlightConsole(project_name="retails", mode="compact", stream=output)
            console.bind(recorder)

            recorder.record_event("flight_stage", {"stage": "tool_result", "tool_name": "read_file", "success": False})
            recorder.record_event("flight_stage", {"stage": "guarding_decision", "reason": "unsupported"})
            recorder.record_event("flight_stage", {"stage": "blocked", "reason": "File not found"})
            recorder.record_event("model_response", {
                "content": "Here is a summary of BOOT.md and smoke sequence...",
                "tool_calls": None,
            })

            self.assertEqual(console.semantic_state, "BLOCKED")
            self.assertEqual(console.current_state, "blocked")

    def test_evidence_resets_between_flights(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = io.StringIO()
            recorder = FlightRecorder(session_id="activity_renderer_reset_test", log_dir=Path(tmpdir))
            console = FlightConsole(project_name="retails", mode="compact", stream=output)
            console.bind(recorder)

            recorder.record_event("flight_stage", {"stage": "tool_result", "tool_name": "read_file", "success": False})
            recorder.record_event("flight_stage", {"stage": "guarding_decision", "reason": "unsupported"})
            recorder.record_event("flight_stage", {"stage": "blocked", "reason": "File not found"})
            recorder.record_event("flight_stage", {"stage": "final_conclusion", "content": "failed turn"})
            self.assertEqual(console.semantic_state, "BLOCKED")

            recorder.record_event("flight_stage", {"stage": "task_received", "message": "define retails project"})
            recorder.record_event("model_request", {"model_name": "qwen3:1.7b", "provider_id": "ollama"})
            recorder.record_event("model_response", {
                "content": "I don't have access to that capability. Would you like me to analyze BOOT.md instead?",
                "tool_calls": None,
            })

            self.assertEqual(console.semantic_state, "GUARDING")

    def test_mode_switch_is_validated(self):
        output = io.StringIO()
        console = FlightConsole(project_name="retails", mode="compact", stream=output)

        self.assertTrue(console.set_mode("verbose"))
        self.assertEqual(console.mode, "verbose")
        self.assertFalse(console.set_mode("invalid"))
        self.assertEqual(console.mode, "verbose")


if __name__ == "__main__":
    unittest.main()
