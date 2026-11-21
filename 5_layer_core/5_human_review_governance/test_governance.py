"""Unit tests for Layer 5 Human Review & Governance (INS 05 - INS 08)."""

import json
import tempfile
import unittest
from pathlib import Path

from governance_engine import GovernanceEngine


class TestGovernanceEngine(unittest.TestCase):
    def test_report_approval_and_supersede_on_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bundle_path = tmp_path / "report_bundle.json"
            bundle_path.write_text(
                json.dumps({"report_id": "RPT_01", "snapshot_id": "SNAP_01"}),
                encoding="utf-8",
            )

            gov = GovernanceEngine(tmp_path / "gov")
            entry = gov.register_report(bundle_path)
            self.assertEqual(entry["status"], "draft")

            gov.transition_report("RPT_01", "under_review", "Manager_A")
            approved = gov.transition_report("RPT_01", "approved", "Manager_A", "Verified numbers")
            self.assertEqual(approved["status"], "approved")

            # Human label correction must supersede approved report (INS 05, INS 08)
            corr = gov.record_label_correction(
                record_id="REC_01",
                reviewer="Staff_B",
                old_theme="product_quality",
                new_theme="safety_incident",
                old_sentiment="negative",
                new_sentiment="negative",
                reason="Explicit overheat report",
            )
            self.assertTrue(corr["auto_retrain_blocked"])

            reg = json.loads((tmp_path / "gov" / "report_registry.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["reports"]["RPT_01"]["status"], "superseded")

    def test_internal_action_register_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gov = GovernanceEngine(Path(tmp))
            act = gov.propose_action(
                action_id="ACT_01",
                theme_id="technical_support",
                title="Rà soát quy trình kiểm tra sau bảo trì",
                evidence_record_ids=["REC_SC_00001"],
                owner="Engineering_Lead",
                review_date="2026-12-01",
            )
            self.assertTrue(act["internal_only"])
            self.assertFalse(act["external_customer_messaging"])

            gov.update_action_status("ACT_01", "accepted")
            gov.update_action_status("ACT_01", "implemented")
            reviewed = gov.update_action_status(
                "ACT_01", "outcome_reviewed", "Đã cập nhật checklist bảo trì v2"
            )
            self.assertEqual(reviewed["status"], "outcome_reviewed")


if __name__ == "__main__":
    unittest.main()
