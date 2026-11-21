# Tầng 2: Phân tích Ngôn ngữ & Phân loại Phản hồi (NLP & Classification)

Tài liệu đặc tả kỹ thuật cho Tầng 2 căn cứ theo Điều khoản `ANL 01`–`ANL 05`, `B 02`, `AT 01`–`AT 03` của [SongNhat_Vietnam_Voice_of_Customer_Insight_Engine_RFP.md](file:///c:/Users/ACER/__SongNhat/Voice%20of%20Customer%20Insight%20Engine/SongNhat_Vietnam_Voice_of_Customer_Insight_Engine_RFP.md) và sơ đồ [nlp_classification.mmd](file:///c:/Users/ACER/__SongNhat/5%20layers%20core/2_nlp_classification/nlp_classification.mmd).

---

## 1. Mục tiêu và Phạm vi
- Nhận toàn bộ các bản ghi đã được khử định danh (`redacted_text`) từ `1_controlled_intake/intake_output/normalized_store/normalized_*.csv`.
- Phân loại đa nhãn theo bộ taxonomy có phiên bản (`taxonomy_v1.json`, phiên bản `tax-v1.0.0`).
- Gán cảm xúc theo từng khía cạnh (`positive`, `negative`, `mixed`, `neutral`) kèm trích xuất **bằng chứng chính xác (`evidence_span`)**.
- Bảo toàn các quy tắc an toàn và không suy diễn vượt bằng chứng (`ANL 04`, `ANL 05`).

---

## 2. Bộ Taxonomy có Phiên bản (`tax-v1.0.0`)

| Mã chủ đề (`theme_id`) | Tên hiển thị | Phạm vi bao gồm |
| :--- | :--- | :--- |
| `product_quality` | Chất lượng & Vận hành thiết bị | Lỗi phần cứng, pin, màn hình, tiếng ồn, rung lắc, treo đơ, độ bền. |
| `delivery_leadtime` | Tiến độ giao hàng & Cung ứng | Giao chậm, thiếu hàng, lịch giao linh kiện, đóng gói, vận chuyển. |
| `pricing_quotation` | Báo giá & Thanh toán | Giá bán, báo giá, chiết khấu, hóa đơn, khuyến mãi, sai lệch thanh toán. |
| `customer_service` | Thái độ & Quy trình CSKH | Tư vấn bán hàng, thái độ nhân viên, phản hồi chậm, quy trình đổi trả. |
| `technical_support` | Hỗ trợ kỹ thuật & Bảo hành | Bảo hành, sửa chữa, cài đặt phần mềm, lấy lại tài khoản, cập nhật lỗi. |
| `safety_incident` | An toàn & Sự cố nghiêm trọng | Quá nhiệt, cháy nổ, mùi khét, rò rỉ, chập điện, mất an toàn vận hành. |

---

## 3. Quy tắc Xử lý Nghiệp vụ (`ANL 01` - `ANL 05`)
- **`ANL 01` (Baseline & Pluggable Classifier):** Cung cấp `BaseClassifier` với triển khai mặc định `DeterministicLexiconClassifier` (chạy trên CPU trong vài giây) và adapter `PhoBERTClassifier` (dành cho RTX 4050 6 GB VRAM ở FP16).
- **`ANL 02` (Themes & Abstention):** Mỗi bản ghi có thể mang nhiều chủ đề. Nếu không đủ căn cứ -> gán `needs_review = True` (`uncertainty_reason = "no_supported_theme"`); nếu khớp > 5 chủ đề -> gắn `needs_review = True` (`uncertainty_reason = "exceeds_five_themes"`), tuyệt đối không âm thầm cắt bỏ nhãn.
- **`ANL 03` (Aspect Sentiment & Negation):** Xử lý từ phủ định tiếng Việt (`không`, `chưa`, `chẳng`, `đâu có`) đảo cực tính cảm xúc trong cửa sổ ngữ cảnh; hỗ trợ 4 mức `{positive, negative, mixed, neutral}`.
- **`ANL 04` (Allegations):** Không tự động kết luận lỗi sản xuất, trách nhiệm pháp lý hay nguyên nhân kỹ thuật; mọi kết quả giữ ở trạng thái `draft` gắn cờ `attribution_type = "customer_report"` hoặc `"staff_observation"` (theo `DAT 01`).
- **`ANL 05` (Priority Review):** Cờ `priority_flag` từ Tầng 1 được giữ nguyên và kết hợp thêm tín hiệu phát hiện `safety_incident` ở Tầng 2; mô hình có độ tin cậy thấp cũng không được phép tắt cờ ưu tiên.

---

## 4. Đầu ra
- `classifications.jsonl`: Toàn bộ kết quả phân loại (`record_id`, `case_id`, `customer_id`, `channel`, `event_time`, `author_role`, `taxonomy_version`, `model_version`, `label_stage="draft"`, `aspects`, `needs_review`, `uncertainty_reason`, `priority_flag`, `priority_keywords`).
- `review_candidates.csv`: Danh sách rút gọn các bản ghi cần nhân viên kiểm duyệt (`needs_review == True` hoặc `priority_flag == True`).
- `classification_summary.json`: Thống kê tổng quan phân bố chủ đề, cảm xúc, số lượng `needs_review` và `priority_flag`.
