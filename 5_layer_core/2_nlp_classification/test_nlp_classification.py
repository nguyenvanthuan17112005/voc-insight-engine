"""Unit tests for Layer 2 NLP & Classification Engine (ANL 01 - ANL 05)."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from nlp_classification_engine import (
    DeterministicLexiconClassifier,
    classify_records,
    score_local_sentiment,
)

TAXONOMY_PATH = Path(__file__).parent / "taxonomy_v1.json"


class TestNLPClassification(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = DeterministicLexiconClassifier(TAXONOMY_PATH)

    def test_negation_flips_positive_to_negative(self) -> None:
        self.assertEqual(score_local_sentiment("máy không tốt chút nào"), "negative")
        self.assertEqual(score_local_sentiment("nhân viên rất nhiệt tình"), "positive")

    def test_mixed_aspect_sentiment_and_span(self) -> None:
        text = "Báo giá rõ ràng nhưng giao hàng quá chậm."
        preds = self.classifier.predict(text)
        theme_ids = {p.theme_id for p in preds}
        self.assertIn("pricing_quotation", theme_ids)
        self.assertIn("delivery_leadtime", theme_ids)
        for p in preds:
            self.assertEqual(text[p.span_start : p.span_end], p.evidence_span)

    def test_abstention_and_priority_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            in_dir = tmp_path / "in"
            out_dir = tmp_path / "out"
            in_dir.mkdir()

            with (in_dir / "normalized_service_case_feedback.csv").open(
                "w", encoding="utf-8", newline=""
            ) as f:
                w = csv.writer(f)
                w.writerow(["record_id", "case_id", "customer_id", "channel", "event_time", "author_role", "text", "priority_flag", "priority_keywords"])
                w.writerow(["R1", "C1", "CUST_1", "ticket", "2026-11-20T08:00:00", "customer", "Xin chào", "True", "urgent_outage"])
                w.writerow(["R2", "C2", "CUST_2", "ticket", "2026-11-20T09:00:00", "staff_note", "Động cơ quá nhiệt khi tải cao", "False", ""])

            summary = classify_records(in_dir, out_dir, self.classifier, self.classifier.taxonomy_version)
            self.assertEqual(summary["total_records_classified"], 2)
            self.assertEqual(summary["needs_review_count"], 1)
            self.assertEqual(summary["priority_flagged_count"], 2)

            rows = [json.loads(line) for line in (out_dir / "classifications.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(rows[0]["needs_review"])
            self.assertTrue(rows[0]["priority_flag"])
            self.assertEqual(rows[1]["attribution_type"], "staff_observation")


if __name__ == "__main__":
    unittest.main()
