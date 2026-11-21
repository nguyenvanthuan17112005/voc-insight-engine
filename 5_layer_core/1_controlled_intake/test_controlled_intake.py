"""Acceptance tests for Layer 1 Controlled Intake Engine (DAT 01 - DAT 08, SEC 03)."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from controlled_intake_engine import (
    ControlledIntakeEngine,
    redact_pii,
    scan_priority,
    strip_quoted_history,
)


class TestControlledIntakeEngine(unittest.TestCase):
    def test_strip_quoted_history_preserves_main_text(self) -> None:
        raw = (
            "Kính gửi SongNhat,\n\nĐộng cơ giao chậm 3 ngày.\n\n"
            "-----Original Message-----\nFrom: sales@songnhat.vn\nNội dung cũ"
        )
        main, excluded, reason = strip_quoted_history(raw)
        self.assertIn("Động cơ giao chậm 3 ngày.", main)
        self.assertNotIn("Original Message", main)
        self.assertIn("Original Message", excluded)
        self.assertEqual(reason, "quoted_email_history")

    def test_pii_redaction(self) -> None:
        raw = "Liên hệ anh An qua SĐT 0912345678 hoặc an.nguyen@abc.vn.\n\nTrân trọng,\nNguyễn Văn An"
        redacted = redact_pii(raw)
        self.assertNotIn("0912345678", redacted)
        self.assertNotIn("an.nguyen@abc.vn", redacted)
        self.assertNotIn("Nguyễn Văn An", redacted)
        self.assertIn("[REDACTED_PHONE]", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)
        self.assertIn("[REDACTED_NAME]", redacted)

    def test_priority_scan(self) -> None:
        flagged, labels = scan_priority("Động cơ quá nhiệt và có mùi khét.")
        self.assertTrue(flagged)
        self.assertIn("overheat", labels)
        self.assertIn("fire_hazard", labels)

    def test_end_to_end_idempotency_and_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            in_dir = tmp_path / "in"
            out_dir = tmp_path / "out"
            in_dir.mkdir()

            manifest = {
                "batch_id": "TEST_B1",
                "source_version": "v1.0",
                "load_mode": "snapshot",
                "cutoff_time": "2026-11-20T08:00:00",
                "extraction_time": "2026-11-01T08:00:00",
                "expected_rows": {
                    "service_case_feedback.csv": 2,
                    "curated_correspondence.csv": 1,
                    "survey_responses.csv": 1,
                },
                "deletion_tombstones": ["REC_DEL_1"],
                "files": [
                    "service_case_feedback.csv",
                    "curated_correspondence.csv",
                    "survey_responses.csv",
                ],
            }
            (in_dir / "batch_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            with (in_dir / "service_case_feedback.csv").open(
                "w", encoding="utf-8", newline=""
            ) as f:
                w = csv.writer(f)
                w.writerow(["record_id", "case_id", "customer_id", "channel", "event_time", "author_role", "text", "product_id"])
                w.writerow(["SC_1", "C1", "unknown", "ticket", "2026-11-20T07:00:00", "customer", "Động cơ quá nhiệt", "P1"])
                w.writerow(["SC_2", "C2", "CUST_2", "ticket", "2026-11-20T07:00:00", "customer", "A" * 8001, "P1"])

            with (in_dir / "curated_correspondence.csv").open(
                "w", encoding="utf-8", newline=""
            ) as f:
                w = csv.writer(f)
                w.writerow(["record_id", "case_id", "customer_id", "channel", "event_time", "author_role", "text", "subject"])
                w.writerow(["CORR_1", "C3", "CUST_3", "email", "2026-11-20T07:00:00", "customer", "Email 0987654321", "Fwd: Test"])

            with (in_dir / "survey_responses.csv").open(
                "w", encoding="utf-8", newline=""
            ) as f:
                w = csv.writer(f)
                w.writerow(["record_id", "customer_id", "channel", "event_time", "rating", "text"])
                w.writerow(["SRV_1", "CUST_4", "survey", "unknown", "9", "Tốt"])

            engine = ControlledIntakeEngine(output_dir=out_dir)
            report1 = engine.process_batch(in_dir)
            self.assertTrue(report1["is_stale"])
            self.assertEqual(report1["deletion_tombstones_processed"], 1)
            sc_rec = report1["reconciliation"][0]
            self.assertEqual(sc_rec["rows_accepted"], 1)
            self.assertEqual(sc_rec["rows_quarantined"], 1)
            self.assertEqual(sc_rec["rows_unanalyzed"], 1)
            self.assertEqual(sc_rec["unknown_customer_count"], 1)

            # Retry same batch -> idempotent suppression
            report2 = engine.process_batch(in_dir)
            sc_rec2 = report2["reconciliation"][0]
            self.assertEqual(sc_rec2["rows_accepted"], 0)
            self.assertEqual(sc_rec2["rows_quarantined"], 2)


if __name__ == "__main__":
    unittest.main()
