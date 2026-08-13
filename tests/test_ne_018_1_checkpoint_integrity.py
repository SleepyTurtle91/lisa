"""
Unit tests for NE-018.1 Knowledge Checkpoint Integrity.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.benchmarks.ne_018_1_checkpoint_integrity import KnowledgeCheckpointVerifier, ProvenanceKnowledgeItem


class TestKnowledgeCheckpointIntegrity(unittest.TestCase):
    def test_superficial_checkpoint_rejected(self):
        items = [
            ProvenanceKnowledgeItem("Project Identity", "Unverified prose", "unverified", False),
        ]
        cp = KnowledgeCheckpointVerifier.verify_checkpoint(items)
        self.assertFalse(cp.is_authorized)
        self.assertLess(cp.integrity_score, 0.7)

    def test_authoritative_checkpoint_authorized(self):
        items = [
            ProvenanceKnowledgeItem(d, f"Fact for {d}", "observed_tool", True)
            for d in KnowledgeCheckpointVerifier.REQUIRED_DOMAINS
        ]
        cp = KnowledgeCheckpointVerifier.verify_checkpoint(items)
        self.assertTrue(cp.is_authorized)
        self.assertEqual(cp.integrity_score, 1.0)


if __name__ == "__main__":
    unittest.main()
