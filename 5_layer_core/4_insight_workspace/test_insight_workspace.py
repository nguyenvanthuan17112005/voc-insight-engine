"""Unit tests for Layer 4 Insight Workspace (INS 01 - INS 04)."""

import json
import tempfile
import unittest
from pathlib import Path

from insight_workspace_engine import build_report_bundle, search_evidence


class TestInsightWorkspace(unittest.TestCase):
    def test_permission_filter_and_grounded_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            snap_path = tmp_path / "measurement_snapshot.json"
            cls_path = tmp_path / "classifications.jsonl"
            out_dir = tmp_path / "out"

            snap = {
                "snapshot_id": "SNAP_TEST",
                "units": {
                    "item_count": 2,
                    "known_case_count": 2,
                    "known_customer_count": 2,
                    "unknown_event_time_items": 0,
                    "needs_review_items": 0,
                    "priority_flagged_items": 1,
                    "reviewed_items": 0,
                    "reviewed_coverage_pct": 0.0,
                },
                "survey_nps": {"available": False},
                "theme_metrics": [
                    {
                        "theme_id": "product_quality",
                        "theme_label": "Chất lượng",
                        "item_count": 2,
                        "case_count": 2,
                        "item_share_pct": 100.0,
                        "sentiment_breakdown": {"negative": 1, "positive": 1},
                    }
                ],
            }
            snap_path.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")

            recs = [
                {
                    "record_id": "R1",
                    "case_id": "C1",
                    "channel": "ticket",
                    "author_role": "customer",
                    "attribution_type": "customer_report",
                    "priority_flag": True,
                    "aspects": [{"theme_id": "product_quality", "sentiment": "negative", "evidence_span": "pin kém"}],
                },
                {
                    "record_id": "R2",
                    "case_id": "C2",
                    "channel": "email",
                    "author_role": "customer",
                    "attribution_type": "customer_report",
                    "priority_flag": False,
                    "aspects": [{"theme_id": "product_quality", "sentiment": "positive", "evidence_span": "máy mượt"}],
                },
            ]
            cls_path.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
                encoding="utf-8",
            )

            # Restrict search to ticket only -> R2 (email) must not appear
            ticket_only = search_evidence(cls_path, allowed_channels=["ticket"])
            self.assertEqual(len(ticket_only), 1)
            self.assertEqual(ticket_only[0]["record_id"], "R1")

            bundle = build_report_bundle(snap_path, cls_path, out_dir)
            self.assertEqual(bundle["status"], "draft")
            self.assertEqual(len(bundle["claims"]), 1)
            self.assertTrue((out_dir / "draft_report.md").exists())


if __name__ == "__main__":
    unittest.main()
