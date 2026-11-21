"""Layer 4: Insight Workspace & Grounded Report Drafting (INS 01 - INS 04, B 04)."""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def search_evidence(
    classifications_path: Path,
    allowed_channels: Optional[List[str]] = None,
    theme_id: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Permission-filtered search over classified records (INS 02, Sec 5)."""
    results: List[Dict[str, Any]] = []
    allowed_set = set(allowed_channels) if allowed_channels else None

    with classifications_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if allowed_set is not None and rec.get("channel") not in allowed_set:
                continue
            aspects = rec.get("aspects", [])
            for asp in aspects:
                if theme_id and asp.get("theme_id") != theme_id:
                    continue
                if sentiment and asp.get("sentiment") != sentiment:
                    continue
                results.append(
                    {
                        "record_id": rec["record_id"],
                        "case_id": rec.get("case_id", "unknown"),
                        "channel": rec.get("channel", "unknown"),
                        "author_role": rec.get("author_role", "unknown"),
                        "attribution_type": rec.get("attribution_type", "customer_report"),
                        "theme_id": asp["theme_id"],
                        "sentiment": asp["sentiment"],
                        "evidence_span": asp["evidence_span"],
                        "priority_flag": rec.get("priority_flag", False),
                    }
                )
                break
            if len(results) >= limit:
                break
    return results


def call_ollama_summary(
    prompt: str, model: str = "qwen2.5:3b", endpoint: str = "http://localhost:11434/api/generate"
) -> Optional[str]:
    """Optional local LLM narrative helper (Ollama on RTX 4050 6GB VRAM)."""
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return str(data.get("response", "")).strip() or None
    except Exception:
        return None


def build_report_bundle(
    snapshot_path: Path,
    classifications_path: Path,
    output_dir: Path,
    allowed_channels: Optional[List[str]] = None,
    use_ollama: bool = False,
    ollama_model: str = "qwen2.5:3b",
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    units = snapshot["units"]
    top_themes = snapshot.get("theme_metrics", [])[:5]
    nps = snapshot.get("survey_nps", {})

    claims: List[Dict[str, Any]] = []
    # Grounded examples per top theme (including contradictory/minority sentiment per INS 03)
    for idx, t in enumerate(top_themes, start=1):
        t_id = t["theme_id"]
        neg_examples = search_evidence(
            classifications_path, allowed_channels, theme_id=t_id, sentiment="negative", limit=2
        )
        pos_examples = search_evidence(
            classifications_path, allowed_channels, theme_id=t_id, sentiment="positive", limit=1
        )
        evidence_refs = neg_examples + pos_examples
        claims.append(
            {
                "claim_id": f"CLAIM_{idx:03d}",
                "claim_type": "observed_fact_and_customer_allegation",
                "statement": (
                    f"Chủ đề '{t['theme_label']}' ghi nhận {t['item_count']} mục "
                    f"({t['item_share_pct']}% tổng mục hợp lệ, {t['case_count']} vụ việc). "
                    f"Phân bố cảm xúc: {t['sentiment_breakdown']}."
                ),
                "evidence_links": evidence_refs,
            }
        )

    priority_examples = []
    with classifications_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if allowed_channels and rec.get("channel") not in set(allowed_channels):
                continue
            if rec.get("priority_flag"):
                asps = rec.get("aspects", [])
                span = asps[0]["evidence_span"] if asps else ""
                priority_examples.append(
                    {
                        "record_id": rec["record_id"],
                        "case_id": rec.get("case_id", "unknown"),
                        "channel": rec.get("channel", "unknown"),
                        "attribution_type": rec.get("attribution_type", "customer_report"),
                        "evidence_span": span,
                    }
                )
            if len(priority_examples) >= 5:
                break

    hypotheses = [
        {
            "hypothesis_id": "HYP_001",
            "label": "HYPOTHESIS (Cần kiểm chứng vận hành)",
            "statement": (
                "Tỷ lệ phản ánh tiêu cực ở nhóm chất lượng thiết bị và hỗ trợ kỹ thuật "
                "có thể liên quan đến quy trình kiểm tra sau bảo trì; cần đối soát hồ sơ kỹ thuật nội bộ."
            ),
        }
    ]

    llm_note = None
    if use_ollama:
        prompt = (
            "Tóm tắt ngắn gọn bằng tiếng Việt (tối đa 4 câu, không tự bịa thêm số liệu) "
            f"dựa trên kết quả sau: item_count={units['item_count']}, "
            f"top_themes={[(t['theme_label'], t['item_count']) for t in top_themes[:3]]}, "
            f"nps={nps.get('nps_score')}."
        )
        llm_note = call_ollama_summary(prompt, model=ollama_model)

    report_id = f"RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    bundle = {
        "report_id": report_id,
        "status": "draft",
        "snapshot_id": snapshot["snapshot_id"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "policy_version": "policy-v1.0.0",
        "allowed_channels_scope": allowed_channels or ["ALL"],
        "units": units,
        "survey_nps": nps,
        "claims": claims,
        "priority_watchlist_samples": priority_examples,
        "hypotheses": hypotheses,
        "llm_narrative_summary": llm_note,
    }

    bundle_path = output_dir / "report_bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    # Render draft_report.md (INS 01)
    md_lines = [
        f"# Báo cáo Nháp Voice of Customer ({report_id})",
        "",
        f"- **Trạng thái:** `{bundle['status']}`",
        f"- **Snapshot ID:** `{snapshot['snapshot_id']}`",
        f"- **Phạm vi kênh:** `{', '.join(bundle['allowed_channels_scope'])}`",
        "",
        "## 1. Sự thật Quan sát được (Observed Facts)",
        f"- Tổng số mục hợp lệ (`item_count`): **{units['item_count']}**",
        f"- Số vụ việc định danh (`known_case_count`): **{units['known_case_count']}**",
        f"- Số khách hàng định danh (`known_customer_count`): **{units['known_customer_count']}**",
        f"- Mục không rõ ngày (`unknown_event_time_items`, loại khỏi xu hướng kỳ): **{units['unknown_event_time_items']}**",
        f"- Mục cần kiểm duyệt (`needs_review_items`): **{units['needs_review_items']}**",
        f"- Mục gắn cờ ưu tiên (`priority_flagged_items`): **{units['priority_flagged_items']}**",
        f"- Tỷ lệ đã được con người duyệt (`reviewed_coverage_pct`): **{units['reviewed_coverage_pct']}%**",
        "",
    ]
    if nps.get("available"):
        md_lines.extend(
            [
                "### Chỉ số Khảo sát NPS (Tính trên `survey` hợp lệ)",
                f"- Số phản hồi hợp lệ: **{nps['valid_responses']}** (Promoters: {nps['promoters']}, Passives: {nps['passives']}, Detractors: {nps['detractors']})",
                f"- **NPS:** **{nps['nps_score']}**",
                "",
            ]
        )

    if llm_note:
        md_lines.extend(["### Tóm tắt diễn giải (Local LLM Draft)", llm_note, ""])

    md_lines.append("## 2. Chủ đề Nổi bật & Bằng chứng Trích dẫn (Customer Allegations & Evidence)")
    for c in claims:
        md_lines.append(f"### {c['claim_id']}: {c['statement']}")
        for ev in c["evidence_links"]:
            md_lines.append(
                f"- `[{ev['record_id']} | {ev['channel']} | {ev['attribution_type']} | {ev['sentiment']}]` \"{ev['evidence_span']}\""
            )
        md_lines.append("")

    md_lines.append("## 3. Danh sách Cảnh báo Ưu tiên (Priority Watchlist - Cần Staff Kiểm duyệt)")
    for pe in priority_examples:
        md_lines.append(
            f"- `[{pe['record_id']} | {pe['channel']} | {pe['attribution_type']}]` \"{pe['evidence_span']}\""
        )
    md_lines.append("")

    md_lines.append("## 4. Giả thuyết Phân tích (Labeled Hypotheses)")
    for h in hypotheses:
        md_lines.append(f"- **{h['hypothesis_id']} ({h['label']}):** {h['statement']}")

    report_md_path = output_dir / "draft_report.md"
    report_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Layer 4 Insight Workspace")
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--classifications", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--use-ollama", action="store_true")
    parser.add_argument("--ollama-model", default="qwen2.5:3b")
    args = parser.parse_args()

    bundle = build_report_bundle(
        args.snapshot,
        args.classifications,
        args.output_dir,
        use_ollama=args.use_ollama,
        ollama_model=args.ollama_model,
    )
    print(json.dumps({"report_id": bundle["report_id"], "claims": len(bundle["claims"])}, indent=2))


if __name__ == "__main__":
    main()
