import importlib.util
import json
import tempfile
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent.parent / "benchmarks" / "ne_010_operator_perception_fidelity.py"
SPEC = importlib.util.spec_from_file_location("ne010", MODULE_PATH)
NE010 = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(NE010)


class TestNE010Evaluator(unittest.TestCase):
    def test_boundary_misprojection_is_hard_failure(self):
        events = [
            {"event_type": "flight_stage", "payload": {"stage": "task_received"}},
            {"event_type": "flight_stage", "payload": {"stage": "tool_result", "success": False, "tool_name": "read_file"}},
            {"event_type": "flight_stage", "payload": {"stage": "guarding_decision", "reason": "failed"}},
            {"event_type": "flight_stage", "payload": {"stage": "blocked", "reason": "failed"}},
            {"event_type": "flight_stage", "payload": {"stage": "final_conclusion", "content": "done"}},
        ]
        snapshots = [
            NE010.ProjectionSnapshot(0, "flight_stage", "task_received", ["Orienting"], "orienting", "UNKNOWN", "", "EMPTY"),
            NE010.ProjectionSnapshot(1, "flight_stage", "tool_result", ["Blocked"], "blocked", "ERROR", "", "EMPTY"),
            NE010.ProjectionSnapshot(2, "flight_stage", "guarding_decision", ["Guarding"], "guarding", "BLOCKED", "", "EMPTY"),
            NE010.ProjectionSnapshot(3, "flight_stage", "blocked", ["Blocked"], "blocked", "BLOCKED", "", "EMPTY"),
            NE010.ProjectionSnapshot(4, "flight_stage", "final_conclusion", ["Completed"], "completed", "BLOCKED", "", "EMPTY"),
        ]

        result = NE010.evaluate_flight("F1", "test", events, snapshots, "irrelevant")
        self.assertTrue(result["hard_failure"])
        self.assertFalse(result["overall_pass"])

    def test_completed_flight_can_pass(self):
        events = [
            {"event_type": "flight_stage", "payload": {"stage": "task_received"}},
            {"event_type": "model_request", "payload": {"model_name": "qwen3:1.7b", "provider_id": "ollama"}},
            {"event_type": "flight_stage", "payload": {"stage": "tool_request", "tool_name": "read_file", "arguments": {"path": "README.md"}}},
            {"event_type": "flight_stage", "payload": {"stage": "tool_result", "success": True, "tool_name": "read_file"}},
            {"event_type": "model_response", "payload": {"content": "Done", "tool_calls": None}},
            {"event_type": "flight_stage", "payload": {"stage": "final_conclusion", "content": "Done"}},
        ]
        snapshots = [
            NE010.ProjectionSnapshot(0, "flight_stage", "task_received", ["Orienting"], "orienting", "UNKNOWN", "", "EMPTY"),
            NE010.ProjectionSnapshot(1, "model_request", None, ["Thinking", "Provider response (ollama)"], "thinking", "UNKNOWN", "", "EMPTY"),
            NE010.ProjectionSnapshot(2, "flight_stage", "tool_request", ["read_file", "README.md", "Tool result"], "using", "UNKNOWN", "", "EMPTY"),
            NE010.ProjectionSnapshot(3, "flight_stage", "tool_result", ["Tool result received"], "using", "UNKNOWN", "", "EMPTY"),
            NE010.ProjectionSnapshot(4, "model_response", None, ["Completed"], "completed", "COMPLETED", "", "NORMAL_CONCLUSION"),
            NE010.ProjectionSnapshot(5, "flight_stage", "final_conclusion", ["Completed"], "completed", "COMPLETED", "", "NORMAL_CONCLUSION"),
        ]

        result = NE010.evaluate_flight("F2", "test", events, snapshots, "Done")
        self.assertFalse(result["hard_failure"])
        self.assertTrue(result["overall_pass"])

    def test_timeline_visibility_failure_detected(self):
        events = [
            {"event_type": "flight_stage", "payload": {"stage": "task_received"}},
            {"event_type": "model_request", "payload": {"model_name": "qwen3:1.7b", "provider_id": "ollama"}},
            {"event_type": "flight_stage", "payload": {"stage": "tool_request", "tool_name": "read_file", "arguments": {"path": "README.md"}}},
            {"event_type": "flight_stage", "payload": {"stage": "tool_result", "success": True, "tool_name": "read_file"}},
            {"event_type": "model_response", "payload": {"content": "Done", "tool_calls": None}},
            {"event_type": "flight_stage", "payload": {"stage": "final_conclusion", "content": "Done"}},
        ]
        # Simulate projection omissions for intermediate checkpoints.
        snapshots = [
            NE010.ProjectionSnapshot(0, "flight_stage", "task_received", ["Orienting"], "orienting", "UNKNOWN", "", "EMPTY"),
            NE010.ProjectionSnapshot(1, "model_request", None, [], "thinking", "UNKNOWN", "", "EMPTY"),
            NE010.ProjectionSnapshot(2, "flight_stage", "tool_request", [], "using", "UNKNOWN", "", "EMPTY"),
            NE010.ProjectionSnapshot(3, "flight_stage", "tool_result", [], "using", "UNKNOWN", "", "EMPTY"),
            NE010.ProjectionSnapshot(4, "model_response", None, [], "completed", "COMPLETED", "", "NORMAL_CONCLUSION"),
            NE010.ProjectionSnapshot(5, "flight_stage", "final_conclusion", ["Completed"], "completed", "COMPLETED", "", "NORMAL_CONCLUSION"),
        ]

        result = NE010.evaluate_flight("F3", "test", events, snapshots, "Done")
        self.assertFalse(result["hard_failure"])
        self.assertFalse(result["overall_pass"])
        visibility_dim = next(d for d in result["dimensions"] if d["name"] == "timeline_visibility_fidelity")
        self.assertFalse(visibility_dim["passed"])

    def test_blind_review_packet_hides_truth_metadata(self):
        artifact = {
            "flights": [
                {
                    "flight_id": "F1",
                    "prompt": "secret prompt",
                    "timeline": [
                        {
                            "t_plus_ms": 0.0,
                            "messages": ["Orienting"],
                            "expected_visible": True,
                        },
                        {
                            "t_plus_ms": 1200.0,
                            "messages": ["Blocked"],
                            "expected_visible": True,
                        },
                    ],
                }
            ]
        }

        packet = NE010.build_blind_review_packet(artifact)
        self.assertIn("Case A", packet)
        self.assertIn("T+0.00s", packet)
        self.assertIn("Orienting", packet)
        self.assertNotIn("secret prompt", packet)
        self.assertNotIn("truth", packet.lower())
        self.assertNotIn("projection", packet.lower())

    def test_export_review_packets_writes_truth_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            log_path = tmp / "trace.jsonl"
            artifact_path = tmp / "artifact.json"

            events = [
                {"time_epoch_ms": 1000.0, "event_type": "flight_stage", "payload": {"stage": "task_received"}},
                {"time_epoch_ms": 1100.0, "event_type": "model_request", "payload": {"model_name": "qwen3", "provider_id": "ollama"}},
                {"time_epoch_ms": 1200.0, "event_type": "model_response", "payload": {"content": "Can you clarify?", "tool_calls": None}},
                {"time_epoch_ms": 1300.0, "event_type": "flight_stage", "payload": {"stage": "final_conclusion", "content": "Can you clarify?"}},
            ]
            log_path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

            artifact = {
                "experiment_id": "NE-010",
                "profile": "harder",
                "timestamp": "2026-08-08T19:39:39",
                "log_file": str(log_path),
                "flights": [
                    {
                        "flight_id": "F1",
                        "prompt": "hidden prompt",
                        "event_span": [0, 4],
                        "timeline": [
                            {"t_plus_ms": 0.0, "messages": ["Orienting"], "expected_visible": True},
                            {"t_plus_ms": 100.0, "messages": ["Thinking"], "expected_visible": True},
                            {"t_plus_ms": 200.0, "messages": ["Clarifying"], "expected_visible": True},
                        ],
                    }
                ],
            }
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

            exported = NE010.export_review_packets(artifact_path)
            truth = json.loads(Path(exported["truth_key"]).read_text(encoding="utf-8"))
            reviewer_packet = Path(exported["reviewer_a"]).read_text(encoding="utf-8")

            self.assertEqual(truth["flights"][0]["case"], "A")
            self.assertEqual(truth["flights"][0]["truth"]["terminal_state"], "CLARIFYING")
            self.assertNotIn("hidden prompt", reviewer_packet)


if __name__ == "__main__":
    unittest.main()
