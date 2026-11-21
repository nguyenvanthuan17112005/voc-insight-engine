"""Layer 1: Controlled Intake Engine (DAT 01 - DAT 08, SEC 03, B 01, Annex C)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MAX_ANALYZABLE_CHARS = 8000
QUOTE_STRIP_RULE_VERSION = "quote-strip-v1.0.0"
REDACTION_VERSION = "pii-redact-v1.0.0"
PRIORITY_RULE_VERSION = "priority-scan-v1.0.0"

REQUIRED_SCHEMAS: Dict[str, List[str]] = {
    "service_case_feedback.csv": [
        "record_id",
        "case_id",
        "customer_id",
        "channel",
        "event_time",
        "author_role",
        "text",
        "product_id",
    ],
    "curated_correspondence.csv": [
        "record_id",
        "case_id",
        "customer_id",
        "channel",
        "event_time",
        "author_role",
        "text",
        "subject",
    ],
    "survey_responses.csv": [
        "record_id",
        "customer_id",
        "channel",
        "event_time",
        "rating",
        "text",
    ],
}

VALID_AUTHOR_ROLES = {"customer", "staff_note", "unknown"}
VALID_LOAD_MODES = {"snapshot", "increment"}

PRIORITY_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("overheat", re.compile(r"quá nhiệt|nóng bất thường", re.IGNORECASE)),
    ("fire_hazard", re.compile(r"cháy nổ|mùi khét|bốc khói|chập điện", re.IGNORECASE)),
    ("safety_risk", re.compile(r"mất an toàn|tai nạn|nguy hiểm|rò rỉ", re.IGNORECASE)),
    ("urgent_outage", re.compile(r"ngừng hoạt động|dừng dây chuyền|khẩn cấp", re.IGNORECASE)),
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+84|84|0)(?:3|5|7|8|9|2\d)\d{7,8}(?!\d)")
SIGNATURE_NAME_RE = re.compile(
    r"(Trân trọng,\s*\n)([^\n\r]{2,60})", re.IGNORECASE
)
QUOTED_HISTORY_RE = re.compile(
    r"(\r?\n\s*-{3,}\s*Original Message\s*-{3,}.*|\r?\n\s*On .+ wrote:\s*.*)",
    re.DOTALL | re.IGNORECASE,
)


def parse_iso_datetime(value: str) -> Optional[datetime]:
    """Parse ISO 8601 string or return None if invalid or 'unknown'."""
    val = (value or "").strip()
    if not val or val.lower() == "unknown":
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def count_business_days(start: datetime, end: datetime) -> int:
    """Count weekdays between start and end."""
    if end <= start:
        return 0
    days = 0
    cur = start.date()
    end_date = end.date()
    while cur < end_date:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            days += 1
    return days


def strip_quoted_history(text: str) -> Tuple[str, str, str]:
    """Strip quoted email history using a versioned rule while preserving original."""
    match = QUOTED_HISTORY_RE.search(text)
    if not match:
        return text, "", ""
    idx = match.start()
    return text[:idx].rstrip(), text[idx:], "quoted_email_history"


def redact_pii(text: str) -> str:
    """Redact emails, phone numbers, and signature contact names (SEC 03)."""
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = SIGNATURE_NAME_RE.sub(r"\1[REDACTED_NAME]", redacted)
    return redacted


def scan_priority(text: str) -> Tuple[bool, List[str]]:
    """Run deterministic priority keyword scan on parseable text (B 01, ANL 05)."""
    matched: List[str] = []
    for label, pattern in PRIORITY_PATTERNS:
        if pattern.search(text):
            matched.append(label)
    return bool(matched), matched


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_audience(author_role: str) -> str:
    if author_role == "staff_note":
        return "internal_staff"
    if author_role == "customer":
        return "external_customer"
    return "unknown"


@dataclass
class BatchReconciliation:
    source_file: str
    rows_expected: int
    rows_received: int = 0
    rows_accepted: int = 0
    rows_quarantined: int = 0
    rows_unanalyzed: int = 0
    unknown_event_time_count: int = 0
    unknown_customer_count: int = 0
    stale_count: int = 0
    priority_flagged_count: int = 0
    status: str = "VERIFIED"


@dataclass
class ControlledIntakeEngine:
    output_dir: Path
    max_chars: int = MAX_ANALYZABLE_CHARS
    state: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.original_dir = self.output_dir / "immutable_original_store"
        self.normalized_dir = self.output_dir / "normalized_store"
        self.quarantine_dir = self.output_dir / "quarantine_queue"
        for d in (self.original_dir, self.normalized_dir, self.quarantine_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.state_path = self.normalized_dir / "intake_state.json"
        self.invalidation_path = self.normalized_dir / "invalidation_events.jsonl"
        self._load_state()

    def _load_state(self) -> None:
        if self.state_path.exists():
            with self.state_path.open("r", encoding="utf-8") as f:
                self.state = json.load(f)
        else:
            self.state = {
                "records": {},
                "content_hashes": {},
                "batches": [],
            }

    def _save_state(self) -> None:
        with self.state_path.open("w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def validate_manifest(self, manifest: Dict[str, Any]) -> None:
        required_keys = {
            "batch_id",
            "source_version",
            "load_mode",
            "cutoff_time",
            "extraction_time",
            "expected_rows",
            "files",
        }
        missing = required_keys - set(manifest.keys())
        if missing:
            raise ValueError(f"Manifest missing required keys: {sorted(missing)}")
        if manifest["load_mode"] not in VALID_LOAD_MODES:
            raise ValueError(f"Invalid load_mode: {manifest['load_mode']}")
        if parse_iso_datetime(manifest["extraction_time"]) is None:
            raise ValueError(f"Invalid extraction_time: {manifest['extraction_time']}")
        if parse_iso_datetime(manifest["cutoff_time"]) is None:
            raise ValueError(f"Invalid cutoff_time: {manifest['cutoff_time']}")

    def _process_tombstones(
        self, tombstones: List[str], batch_id: str, import_time: str
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for rec_id in tombstones:
            existing = self.state["records"].get(rec_id)
            if existing:
                existing["status"] = "DELETED"
                existing["deleted_in_batch"] = batch_id
            else:
                self.state["records"][rec_id] = {
                    "status": "DELETED",
                    "deleted_in_batch": batch_id,
                    "record_version": 0,
                }
            events.append(
                {
                    "event_type": "DELETION_TOMBSTONE",
                    "record_id": rec_id,
                    "case_id": existing.get("case_id", "unknown") if existing else "unknown",
                    "batch_id": batch_id,
                    "import_time": import_time,
                    "action": "INVALIDATE_AFFECTED_AGGREGATES",
                }
            )
        return events

    def process_batch(self, input_dir: Path) -> Dict[str, Any]:
        manifest_path = input_dir / "batch_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing batch_manifest.json in {input_dir}")

        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.validate_manifest(manifest)

        batch_id = manifest["batch_id"]
        source_version = manifest["source_version"]
        extraction_time_str = manifest["extraction_time"]
        extraction_dt = parse_iso_datetime(extraction_time_str)
        import_dt = datetime.now()
        import_time_str = import_dt.isoformat(timespec="seconds")
        is_stale = bool(
            extraction_dt and count_business_days(extraction_dt, import_dt) > 2
        )

        invalidation_events = self._process_tombstones(
            manifest.get("deletion_tombstones", []), batch_id, import_time_str
        )

        reconciliations: List[BatchReconciliation] = []
        missing_files: List[str] = []

        for filename, required_cols in REQUIRED_SCHEMAS.items():
            file_path = input_dir / filename
            expected_count = int(manifest.get("expected_rows", {}).get(filename, 0))
            rec = BatchReconciliation(source_file=filename, rows_expected=expected_count)

            if not file_path.exists():
                rec.status = "MISSING_FEED"
                missing_files.append(filename)
                reconciliations.append(rec)
                continue

            accepted_rows: List[Dict[str, Any]] = []
            quarantined_rows: List[Dict[str, Any]] = []
            original_rows: List[Dict[str, Any]] = []

            with file_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                header = reader.fieldnames or []
                missing_cols = [c for c in required_cols if c not in header]
                if missing_cols:
                    raise ValueError(f"{filename} missing columns: {missing_cols}")

                for row_idx, row in enumerate(reader, start=1):
                    rec.rows_received += 1
                    record_id = (row.get("record_id") or "").strip()
                    raw_text = row.get("text") or ""
                    customer_id = (row.get("customer_id") or "").strip() or "unknown"
                    event_time_raw = (row.get("event_time") or "").strip() or "unknown"
                    author_role = (
                        (row.get("author_role") or "").strip()
                        if "author_role" in required_cols
                        else "customer"
                    )

                    # Step 1: Schema validation
                    if not record_id:
                        quarantined_rows.append(
                            {**row, "quarantine_reason": "Missing record_id (DAT 01)"}
                        )
                        rec.rows_quarantined += 1
                        rec.rows_unanalyzed += 1
                        continue

                    if author_role not in VALID_AUTHOR_ROLES:
                        quarantined_rows.append(
                            {**row, "quarantine_reason": f"Invalid author_role: {author_role}"}
                        )
                        rec.rows_quarantined += 1
                        rec.rows_unanalyzed += 1
                        continue

                    if event_time_raw.lower() != "unknown" and parse_iso_datetime(event_time_raw) is None:
                        quarantined_rows.append(
                            {**row, "quarantine_reason": f"Invalid ISO 8601 event_time: {event_time_raw}"}
                        )
                        rec.rows_quarantined += 1
                        rec.rows_unanalyzed += 1
                        continue

                    if filename == "survey_responses.csv":
                        rating_raw = (row.get("rating") or "").strip()
                        if rating_raw:
                            try:
                                r_val = float(rating_raw)
                                if r_val < 0 or r_val > 10:
                                    raise ValueError("out of range")
                            except ValueError:
                                quarantined_rows.append(
                                    {**row, "quarantine_reason": f"Invalid survey rating: {rating_raw}"}
                                )
                                rec.rows_quarantined += 1
                                rec.rows_unanalyzed += 1
                                continue

                    # Step 2: Idempotency & Duplicate check (DAT 02, DAT 05)
                    content_hash = compute_sha256(raw_text)
                    prev_rec = self.state["records"].get(record_id)
                    if prev_rec:
                        if prev_rec.get("status") == "DELETED":
                            quarantined_rows.append(
                                {**row, "quarantine_reason": "Record previously deleted via tombstone (DAT 02)"}
                            )
                            rec.rows_quarantined += 1
                            rec.rows_unanalyzed += 1
                            continue
                        if prev_rec.get("content_hash") == content_hash:
                            quarantined_rows.append(
                                {**row, "quarantine_reason": "Idempotent retry suppressed (DAT 02/DAT 05)"}
                            )
                            rec.rows_quarantined += 1
                            continue
                        # Source edit detected -> invalidate downstream (DAT 08)
                        invalidation_events.append(
                            {
                                "event_type": "SOURCE_CORRECTION",
                                "record_id": record_id,
                                "case_id": row.get("case_id", "unknown"),
                                "batch_id": batch_id,
                                "import_time": import_time_str,
                                "action": "INVALIDATE_AFFECTED_AGGREGATES",
                            }
                        )

                    seen_hash_owner = self.state["content_hashes"].get(content_hash)
                    review_flag = ""
                    if seen_hash_owner and seen_hash_owner != record_id:
                        quarantined_rows.append(
                            {
                                **row,
                                "quarantine_reason": f"Duplicate content SHA-256 of {seen_hash_owner} (DAT 05)",
                            }
                        )
                        rec.rows_quarantined += 1
                        continue

                    subject = (row.get("subject") or "").strip()
                    if subject.lower().startswith("fwd:"):
                        review_flag = "POTENTIAL_FORWARD_OR_REPEAT"

                    # Step 4: Quoted history rule & 8,000 char limit (DAT 03)
                    analyzable_text, excluded_text, exclusion_reason = strip_quoted_history(raw_text)
                    if not analyzable_text.strip():
                        quarantined_rows.append(
                            {**row, "quarantine_reason": "Empty analyzable text (DAT 03)"}
                        )
                        rec.rows_quarantined += 1
                        rec.rows_unanalyzed += 1
                        continue

                    if len(analyzable_text) > self.max_chars:
                        quarantined_rows.append(
                            {
                                **row,
                                "quarantine_reason": f"Exceeds {self.max_chars} Unicode chars ({len(analyzable_text)}) - no silent truncation (DAT 03)",
                            }
                        )
                        rec.rows_quarantined += 1
                        rec.rows_unanalyzed += 1
                        continue

                    # Step 5: PII Redaction & Priority Scan (SEC 03, B 01)
                    redacted_text = redact_pii(analyzable_text)
                    priority_flag, priority_keywords = scan_priority(analyzable_text)

                    # Step 3: Lineage & Isolation metrics (DAT 01, DAT 04, DAT 07)
                    if event_time_raw.lower() == "unknown":
                        rec.unknown_event_time_count += 1
                    if customer_id.lower() == "unknown":
                        rec.unknown_customer_count += 1
                    if is_stale:
                        rec.stale_count += 1
                    if priority_flag:
                        rec.priority_flagged_count += 1

                    record_version = (prev_rec.get("record_version", 0) + 1) if prev_rec else 1
                    self.state["records"][record_id] = {
                        "record_version": record_version,
                        "source_version": source_version,
                        "content_hash": content_hash,
                        "case_id": row.get("case_id", "unknown"),
                        "status": "ACTIVE",
                    }
                    self.state["content_hashes"][content_hash] = record_id

                    original_rows.append(
                        {
                            "record_id": record_id,
                            "batch_id": batch_id,
                            "source_version": source_version,
                            "record_version": record_version,
                            "passage_anchor": f"{filename}:row:{row_idx}",
                            "original_text": raw_text,
                            "excluded_text": excluded_text,
                            "exclusion_reason": exclusion_reason,
                        }
                    )

                    normalized_row = {
                        **row,
                        "customer_id": customer_id,
                        "event_time": event_time_raw,
                        "author_role": author_role,
                        "audience": resolve_audience(author_role),
                        "batch_id": batch_id,
                        "source_version": source_version,
                        "record_version": record_version,
                        "extraction_time": extraction_time_str,
                        "import_time": import_time_str,
                        "passage_anchor": f"{filename}:row:{row_idx}",
                        "text": redacted_text,
                        "redaction_version": REDACTION_VERSION,
                        "quote_rule_version": QUOTE_STRIP_RULE_VERSION if excluded_text else "",
                        "priority_flag": priority_flag,
                        "priority_keywords": "|".join(priority_keywords),
                        "priority_rule_version": PRIORITY_RULE_VERSION,
                        "review_flag": review_flag,
                        "is_stale": is_stale,
                    }
                    accepted_rows.append(normalized_row)
                    rec.rows_accepted += 1

            if rec.rows_received != rec.rows_expected:
                rec.status = "ROW_COUNT_MISMATCH"
            reconciliations.append(rec)

            # Write immutable original store
            orig_path = self.original_dir / f"original_{filename.replace('.csv', '.jsonl')}"
            with orig_path.open("w", encoding="utf-8") as f:
                for item in original_rows:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")

            # Write normalized store
            norm_path = self.normalized_dir / f"normalized_{filename}"
            if accepted_rows:
                with norm_path.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=list(accepted_rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(accepted_rows)

            # Write quarantine queue
            quar_path = self.quarantine_dir / f"quarantine_{filename}"
            if quarantined_rows:
                with quar_path.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=list(quarantined_rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(quarantined_rows)

        # Write batch manifest ledger
        ledger_path = self.normalized_dir / "batch_manifest_ledger.csv"
        with ledger_path.open("w", encoding="utf-8", newline="") as f:
            fields = [
                "batch_id",
                "source_file",
                "rows_expected",
                "rows_received",
                "rows_accepted",
                "rows_quarantined",
                "rows_unanalyzed",
                "unknown_event_time_count",
                "unknown_customer_count",
                "priority_flagged_count",
                "stale_count",
                "status",
            ]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for r in reconciliations:
                writer.writerow(
                    {
                        "batch_id": batch_id,
                        "source_file": r.source_file,
                        "rows_expected": r.rows_expected,
                        "rows_received": r.rows_received,
                        "rows_accepted": r.rows_accepted,
                        "rows_quarantined": r.rows_quarantined,
                        "rows_unanalyzed": r.rows_unanalyzed,
                        "unknown_event_time_count": r.unknown_event_time_count,
                        "unknown_customer_count": r.unknown_customer_count,
                        "priority_flagged_count": r.priority_flagged_count,
                        "stale_count": r.stale_count,
                        "status": r.status,
                    }
                )

        # Write invalidation events (DAT 08)
        if invalidation_events:
            with self.invalidation_path.open("a", encoding="utf-8") as f:
                for ev in invalidation_events:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")

        coverage_report = {
            "batch_id": batch_id,
            "source_version": source_version,
            "load_mode": manifest["load_mode"],
            "cutoff_time": manifest["cutoff_time"],
            "extraction_time": extraction_time_str,
            "import_time": import_time_str,
            "is_stale": is_stale,
            "missing_feeds": missing_files,
            "survey_coverage_available": "survey_responses.csv" not in missing_files,
            "deletion_tombstones_processed": len(manifest.get("deletion_tombstones", [])),
            "invalidation_events_emitted": len(invalidation_events),
            "reconciliation": [r.__dict__ for r in reconciliations],
        }
        coverage_path = self.normalized_dir / "coverage_report.json"
        with coverage_path.open("w", encoding="utf-8") as f:
            json.dump(coverage_report, f, ensure_ascii=False, indent=2)

        self.state["batches"].append(
            {"batch_id": batch_id, "import_time": import_time_str, "source_version": source_version}
        )
        self._save_state()
        return coverage_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Layer 1 Controlled Intake Engine")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    engine = ControlledIntakeEngine(output_dir=args.output_dir)
    report = engine.process_batch(args.input_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
