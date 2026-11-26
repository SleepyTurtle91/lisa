import sys
import tempfile
import unittest
from pathlib import Path
from dataclasses import is_dataclass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lisa.projects import ProjectExecutor, ProjectOperation, ProjectRegistry, ProjectRequest
from lisa.projects.capability import CapabilityEvidence, CapabilityMatch
from lisa.projects.capability_discovery import CapabilityDiscoveryExecutor
from lisa.projects.capability_request import CapabilityDiscoveryRequest
from lisa.projects.capability_result import CapabilityDiscoveryResult


class TestCapabilityDiscovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.registry = ProjectRegistry()
        self.register = ProjectExecutor(registry=self.registry)

        self.source = self.root / "source_pos"
        self.source.mkdir()
        (self.source / "README.md").write_text(
            "# Retail capabilities\nInventory management supports stocktake and stock control.",
            encoding="utf-8",
        )
        (self.source / "src" / "inventory").mkdir(parents=True)
        (self.source / "src" / "inventory" / "stocktake.kt").write_text(
            "class Stocktake {}", encoding="utf-8"
        )

        self.target = self.root / "target_app"
        self.target.mkdir()
        (self.target / "README.md").write_text(
            "# Customer application\nCustomer profiles and CRM workflows.",
            encoding="utf-8",
        )

        self.source_id = self.register.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(self.source)
        )).manifest.project_id
        self.target_id = self.register.execute(ProjectRequest(
            operation=ProjectOperation.REGISTER, path=str(self.target)
        )).manifest.project_id
        self.discovery = CapabilityDiscoveryExecutor(registry=self.registry)

    def test_finds_matching_source_project_with_evidence(self):
        result = self.discovery.execute(CapabilityDiscoveryRequest(
            query="inventory stocktake"
        ))
        self.assertTrue(result.success, result.error)
        self.assertEqual(len(result.matches), 1)
        match = result.matches[0]
        self.assertEqual(match.project_id, self.source_id)
        self.assertEqual(set(match.matched_terms), {"inventory", "stocktake"})
        self.assertTrue(any(item.relative_path == "README.md" for item in match.evidence))
        self.assertTrue(any("stocktake" in path for path in match.source_paths))
        self.assertEqual(match.score, 1.0)

    def test_normalizes_underscore_aliases_for_matching_and_evidence(self):
        readme = self.source / "README.md"
        readme.write_text(
            "# Retail capabilities\nMy_Invois integration supports e-invoice submission.",
            encoding="utf-8",
        )
        result = self.discovery.execute(CapabilityDiscoveryRequest(query="einvoice"))
        self.assertTrue(result.success, result.error)
        self.assertEqual([item.project_id for item in result.matches], [self.source_id])
        self.assertIn("einvoice", result.matches[0].matched_terms)
        self.assertTrue(any(item.relative_path == "README.md" for item in result.matches[0].evidence))

    def test_generic_invoice_evidence_does_not_match_einvoice_query(self):
        (self.target / "README.md").write_text(
            "# Billing\nInvoice history and invoice reports.",
            encoding="utf-8",
        )
        result = self.discovery.execute(CapabilityDiscoveryRequest(query="einvoice"))
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.matches, ())

    def test_compound_alias_cannot_be_assembled_from_unrelated_evidence_units(self):
        (self.source / "README.md").write_text(
            "# Retail capabilities\\nStock control and stock adjustments.",
            encoding="utf-8",
        )
        (self.source / "src" / "inventory" / "stocktake.kt").unlink()
        take_dir = self.source / "src" / "take"
        take_dir.mkdir()
        (take_dir / "Report.kt").write_text("class Report {}", encoding="utf-8")

        result = self.discovery.execute(CapabilityDiscoveryRequest(query="stocktake"))
        self.assertTrue(result.success, result.error)
        self.assertNotIn(self.source_id, [item.project_id for item in result.matches])

    def test_einvoice_matches_prefixed_snake_case_source_identifiers(self):
        billing = self.source / "src" / "billing"
        billing.mkdir()
        source_file = billing / "create_e_invoice.py"
        source_file.write_text("def submit(): pass", encoding="utf-8")

        result = self.discovery.execute(CapabilityDiscoveryRequest(query="einvoice"))
        self.assertTrue(result.success, result.error)
        match = next(item for item in result.matches if item.project_id == self.source_id)
        self.assertIn("einvoice", match.matched_terms)
        self.assertIn("src/billing/create_e_invoice.py", match.source_paths)

    def test_each_evidence_excerpt_is_tokenized_once_for_multi_term_query(self):
        class CountingDiscovery(CapabilityDiscoveryExecutor):
            excerpt_tokenizations = 0
            expected_excerpt = ""

            @classmethod
            def _tokens(cls, text):
                if text == cls.expected_excerpt:
                    cls.excerpt_tokenizations += 1
                return super()._tokens(text)

        CountingDiscovery.expected_excerpt = (self.source / "README.md").read_text(encoding="utf-8")
        counting = CountingDiscovery(
            registry=self.registry,
            profile_executor=self.discovery._profiles,
        )
        result = counting.execute(CapabilityDiscoveryRequest(query="inventory stocktake"))
        self.assertTrue(result.success, result.error)
        self.assertEqual(CountingDiscovery.excerpt_tokenizations, 1)

    def test_can_scope_discovery_to_selected_projects(self):
        result = self.discovery.execute(CapabilityDiscoveryRequest(
            query="customer crm", project_ids=(self.target_id,)
        ))
        self.assertTrue(result.success, result.error)
        self.assertEqual([item.project_id for item in result.matches], [self.target_id])

    def test_discovery_contracts_are_frozen_dataclasses(self):
        for contract in (
            CapabilityEvidence, CapabilityMatch,
            CapabilityDiscoveryRequest, CapabilityDiscoveryResult,
        ):
            with self.subTest(contract=contract.__name__):
                self.assertTrue(is_dataclass(contract))
                self.assertTrue(contract.__dataclass_params__.frozen)

    def test_unknown_project_scope_and_empty_query_fail_safely(self):
        unknown = self.discovery.execute(CapabilityDiscoveryRequest(
            query="inventory", project_ids=("prj_missing",)
        ))
        empty = self.discovery.execute(CapabilityDiscoveryRequest(query="the and or"))
        self.assertFalse(unknown.success)
        self.assertFalse(empty.success)


if __name__ == "__main__":
    unittest.main()
