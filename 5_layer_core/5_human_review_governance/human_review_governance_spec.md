# Tầng 5: Quản trị Kiểm duyệt Con người & Đề xuất Hành động (Human Review & Action Governance)

Tài liệu đặc tả kỹ thuật cho Tầng 5 căn cứ theo Điều khoản `INS 05`–`INS 08`, `B 05`, `B 06`, `AT 06`, `AT 08` của [SongNhat_Vietnam_Voice_of_Customer_Insight_Engine_RFP.md](file:///c:/Users/ACER/__SongNhat/Voice%20of%20Customer%20Insight%20Engine/SongNhat_Vietnam_Voice_of_Customer_Insight_Engine_RFP.md) và sơ đồ [human_review_governance.mmd](file:///c:/Users/ACER/__SongNhat/5%20layers%20core/5_human_review_governance/human_review_governance.mmd).

---

## 1. Quy trình Kiểm duyệt & Hiệu chỉnh Nhãn (`INS 08`)
- Nhân viên kiểm duyệt các bản ghi trong `review_candidates.csv` (`needs_review` hoặc `priority_flag`).
- Mọi chỉnh sửa nhãn (`old_theme`, `new_theme`, `old_sentiment`, `new_sentiment`, `reviewer`, `reason`, `timestamp`) được ghi vào `reviewer_corrections.jsonl` với `label_stage = "reviewed"`.
- **Nguyên tắc kiểm soát:** Các chỉnh sửa này **không bao giờ** tự động đi vào tập huấn luyện AI hoặc tự động sửa luật sản xuất; mọi thay đổi mô hình/luật đều phải qua quy trình đánh giá và phát hành phiên bản riêng (`INS 08`).

---

## 2. Vòng đời Phê duyệt Báo cáo (`INS 05`, `DAT 08`)
- Báo cáo đi qua các trạng thái tường minh: `draft` -> `under_review` -> `approved` / `rejected` -> `superseded`.
- Trạng thái `approved` bắt buộc gắn với `named_owner`, `snapshot_id`, `policy_version` và `approved_at`.
- Nếu phát sinh thay đổi phụ thuộc (hiệu chỉnh nhãn mới hoặc sự kiện xóa/sửa từ `invalidation_events.jsonl`), báo cáo `approved` bị ảnh hưởng sẽ tự động chuyển sang `superseded` (`DAT 08`, `B 06`), không bao giờ viết đè âm thầm lên bản đã duyệt.

---

## 3. Sổ bộ Đề xuất Hành động Nội bộ (`INS 06`, `INS 07`)
- Ghi nhận đề xuất cải tiến nội bộ gắn với `theme_id`, `evidence_record_ids`, `owner`, `review_date` và trạng thái tách biệt:
  - Quyết định đề xuất: `proposed` -> `accepted` / `deferred` / `rejected`
  - Thực thi & kết quả: `implemented` -> `outcome_reviewed` (cần bằng chứng từ owner và quan sát đối chiếu sau đó, không tự quy kết nguyên nhân).
- **Ràng buộc an toàn:** Hệ thống lõi chỉ ghi nhận quyết định nội bộ, tuyệt đối không tự động gửi tin nhắn cho khách hàng hay tạo ticket trên CRM bên ngoài.
