# [Jira Epic Description] Layer 2: NLP & Classification (EN / VI)

---

## PART 1 — ENGLISH

* **Work Type:** Epic
* **Status:** Done

### Objective
Classify all redacted records (`1_controlled_intake/intake_output/normalized_store/normalized_*.csv`) from Layer 1 against a versioned 6-theme taxonomy (`tax-v1.0.0`), extract aspect-based sentiment (`positive`, `negative`, `mixed`, `neutral`) with exact `evidence_span`, and enforce abstention, attribution, and priority escalation rules (`ANL 01`–`ANL 05`, `B 02`, `AT 01`–`AT 03`).

### Scope & Implementation
* **Engine:** `nlp_classification_engine.py`
* **Taxonomy:** `taxonomy_v1.json` (`tax-v1.0.0`)
* **Tests:** `test_nlp_classification.py`
* **Spec & Diagram:** `nlp_classification_spec.md`, `nlp_classification.mmd`
* **Output Directory:** `nlp_output/`

### Versioned Taxonomy (`tax-v1.0.0`)
| Theme ID (`theme_id`) | Display Name | Scope |
| :--- | :--- | :--- |
| `product_quality` | Product Quality & Operation | Hardware defects, battery, screen, noise, vibration, freezing, durability. |
| `delivery_leadtime` | Delivery & Supply Leadtime | Late delivery, stockouts, component delivery schedule, packaging, shipping. |
| `pricing_quotation` | Pricing & Payment | Pricing, quotations, discounts, invoices, promotions, payment discrepancies. |
| `customer_service` | Customer Service & Process | Sales consultation, staff attitude, slow response, return/exchange process. |
| `technical_support` | Technical Support & Warranty | Warranty, repair, software installation, account recovery, bug updates. |
| `safety_incident` | Safety & Critical Incidents | Overheating, fire/explosion, burning odor, leakage, electrical short, operational safety hazard. |

### Core Rules (`ANL 01` - `ANL 05`, `B 02`, `AT 01` - `AT 03`)
1. **Pluggable Classifier (`ANL 01`):** `BaseClassifier` with CPU baseline `DeterministicLexiconClassifier` (`lexicon-baseline-tax-v1.0.0`, runs in seconds on CPU) and `PhoBERTClassifier` adapter (RTX 4050 6 GB VRAM, FP16).
2. **Multi-label Themes & Abstention (`ANL 02`):** Support multi-label classification per record. Flag `needs_review = True` if no theme is supported (`uncertainty_reason = "no_supported_theme"`) or > 5 themes match (`uncertainty_reason = "exceeds_five_themes"`); never silently drop labels.
3. **Aspect Sentiment & Negation (`ANL 03`):** Handle Vietnamese negation (`không`, `chưa`, `chẳng`, `đâu có`) within context windows across `positive`, `negative`, `mixed`, and `neutral` with exact `evidence_span`.
4. **Allegation Attribution (`ANL 04`):** Do not auto-conclude manufacturing defects, legal liability, or root causes. Keep all classifications at `label_stage = "draft"` with `attribution_type` (`"customer_report"` or `"staff_observation"`, per `DAT 01`).
5. **Priority Escalation (`ANL 05`):** Preserve Layer 1 `priority_flag` and escalate `safety_incident` detections; low model confidence cannot clear priority flags.

### Outputs (`nlp_output/`)
* `classifications.jsonl`: Full classification records (`record_id`, `case_id`, `customer_id`, `channel`, `event_time`, `author_role`, `taxonomy_version`, `model_version`, `label_stage="draft"`, `aspects`, `needs_review`, `uncertainty_reason`, `priority_flag`, `priority_keywords`).
* `review_candidates.csv`: Filtered queue of records requiring human review (`needs_review == True` or `priority_flag == True`).
* `classification_summary.json`: Summary statistics of theme distribution, sentiment distribution, `needs_review`, and `priority_flag` counts.

### Acceptance Criteria (Verified)
* `nlp_output/classifications.jsonl`: **36,108** records classified.
* `nlp_output/classification_summary.json` theme distribution:
  * `product_quality`: 17,281
  * `pricing_quotation`: 8,579
  * `customer_service`: 5,843
  * `technical_support`: 3,383
  * `delivery_leadtime`: 1,189
  * `safety_incident`: 298
* Sentiment distribution: `positive` (14,122), `neutral` (13,716), `negative` (6,047), `mixed` (2,688).
* `nlp_output/review_candidates.csv`: **21,980** `needs_review` items and **305** `priority_flag` items exported for human review.

---

## PART 2 — TIẾNG VIỆT

* **Work Type:** Epic
* **Status:** Done

### Objective (Mục tiêu)
Tiếp nhận toàn bộ các bản ghi đã khử định danh (`redacted_text`) từ Layer 1 (`1_controlled_intake/intake_output/normalized_store/normalized_*.csv`), phân loại đa nhãn theo bộ taxonomy có phiên bản gồm 6 chủ đề (`tax-v1.0.0`), gán aspect sentiment (`positive`, `negative`, `mixed`, `neutral`) kèm `evidence_span` chính xác, đồng thời thực thi các quy tắc abstention, attribution và priority escalation (`ANL 01`–`ANL 05`, `B 02`, `AT 01`–`AT 03`).

### Scope & Implementation (Phạm vi & Triển khai)
* **Engine:** `nlp_classification_engine.py`
* **Taxonomy:** `taxonomy_v1.json` (`tax-v1.0.0`)
* **Tests:** `test_nlp_classification.py`
* **Spec & Diagram:** `nlp_classification_spec.md`, `nlp_classification.mmd`
* **Output Directory:** `nlp_output/`

### Bộ Taxonomy có Phiên bản (`tax-v1.0.0`)
| Mã chủ đề (`theme_id`) | Tên hiển thị | Phạm vi bao gồm |
| :--- | :--- | :--- |
| `product_quality` | Chất lượng & Vận hành thiết bị | Lỗi phần cứng, pin, màn hình, tiếng ồn, rung lắc, treo đơ, độ bền. |
| `delivery_leadtime` | Tiến độ giao hàng & Cung ứng | Giao chậm, thiếu hàng, lịch giao linh kiện, đóng gói, vận chuyển. |
| `pricing_quotation` | Báo giá & Thanh toán | Giá bán, báo giá, chiết khấu, hóa đơn, khuyến mãi, sai lệch thanh toán. |
| `customer_service` | Thái độ & Quy trình CSKH | Tư vấn bán hàng, thái độ nhân viên, phản hồi chậm, quy trình đổi trả. |
| `technical_support` | Hỗ trợ kỹ thuật & Bảo hành | Bảo hành, sửa chữa, cài đặt phần mềm, lấy lại tài khoản, cập nhật lỗi. |
| `safety_incident` | An toàn & Sự cố nghiêm trọng | Quá nhiệt, cháy nổ, mùi khét, rò rỉ, chập điện, mất an toàn vận hành. |

### Core Rules (`ANL 01` - `ANL 05`, `B 02`, `AT 01` - `AT 03`)
1. **Pluggable Classifier (`ANL 01`):** Cung cấp `BaseClassifier` với baseline chạy CPU `DeterministicLexiconClassifier` (`lexicon-baseline-tax-v1.0.0`, chạy trong vài giây) và adapter `PhoBERTClassifier` (cho GPU 6 GB VRAM, FP16).
2. **Multi-label Themes & Abstention (`ANL 02`):** Mỗi bản ghi có thể mang nhiều chủ đề. Gắn `needs_review = True` nếu không đủ căn cứ (`uncertainty_reason = "no_supported_theme"`) hoặc khớp > 5 chủ đề (`uncertainty_reason = "exceeds_five_themes"`); tuyệt đối không âm thầm cắt bỏ nhãn.
3. **Aspect Sentiment & Negation (`ANL 03`):** Xử lý từ phủ định tiếng Việt (`không`, `chưa`, `chẳng`, `đâu có`) đảo cực tính cảm xúc trong cửa sổ ngữ cảnh qua 4 mức `{positive, negative, mixed, neutral}` kèm `evidence_span` chính xác.
4. **Allegation Attribution (`ANL 04`):** Không tự động kết luận lỗi sản xuất, trách nhiệm pháp lý hay nguyên nhân kỹ thuật; giữ mọi kết quả ở `label_stage = "draft"` với `attribution_type` (`"customer_report"` hoặc `"staff_observation"`, theo `DAT 01`).
5. **Priority Escalation (`ANL 05`):** Bảo toàn `priority_flag` từ Layer 1 và kết hợp leo thang khi phát hiện `safety_incident`; độ tin cậy mô hình thấp cũng không được phép tắt cờ ưu tiên.

### Outputs (`nlp_output/`)
* `classifications.jsonl`: Toàn bộ kết quả phân loại (`record_id`, `case_id`, `customer_id`, `channel`, `event_time`, `author_role`, `taxonomy_version`, `model_version`, `label_stage="draft"`, `aspects`, `needs_review`, `uncertainty_reason`, `priority_flag`, `priority_keywords`).
* `review_candidates.csv`: Danh sách rút gọn các bản ghi cần nhân viên kiểm duyệt (`needs_review == True` hoặc `priority_flag == True`).
* `classification_summary.json`: Thống kê tổng quan phân bố 6 chủ đề, cảm xúc, số lượng `needs_review` và `priority_flag`.

### Acceptance Criteria (Verified)
* `nlp_output/classifications.jsonl`: Đã phân loại **36,108** bản ghi.
* `nlp_output/classification_summary.json` (phân bố chủ đề):
  * `product_quality`: 17,281
  * `pricing_quotation`: 8,579
  * `customer_service`: 5,843
  * `technical_support`: 3,383
  * `delivery_leadtime`: 1,189
  * `safety_incident`: 298
* Phân bố sentiment: `positive` (14,122), `neutral` (13,716), `negative` (6,047), `mixed` (2,688).
* `nlp_output/review_candidates.csv`: Xuất **21,980** mục `needs_review` và **305** mục `priority_flag` chờ kiểm duyệt.
