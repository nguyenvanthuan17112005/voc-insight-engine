# Tầng 3: Dịch vụ Đo lường và Tập hợp Xác định (Measurement Service)

Tài liệu đặc tả kỹ thuật cho Tầng 3 căn cứ theo Điều khoản `DAT 06`–`DAT 08`, `ANL 06`–`ANL 07`, `B 03`, `B 06`, `AT 04` và `Annex C` của [SongNhat_Vietnam_Voice_of_Customer_Insight_Engine_RFP.md](file:///c:/Users/ACER/__SongNhat/Voice%20of%20Customer%20Insight%20Engine/SongNhat_Vietnam_Voice_of_Customer_Insight_Engine_RFP.md) và sơ đồ [measurement_service.mmd](file:///c:/Users/ACER/__SongNhat/5%20layers%20core/3_measurement_service/measurement_service.mmd).

---

## 1. Kiến trúc Lưu trữ Quan hệ (`measurement_store.db`)
- **`items`**: Lưu thông tin gốc bất biến của từng bản ghi (`record_id`, `case_id`, `customer_id`, `channel`, `product_id`, `event_time`, `author_role`, `attribution_type`, `rating`, `priority_flag`, `needs_review`).
- **`labels`**: Lưu nhãn đa khía cạnh (`record_id`, `theme_id`, `theme_label`, `sentiment`, `evidence_span`, `label_stage` là `draft` hoặc `reviewed`, `taxonomy_version`, `model_version`).
- **`snapshots`**: Lưu các lát cắt tổng hợp (`snapshot_id`, `status` là `ACTIVE` hoặc `SUPERSEDED`, `created_at`).
- **`invalidation_log`**: Ghi nhận sự kiện xóa/sửa từ `invalidation_events.jsonl` (`DAT 08`).

---

## 2. Quy tắc Tính toán Xác định (`DAT 06` - `DAT 08`, `ANL 06` - `ANL 07`)
- **Tách biệt 3 đơn vị đếm (`DAT 06`):** Luôn báo cáo riêng `item_count`, `case_count` (nhóm theo `case_id` hợp lệ, loại trừ `"unknown"`), và `known_customer_count` (loại trừ `"unknown"`).
- **Cohort vụ việc (`Annex C`):** Gán ngày cohort của mỗi `case_id` dựa trên `event_time` hợp lệ sớm nhất của khách hàng (`customer`); mỗi vụ việc chỉ tính một lần trên mỗi chủ đề trong snapshot cohort.
- **Độ phủ & Ngày không xác định (`DAT 07`):** Các bản ghi có `event_time = "unknown"` được đếm riêng (`unknown_event_time_count`) và loại khỏi chuỗi xu hướng theo tháng/ngày, tuyệt đối không gán tạm bằng `import_time`.
- **Tỷ lệ đa nhãn (`DAT 06`, `INS 04`):** Chia trên mẫu số `eligible_items` (tổng số mục hợp lệ), cho phép tổng tỷ lệ các chủ đề vượt 100%; tách biệt tỷ lệ `draft` và `reviewed`.
- **Công thức NPS chuẩn (`ANL 07`, `Annex C`, `R06`):**
  - Chỉ tính trên các bản ghi `channel == "survey"` có `rating` hợp lệ từ `0` đến `10`.
  - $\text{NPS} = 100 \times \frac{\text{Promoters (9-10)}}{N_{\text{valid}}} - 100 \times \frac{\text{Detractors (0-6)}}{N_{\text{valid}}}$ (nhóm Passives 7–8 giữ nguyên trong mẫu số $N_{\text{valid}}$).
  - Không bao giờ suy diễn điểm khảo sát từ cảm xúc văn bản.
- **Vô hiệu hóa khi có chỉnh sửa/xóa (`DAT 08`, `B 06`):** Nếu có `invalidation_events.jsonl` mới, các snapshot `ACTIVE` trước đó chuyển sang `SUPERSEDED` và bắt buộc tính lại.
