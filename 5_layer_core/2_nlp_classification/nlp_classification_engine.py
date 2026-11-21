"""Layer 2: NLP & Classification Engine (ANL 01 - ANL 05, B 02)."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

NEGATION_WORDS = {"không", "ko", "k", "chưa", "chẳng", "chả", "đâu có", "khỏi"}

POSITIVE_LEXICON = {
    "tốt", "ok", "oke", "okie", "ổn", "mượt", "nhanh", "trâu", "đẹp", "nét",
    "rõ", "nhiệt tình", "chu đáo", "vui vẻ", "tuyệt vời", "hài lòng", "ưng",
    "ngon", "xịn", "đỉnh", "mạnh", "khỏe", "đầy đủ", "hay", "tích cực", "sáng",
}

NEGATIVE_LEXICON = {
    "kém", "tệ", "xấu", "chậm", "trễ", "lag", "giật", "đơ", "treo", "lỗi",
    "hỏng", "hư", "rè", "mờ", "tối", "yếu", "nóng", "quá nhiệt", "khét",
    "cháy", "nổ", "thất vọng", "chán", "bực", "ức chế", "lừa", "tụt", "hao",
    "nhòe", "chập chờn", "khó chịu", "ồn", "rung",
}


def normalize_nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def find_evidence_span(text: str, keyword: str) -> Tuple[int, int, str]:
    """Return (start, end, exact_substring) around the matched keyword."""
    lower_text = text.lower()
    idx = lower_text.find(keyword.lower())
    if idx == -1:
        return 0, min(len(text), 80), text[:80]
    start = max(0, idx - 25)
    end = min(len(text), idx + len(keyword) + 35)
    return start, end, text[start:end]


def score_local_sentiment(snippet: str) -> str:
    """Determine positive/negative/mixed/neutral with Vietnamese negation & multi-word phrases."""
    lower = snippet.lower()
    pos_hits = 0
    neg_hits = 0

    # Match multi-word lexicon phrases first
    for phrase in POSITIVE_LEXICON | NEGATIVE_LEXICON:
        if " " not in phrase:
            continue
        for match in re.finditer(re.escape(phrase), lower):
            prefix_tokens = re.findall(r"[\w]+", lower[max(0, match.start() - 20) : match.start()])[-2:]
            is_negated = any(w in NEGATION_WORDS for w in prefix_tokens)
            if phrase in POSITIVE_LEXICON:
                neg_hits += 1 if is_negated else 0
                pos_hits += 0 if is_negated else 1
            else:
                pos_hits += 1 if is_negated else 0
                neg_hits += 0 if is_negated else 1

    # Match single-word tokens
    tokens = re.findall(r"[\w]+", lower)
    for i, tok in enumerate(tokens):
        window = tokens[max(0, i - 2) : i]
        is_negated = any(w in NEGATION_WORDS for w in window)
        if tok in POSITIVE_LEXICON:
            if is_negated:
                neg_hits += 1
            else:
                pos_hits += 1
        elif tok in NEGATIVE_LEXICON:
            if is_negated:
                pos_hits += 1
            else:
                neg_hits += 1

    if pos_hits > 0 and neg_hits > 0:
        return "mixed"
    if pos_hits > 0:
        return "positive"
    if neg_hits > 0:
        return "negative"
    return "neutral"


@dataclass
class AspectPrediction:
    theme_id: str
    theme_label: str
    sentiment: str
    evidence_span: str
    span_start: int
    span_end: int
    confidence: float


class BaseClassifier(ABC):
    """Pluggable classifier interface (ANL 01)."""

    model_version: str

    @abstractmethod
    def predict(self, text: str) -> List[AspectPrediction]:
        raise NotImplementedError


class DeterministicLexiconClassifier(BaseClassifier):
    """Fast CPU baseline classifier using signed taxonomy keywords + negation rules."""

    def __init__(self, taxonomy_path: Path) -> None:
        with taxonomy_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.taxonomy_version: str = data["taxonomy_version"]
        self.themes: List[Dict[str, Any]] = data["themes"]
        self.model_version = f"lexicon-baseline-{self.taxonomy_version}"

    def predict(self, text: str) -> List[AspectPrediction]:
        lower_text = text.lower()
        predictions: List[AspectPrediction] = []
        for theme in self.themes:
            matched_kw: Optional[str] = None
            hit_count = 0
            for kw in theme["keywords"]:
                if kw in lower_text:
                    hit_count += 1
                    if matched_kw is None:
                        matched_kw = kw
            if matched_kw is not None:
                s_idx, e_idx, span = find_evidence_span(text, matched_kw)
                sentiment = score_local_sentiment(span)
                conf = min(0.95, 0.55 + 0.1 * hit_count)
                predictions.append(
                    AspectPrediction(
                        theme_id=theme["theme_id"],
                        theme_label=theme["label"],
                        sentiment=sentiment,
                        evidence_span=span,
                        span_start=s_idx,
                        span_end=e_idx,
                        confidence=round(conf, 3),
                    )
                )
        return predictions


class PhoBERTClassifier(BaseClassifier):
    """Adapter stub for local fine-tuned PhoBERT (FP16 on RTX 4050 6GB VRAM)."""

    def __init__(self, model_dir: Path, taxonomy_path: Path) -> None:
        self.model_dir = model_dir
        self.taxonomy_path = taxonomy_path
        self.model_version = "phobert-fp16-v1.0.0"

    def predict(self, text: str) -> List[AspectPrediction]:
        raise NotImplementedError(
            "PhoBERTClassifier requires a fine-tuned checkpoint and PyTorch/Transformers."
        )


def classify_records(
    input_dir: Path,
    output_dir: Path,
    classifier: BaseClassifier,
    taxonomy_version: str,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = output_dir / "classifications.jsonl"
    review_csv = output_dir / "review_candidates.csv"
    summary_json = output_dir / "classification_summary.json"

    normalized_files = sorted(input_dir.glob("normalized_*.csv"))
    if not normalized_files:
        raise FileNotFoundError(f"No normalized_*.csv files found in {input_dir}")

    total_records = 0
    needs_review_count = 0
    priority_count = 0
    theme_counts: Counter[str] = Counter()
    sentiment_counts: Counter[str] = Counter()
    review_rows: List[Dict[str, Any]] = []

    with out_jsonl.open("w", encoding="utf-8") as f_out:
        for csv_path in normalized_files:
            with csv_path.open("r", encoding="utf-8", newline="") as f_in:
                reader = csv.DictReader(f_in)
                for row in reader:
                    total_records += 1
                    text = normalize_nfc(row.get("text") or "")
                    author_role = row.get("author_role") or "unknown"
                    attribution_type = (
                        "staff_observation"
                        if author_role == "staff_note"
                        else "customer_report"
                    )
                    priority_flag = str(row.get("priority_flag", "")).lower() == "true"

                    preds = classifier.predict(text)

                    # ANL 05: safety_incident or Layer 1 priority_flag stays active
                    if any(p.theme_id == "safety_incident" for p in preds):
                        priority_flag = True

                    needs_review = False
                    uncertainty_reason = ""
                    if not preds:
                        needs_review = True
                        uncertainty_reason = "no_supported_theme"
                    elif len(preds) > 5:
                        needs_review = True
                        uncertainty_reason = "exceeds_five_themes"
                    elif any(p.sentiment == "neutral" and p.confidence < 0.7 for p in preds):
                        needs_review = True
                        uncertainty_reason = "low_confidence_sentiment"

                    if needs_review:
                        needs_review_count += 1
                    if priority_flag:
                        priority_count += 1

                    for p in preds:
                        theme_counts[p.theme_id] += 1
                        sentiment_counts[p.sentiment] += 1

                    record_obj = {
                        "record_id": row["record_id"],
                        "case_id": row.get("case_id", "unknown"),
                        "customer_id": row.get("customer_id", "unknown"),
                        "channel": row.get("channel", "unknown"),
                        "product_id": row.get("product_id", ""),
                        "event_time": row.get("event_time", "unknown"),
                        "author_role": author_role,
                        "attribution_type": attribution_type,
                        "rating": row.get("rating", ""),
                        "batch_id": row.get("batch_id", ""),
                        "source_version": row.get("source_version", ""),
                        "taxonomy_version": taxonomy_version,
                        "model_version": classifier.model_version,
                        "label_stage": "draft",
                        "aspects": [p.__dict__ for p in preds],
                        "needs_review": needs_review,
                        "uncertainty_reason": uncertainty_reason,
                        "priority_flag": priority_flag,
                        "priority_keywords": row.get("priority_keywords", ""),
                    }
                    f_out.write(json.dumps(record_obj, ensure_ascii=False) + "\n")

                    if needs_review or priority_flag:
                        review_rows.append(
                            {
                                "record_id": row["record_id"],
                                "case_id": row.get("case_id", "unknown"),
                                "channel": row.get("channel", "unknown"),
                                "author_role": author_role,
                                "priority_flag": priority_flag,
                                "needs_review": needs_review,
                                "uncertainty_reason": uncertainty_reason,
                                "themes": "|".join(p.theme_id for p in preds),
                                "text_preview": text[:160],
                            }
                        )

    if review_rows:
        with review_csv.open("w", encoding="utf-8", newline="") as f_rev:
            writer = csv.DictWriter(f_rev, fieldnames=list(review_rows[0].keys()))
            writer.writeheader()
            writer.writerows(review_rows)

    summary = {
        "taxonomy_version": taxonomy_version,
        "model_version": classifier.model_version,
        "total_records_classified": total_records,
        "needs_review_count": needs_review_count,
        "priority_flagged_count": priority_count,
        "theme_counts": dict(theme_counts),
        "sentiment_counts": dict(sentiment_counts),
    }
    with summary_json.open("w", encoding="utf-8") as f_sum:
        json.dump(summary, f_sum, ensure_ascii=False, indent=2)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Layer 2 NLP Classification Engine")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--taxonomy",
        default=Path(__file__).parent / "taxonomy_v1.json",
        type=Path,
    )
    args = parser.parse_args()

    classifier = DeterministicLexiconClassifier(args.taxonomy)
    summary = classify_records(
        args.input_dir, args.output_dir, classifier, classifier.taxonomy_version
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
