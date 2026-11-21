"""Layer 3: Deterministic Measurement Service (DAT 06 - DAT 08, ANL 06 - ANL 07, B 03, B 06)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS items (
            record_id TEXT PRIMARY KEY,
            case_id TEXT,
            customer_id TEXT,
            channel TEXT,
            product_id TEXT,
            event_time TEXT,
            author_role TEXT,
            attribution_type TEXT,
            rating REAL,
            batch_id TEXT,
            source_version TEXT,
            needs_review INTEGER,
            priority_flag INTEGER,
            status TEXT DEFAULT 'ACTIVE'
        );
        CREATE TABLE IF NOT EXISTS labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT,
            theme_id TEXT,
            theme_label TEXT,
            sentiment TEXT,
            evidence_span TEXT,
            label_stage TEXT,
            taxonomy_version TEXT,
            model_version TEXT,
            FOREIGN KEY(record_id) REFERENCES items(record_id)
        );
        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id TEXT PRIMARY KEY,
            created_at TEXT,
            status TEXT,
            payload_json TEXT
        );
        CREATE TABLE IF NOT EXISTS invalidation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            record_id TEXT,
            batch_id TEXT,
            processed_at TEXT
        );
        """
    )
    conn.commit()


def calculate_nps(ratings: List[float]) -> Dict[str, Any]:
    """Compute exact NPS: 100*P(9..10) - 100*P(0..6), keeping 7-8 in denominator (Annex C)."""
    valid = [r for r in ratings if 0.0 <= r <= 10.0]
    n = len(valid)
    if n == 0:
        return {
            "available": False,
            "valid_responses": 0,
            "promoters": 0,
            "passives": 0,
            "detractors": 0,
            "nps_score": None,
        }
    promoters = sum(1 for r in valid if r >= 9.0)
    detractors = sum(1 for r in valid if r <= 6.0)
    passives = n - promoters - detractors
    nps = round(100.0 * (promoters / n) - 100.0 * (detractors / n), 2)
    return {
        "available": True,
        "valid_responses": n,
        "promoters": promoters,
        "passives": passives,
        "detractors": detractors,
        "nps_score": nps,
    }


def load_classifications_to_db(
    conn: sqlite3.Connection, classifications_path: Path
) -> int:
    count = 0
    conn.execute("DELETE FROM labels")
    conn.execute("DELETE FROM items")
    with classifications_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            rating_val: Optional[float] = None
            raw_r = str(rec.get("rating", "")).strip()
            if raw_r:
                try:
                    rating_val = float(raw_r)
                except ValueError:
                    rating_val = None
            conn.execute(
                """
                INSERT INTO items (
                    record_id, case_id, customer_id, channel, product_id,
                    event_time, author_role, attribution_type, rating,
                    batch_id, source_version, needs_review, priority_flag, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                """,
                (
                    rec["record_id"],
                    rec.get("case_id", "unknown"),
                    rec.get("customer_id", "unknown"),
                    rec.get("channel", "unknown"),
                    rec.get("product_id", ""),
                    rec.get("event_time", "unknown"),
                    rec.get("author_role", "unknown"),
                    rec.get("attribution_type", "customer_report"),
                    rating_val,
                    rec.get("batch_id", ""),
                    rec.get("source_version", ""),
                    1 if rec.get("needs_review") else 0,
                    1 if rec.get("priority_flag") else 0,
                ),
            )
            for asp in rec.get("aspects", []):
                conn.execute(
                    """
                    INSERT INTO labels (
                        record_id, theme_id, theme_label, sentiment,
                        evidence_span, label_stage, taxonomy_version, model_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rec["record_id"],
                        asp["theme_id"],
                        asp.get("theme_label", asp["theme_id"]),
                        asp["sentiment"],
                        asp.get("evidence_span", ""),
                        rec.get("label_stage", "draft"),
                        rec.get("taxonomy_version", ""),
                        rec.get("model_version", ""),
                    ),
                )
            count += 1
    conn.commit()
    return count


def apply_invalidations(
    conn: sqlite3.Connection, invalidation_path: Optional[Path]
) -> int:
    if not invalidation_path or not invalidation_path.exists():
        return 0
    processed = 0
    now_iso = datetime.now().isoformat(timespec="seconds")
    with invalidation_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            ev = json.loads(line)
            rec_id = ev.get("record_id", "")
            if ev.get("event_type") == "DELETION_TOMBSTONE" and rec_id:
                conn.execute(
                    "UPDATE items SET status = 'DELETED' WHERE record_id = ?",
                    (rec_id,),
                )
            conn.execute(
                "INSERT INTO invalidation_log (event_type, record_id, batch_id, processed_at) VALUES (?, ?, ?, ?)",
                (ev.get("event_type", ""), rec_id, ev.get("batch_id", ""), now_iso),
            )
            processed += 1
    if processed > 0:
        conn.execute("UPDATE snapshots SET status = 'SUPERSEDED' WHERE status = 'ACTIVE'")
    conn.commit()
    return processed


def compute_measurement_snapshot(
    conn: sqlite3.Connection,
    coverage_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cur = conn.cursor()
    active_items = cur.execute(
        "SELECT record_id, case_id, customer_id, channel, event_time, author_role, rating, needs_review, priority_flag FROM items WHERE status = 'ACTIVE'"
    ).fetchall()

    item_count = len(active_items)
    known_cases = {r[1] for r in active_items if r[1] and r[1].lower() != "unknown"}
    known_customers = {r[2] for r in active_items if r[2] and r[2].lower() != "unknown"}
    unknown_date_items = sum(1 for r in active_items if not r[4] or r[4].lower() == "unknown")
    needs_review_items = sum(1 for r in active_items if r[7] == 1)
    priority_items = sum(1 for r in active_items if r[8] == 1)

    channel_counts: Counter[str] = Counter(r[3] for r in active_items)
    period_counts: Counter[str] = Counter()
    for r in active_items:
        et = r[4] or ""
        if et and et.lower() != "unknown" and len(et) >= 7:
            period_counts[et[:7]] += 1  # YYYY-MM

    survey_ratings = [
        float(r[6]) for r in active_items if r[3] == "survey" and r[6] is not None
    ]
    nps_result = calculate_nps(survey_ratings)

    # Multi-label theme counts (items and cases)
    label_rows = cur.execute(
        """
        SELECT l.record_id, i.case_id, l.theme_id, l.theme_label, l.sentiment, l.label_stage
        FROM labels l
        JOIN items i ON l.record_id = i.record_id
        WHERE i.status = 'ACTIVE'
        """
    ).fetchall()

    theme_item_sets: Dict[str, set] = defaultdict(set)
    theme_case_sets: Dict[str, set] = defaultdict(set)
    theme_labels_map: Dict[str, str] = {}
    theme_sentiment: Dict[str, Counter[str]] = defaultdict(Counter)
    reviewed_records: set = set()

    for rec_id, case_id, t_id, t_lbl, sent, stage in label_rows:
        theme_item_sets[t_id].add(rec_id)
        if case_id and case_id.lower() != "unknown":
            theme_case_sets[t_id].add(case_id)
        theme_labels_map[t_id] = t_lbl
        theme_sentiment[t_id][sent] += 1
        if stage == "reviewed":
            reviewed_records.add(rec_id)

    theme_metrics = []
    for t_id, rec_set in sorted(theme_item_sets.items(), key=lambda x: len(x[1]), reverse=True):
        cnt = len(rec_set)
        pct = round(100.0 * cnt / item_count, 2) if item_count else 0.0
        theme_metrics.append(
            {
                "theme_id": t_id,
                "theme_label": theme_labels_map[t_id],
                "item_count": cnt,
                "case_count": len(theme_case_sets[t_id]),
                "item_share_pct": pct,
                "sentiment_breakdown": dict(theme_sentiment[t_id]),
            }
        )

    snapshot_id = f"SNAP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    snapshot = {
        "snapshot_id": snapshot_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "ACTIVE",
        "units": {
            "item_count": item_count,
            "known_case_count": len(known_cases),
            "known_customer_count": len(known_customers),
            "unknown_event_time_items": unknown_date_items,
            "needs_review_items": needs_review_items,
            "priority_flagged_items": priority_items,
            "reviewed_items": len(reviewed_records),
            "reviewed_coverage_pct": round(100.0 * len(reviewed_records) / item_count, 2)
            if item_count
            else 0.0,
        },
        "channel_counts": dict(channel_counts),
        "monthly_item_trend_excluding_unknown": dict(sorted(period_counts.items())),
        "survey_nps": nps_result,
        "theme_metrics": theme_metrics,
        "intake_coverage_ref": coverage_report or {},
    }

    conn.execute(
        "INSERT INTO snapshots (snapshot_id, created_at, status, payload_json) VALUES (?, ?, 'ACTIVE', ?)",
        (snapshot_id, snapshot["created_at"], json.dumps(snapshot, ensure_ascii=False)),
    )
    conn.commit()
    return snapshot


def run_measurement(
    classifications_path: Path,
    output_dir: Path,
    coverage_path: Optional[Path] = None,
    invalidation_path: Optional[Path] = None,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "measurement_store.db"
    conn = sqlite3.connect(str(db_path))
    try:
        init_db(conn)
        load_classifications_to_db(conn, classifications_path)
        apply_invalidations(conn, invalidation_path)
        cov = (
            json.loads(coverage_path.read_text(encoding="utf-8"))
            if coverage_path and coverage_path.exists()
            else None
        )
        snapshot = compute_measurement_snapshot(conn, cov)
    finally:
        conn.close()

    snap_path = output_dir / "measurement_snapshot.json"
    snap_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Layer 3 Measurement Service")
    parser.add_argument("--classifications", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--coverage", default=None, type=Path)
    parser.add_argument("--invalidations", default=None, type=Path)
    args = parser.parse_args()

    snap = run_measurement(
        args.classifications, args.output_dir, args.coverage, args.invalidations
    )
    print(json.dumps(snap, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
