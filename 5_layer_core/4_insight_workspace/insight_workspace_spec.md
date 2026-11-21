# Tầng 4: Không gian Làm việc & Soạn thảo Báo cáo Trích dẫn Nguồn (Insight Workspace)

Tài liệu đặc tả kỹ thuật cho Tầng 4 căn cứ theo Điều khoản `INS 01`–`INS 04`, `B 04`, `AT 05` của [SongNhat_Vietnam_Voice_of_Customer_Insight_Engine_RFP.md](file:///c:/Users/ACER/__SongNhat/Voice%20of%20Customer%20Insight%20Engine/SongNhat_Vietnam_Voice_of_Customer_Insight_Engine_RFP.md) và sơ đồ [insight_workspace.mmd](file:///c:/Users/ACER/__SongNhat/5%20layers%20core/4_insight_workspace/insight_workspace.mmd).

---

## 1. Chức năng Cốt lõi
- **Tìm kiếm & lọc theo quyền (`Permission-Filtered Search`):** Mọi truy vấn dữ liệu và ví dụ trích dẫn đều lọc theo `allowed_channels` / `allowed_products` của người dùng; người dùng không thể biết sự tồn tại của phản hồi bị giới hạn quyền thông qua số đếm hoặc tóm tắt.
- **Lấy mẫu bằng chứng cân bằng (`INS 03`):** Chọn ví dụ minh họa bao gồm cả phản hồi tích cực, tiêu cực, trái chiều/thiểu số (`minority_contradictory_evidence`) và không làm rơi các ca `priority_flag`.
- **Liên kết bằng chứng (`INS 02`, `AT 05`):** Mọi nhận định (`claim`) trong báo cáo đều gắn `claim_id` liên kết trực tiếp tới `record_id` và `evidence_span` cụ thể.
- **Tách bạch 3 loại nhận định (`INS 01`):**
  1. **Sự thật quan sát được (`Observed Facts`):** Các con số xác định từ Tầng 3 (`item_count`, `case_count`, `nps_score`, `unknown_event_time_items`).
  2. **Phản ánh từ khách hàng (`Customer Allegations`):** Ghi rõ "Khách hàng phản ánh...", không suy diễn thành lỗi kỹ thuật hay trách nhiệm pháp lý (`ANL 04`).
  3. **Giả thuyết phân tích (`Analyst Hypotheses`):** Gắn nhãn tường minh là giả thuyết cần kiểm chứng.
- **Tùy chọn Local LLM (`--use-ollama`):** Cho phép gọi Ollama cục bộ (ví dụ `qwen2.5:3b` / `qwen2.5:7b-instruct-q4_K_M` trên RTX 4050 6 GB) để viết phần diễn giải tóm tắt từ JSON số liệu đã chốt (`INS 04`). Nếu không bật hoặc Ollama chưa chạy, hệ thống dùng bộ sinh diễn giải xác định.

---

## 2. Đầu ra
- `draft_report.md`: Báo cáo nháp trình bày rõ kỳ dữ liệu, độ phủ nguồn, số liệu theo từng đơn vị, chủ đề nổi bật, NPS, bằng chứng trích dẫn và giả thuyết.
- `report_bundle.json`: Gói dữ liệu báo cáo có `report_id`, `status = "draft"`, `snapshot_id`, `claims` và `evidence_links` để chuyển sang Tầng 5 phê duyệt.
