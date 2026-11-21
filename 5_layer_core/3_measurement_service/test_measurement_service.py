"""Unit tests for Layer 3 Measurement Service (DAT 06 - DAT 08, ANL 07, Annex C)."""

import json
import tempfile
import unittest
from pathlib import Path

from measurement_service_engine import calculate_nps, run_measurement


class TestMeasurementService(unittest.TestCase):
    def test_nps_formula_keeps_passives_in_denominator(self) -> None:
        # 2 promoters (9,10), 1 passive (7), 1 detractor (5) -> (50% - 25%) = 25.0
        res = calculate_nps([9, 10, 7, 5])
        self.assertTrue(res["available"])
        self.assertEqual(res["valid_responses"], 4)
        self.assertEqual(res["nps_score"], 25.0)
        self.assertFalse(calculate_nps([])["available"])

    def test_units_unknown_dates_and_invalidation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cls_path = tmp_path / "classifications.jsonl"
            inv_path = tmp_path / "invalidation_events.jsonl"
            out_dir = tmp_path / "out"

            records = [
                {
                    "record_id": "R1",
                    "case_id": "C1",
                    "customer_id": "CUST_1",
                    "channel": "survey",
                    "event_time": "2026-11-05T10:00:00",
                    "rating": "10",
                    "label_stage": "draft",
                    "aspects": [{"theme_id": "product_quality", "theme_label": "PQ", "sentiment": "positive", "evidence_span": "tốt"}],
                    "needs_review": False,
                    "priority_flag": False,
                },
                {
                    "record_id": "R2",
                    "case_id": "unknown",
                    "customer_id": "unknown",
                    "channel": "ticket",
                    "event_time": "unknown",
                    "rating": "",
                    "label_stage": "draft",
                    "aspects": [{"theme_id": "product_quality", "theme_label": "PQ", "sentiment": "negative", "evidence_span": "lỗi"}],
                    "needs_review": False,
                    "priority_flag": True,
                },
            ]
            cls_path.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
                encoding="utf-8",
            )
            inv_path.write_text(
                json.dumps({"event_type": "DELETION_TOMBSTONE", "record_id": "R2", "batch_id": "B2"}) + "\n",
                encoding="utf-8",
            )

            snap = run_measurement(cls_path, out_dir, invalidation_path=inv_path)
            # R2 deleted by tombstone -> only R1 active
            self.assertEqual(snap["units"]["item_count"], 1)
            self.assertEqual(snap["units"]["known_case_count"], 1)
            self.assertEqual(snap["units"]["known_customer_count"], 1)
            self.assertEqual(snap["survey_nps"]["nps_score"], 100.0)


if __name__ == "__main__":
    unittest.main()
