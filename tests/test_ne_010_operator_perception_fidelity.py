import importlib.util
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


if __name__ == "__main__":
    unittest.main()
