import unittest
from pathlib import Path

from voc.schemas import MAX_TEXT_CHARS
from voc.validator import validate_file, validate_rows

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample"


class ValidatorSampleTests(unittest.TestCase):
    def test_service_case_sample(self):
        m = validate_file(SAMPLE / "service_case_feedback.csv", "service_case_feedback")
        self.assertEqual(m.received, 9)
        self.assertEqual(m.duplicate_retries, 1)       # S006 nhập lặp
        self.assertEqual(m.quarantined, 1)             # S008 không text, không rating
        self.assertEqual(m.accepted, 7)
        self.assertEqual(m.unknown_date, 1)            # S004 giữ unknown
        self.assertTrue(m.reconcile(expected=9))

    def test_rating_only_survey_is_accepted(self):
        m = validate_file(SAMPLE / "survey_response.csv", "survey_response")
        self.assertEqual(m.received, 4)
        self.assertEqual(m.accepted, 4)                # V002, V004 chỉ có rating
        self.assertTrue(m.reconcile())

    def test_correspondence_sample(self):
        m = validate_file(SAMPLE / "curated_correspondence.csv", "curated_correspondence")
        self.assertEqual(m.received, 5)
        self.assertEqual(m.accepted, 5)


class ValidatorRuleTests(unittest.TestCase):
    def row(self, **kw):
        base = {"record_id": "X1", "record_version": "1", "text": "ok",
                "event_time": "2026-10-01T00:00:00", "author_role": "customer"}
        base.update(kw)
        return base

    def test_oversized_text_is_never_truncated(self):
        long_text = "a" * (MAX_TEXT_CHARS + 1)
        m = validate_rows([self.row(text=long_text)], "service_case_feedback")
        self.assertEqual(m.quarantined, 1)
        self.assertEqual(m.unanalyzed, 1)
        self.assertEqual(m.quarantined_rows[0]["text"], long_text)  # nguyên bản

    def test_conflicting_duplicate_key(self):
        rows = [self.row(), self.row(text="khác")]
        m = validate_rows(rows, "service_case_feedback")
        self.assertEqual((m.accepted, m.quarantined), (1, 1))
        self.assertEqual(m.reasons["conflicting_duplicate_key"], 1)

    def test_missing_record_id(self):
        m = validate_rows([self.row(record_id="")], "service_case_feedback")
        self.assertEqual(m.reasons["missing_required_value"], 1)

    def test_invalid_role(self):
        m = validate_rows([self.row(author_role="robot")], "service_case_feedback")
        self.assertEqual(m.reasons["invalid_author_role"], 1)

    def test_unknown_schema(self):
        with self.assertRaises(ValueError):
            validate_rows([], "khong_ton_tai")


if __name__ == "__main__":
    unittest.main()
