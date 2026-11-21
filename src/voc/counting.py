"""Đếm xác định (DAT 05-07, ANL 07). Không dùng LLM cho bất kỳ con số nào."""


def count_units(rows):
    """Tách riêng item, case, customer; khóa trống = unknown, không gộp."""
    items = len(rows)
    cases = {r["case_key"].strip() for r in rows if (r.get("case_key") or "").strip()}
    customers = {r["customer_key"].strip() for r in rows if (r.get("customer_key") or "").strip()}
    return {
        "items": items,
        "cases": len(cases),
        "known_customers": len(customers),
        "unknown_case_items": sum(1 for r in rows if not (r.get("case_key") or "").strip()),
        "unknown_customer_items": sum(1 for r in rows if not (r.get("customer_key") or "").strip()),
    }


def theme_share(labels_per_item, theme, denominator):
    """Phần trăm theme trên mẫu số đã nêu rõ; đa nhãn nên tổng có thể > 100%."""
    if denominator <= 0:
        return None
    hits = sum(1 for labels in labels_per_item if theme in labels)
    return round(100 * hits / denominator, 1)


def nps(ratings):
    """NPS chuẩn 0-10: %9-10 trừ %0-6, mẫu số gồm cả 7-8.
    Chỉ nhận rating thật; trả None nếu không có rating hợp lệ."""
    valid = []
    for r in ratings:
        s = str(r).strip() if r is not None else ""
        if s.isdigit() and 0 <= int(s) <= 10:
            valid.append(int(s))
    if not valid:
        return None
    n = len(valid)
    promoters = sum(1 for v in valid if v >= 9)
    detractors = sum(1 for v in valid if v <= 6)
    return round(100 * promoters / n - 100 * detractors / n, 1)
