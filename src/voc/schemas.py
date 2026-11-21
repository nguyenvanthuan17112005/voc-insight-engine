"""Định nghĩa 3 schema CSV đầu vào (DAT 01-04, RFP mục 2).

Ghi chú: với survey_response, nội dung bình luận nằm ở cột `text` chung.
"""

COMMON_COLUMNS = [
    "record_id", "record_version", "source_system",
    "event_time", "extraction_time", "import_time",
    "channel", "author_role", "customer_key", "case_key",
    "text", "access_label",
]

SCHEMAS = {
    "service_case_feedback": COMMON_COLUMNS + ["product_id", "site", "case_status"],
    "curated_correspondence": COMMON_COLUMNS + [
        "thread_id", "audience", "is_forwarded", "quoted_history_flag"],
    "survey_response": COMMON_COLUMNS + ["question_id", "rating", "rating_scale"],
}

# Cột bắt buộc phải có giá trị (còn lại có thể trống = unknown)
REQUIRED_VALUES = ["record_id", "record_version"]

AUTHOR_ROLES = {"customer", "staff", "unknown"}
MAX_TEXT_CHARS = 8000  # RFP mục 2
