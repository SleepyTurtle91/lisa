import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.benchmarks.registry import (
    ExperimentRegistry,
    RawEvidence,
    DerivedMeasurements,
    ResearchInterpretation
)

class TestExperimentRegistry(unittest.TestCase):
    def test_save_and_list_experiment(self):
        raw = RawEvidence(
            experiment_id="TEST-001",
            timestamp="2026-08-08T10:30:00",
            brain_model="qwen3:1.7b",
            hardware_context="RTX 3060 16GB",
            task_id="T1_test",
            prompt="Test prompt",
            scaffolding_applied="Level 2",
            available_tools=["read_file"],
            latency_ms=1234.5,
            prompt_tokens=100,
            completion_tokens=50,
            tool_calls_count=1,
            tool_calls_successful=True,
            hallucination_detected=False,
            response_excerpt="Test response excerpt"
        )
        derived = DerivedMeasurements(
            success_rate_pct=100.0,
            tool_adherence_pct=100.0,
            hallucination_rate_pct=0.0,
            tok_sec=40.5
        )
        interpretation = ResearchInterpretation(
            observation="Test observation",
            hypothesis_evaluated="Test hypothesis",
            evidence_class="Unit Test",
            confidence_level="High",
            limitations="None",
            next_question="What is next?"
        )
        
        path = ExperimentRegistry.save_experiment(raw, derived, interpretation)
        self.assertTrue(path.exists())
        
        # Cleanup test artifact
        try:
            os.remove(path)
        except Exception:
            pass

if __name__ == "__main__":
    unittest.main()
