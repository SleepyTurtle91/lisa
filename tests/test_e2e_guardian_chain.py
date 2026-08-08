import unittest

from benchmarks.e2e_guardian_chain import derive_guardian_decision


class E2EGuardianChainTests(unittest.TestCase):
    def test_strong_evidence_yields_act(self) -> None:
        payload = {
            "candidates": [
                {
                    "id": "session-context-validation",
                    "confidence": 0.86,
                    "support": 6,
                    "contradictions": 0,
                    "notes": "Concrete runtime evidence and a clear contract violation."
                }
            ]
        }
        decision = derive_guardian_decision(payload)
        self.assertEqual(decision["decision"], "ACT")
        self.assertGreaterEqual(decision["confidence"], 0.8)

    def test_weak_evidence_yields_abstain(self) -> None:
        payload = {
            "candidates": [
                {
                    "id": "speculative-target",
                    "confidence": 0.36,
                    "support": 2,
                    "contradictions": 3,
                    "notes": "Partial observations but no concrete defect signature."
                }
            ]
        }
        decision = derive_guardian_decision(payload)
        self.assertEqual(decision["decision"], "ABSTAIN")
        self.assertLess(decision["evidence_confidence"], 0.7)


if __name__ == "__main__":
    unittest.main()
