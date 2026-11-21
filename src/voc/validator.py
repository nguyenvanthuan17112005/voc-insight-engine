"""Kiểm tra file CSV đầu vào và lập manifest (DAT 02, DAT 03).

Nguyên tắc: không cắt cụt âm thầm, không tự điền ngày/khóa không rõ,
mọi dòng đều được tính vào accepted hoặc quarantined.
"""
import csv
from dataclasses import dataclass, field
from datetime import datetime

from .schemas import AUTHOR_ROLES, MAX_TEXT_CHARS, REQUIRED_VALUES, SCHEMAS


@dataclass
class Manifest:
    schema: str
    received: int = 0
    accepted: int = 0
    quarantined: int = 0
    duplicate_retries: int = 0
    unknown_date: int = 0
    unanalyzed: int = 0  # bị giữ lại trong hàng chờ review
    reasons: dict = field(default_factory=dict)
    accepted_rows: list = field(default_factory=list)
    quarantined_rows: list = field(default_factory=list)

    def reconcile(self, expected=None):
        """received phải bằng accepted + quarantined + duplicate_retries."""
        ok = self.received == self.accepted + self.quarantined + self.duplicate_retries
        if expected is not None:
            ok = ok and self.received == expected
        return ok

    def summary(self):
        return {
            "schema": self.schema, "received": self.received,
            "accepted": self.accepted, "quarantined": self.quarantined,
            "duplicate_retries": self.duplicate_retries,
            "unknown_date": self.unknown_date, "unanalyzed": self.unanalyzed,
            "reasons": self.reasons,
        }


def _parse_time(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _quarantine(m, row, reason):
    m.quarantined += 1
    m.reasons[reason] = m.reasons.get(reason, 0) + 1
    m.quarantined_rows.append({**row, "_reason": reason})


def validate_rows(rows, schema):
    if schema not in SCHEMAS:
        raise ValueError(f"Schema không hợp lệ: {schema}")
    m = Manifest(schema=schema)
    seen = {}  # (record_id, record_version) -> nội dung dòng
    for row in rows:
        m.received += 1
        if any(not (row.get(c) or "").strip() for c in REQUIRED_VALUES):
            _quarantine(m, row, "missing_required_value")
            continue
        key = (row["record_id"].strip(), row["record_version"].strip())
        if key in seen:
            if seen[key] == row:           # retry giống hệt: tự loại
                m.duplicate_retries += 1
            else:                           # cùng khóa nhưng khác nội dung
                _quarantine(m, row, "conflicting_duplicate_key")
            continue
        text = row.get("text") or ""
        has_rating = bool((row.get("rating") or "").strip())
        role = (row.get("author_role") or "unknown").strip() or "unknown"
        if role not in AUTHOR_ROLES:
            _quarantine(m, row, "invalid_author_role")
            continue
        if len(text) > MAX_TEXT_CHARS:
            m.unanalyzed += 1               # không cắt cụt, đưa vào hàng chờ
            _quarantine(m, row, "oversized_text")
            continue
        if not text.strip() and not has_rating:
            _quarantine(m, row, "empty_text_no_rating")
            continue
        if _parse_time(row.get("event_time")) is None:
            m.unknown_date += 1             # giữ nguyên unknown, không gán ngày nhập
        seen[key] = row
        m.accepted += 1
        m.accepted_rows.append(row)
    return m


def validate_file(path, schema):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in SCHEMAS[schema] if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Thiếu cột: {missing}")
        return validate_rows(list(reader), schema)
