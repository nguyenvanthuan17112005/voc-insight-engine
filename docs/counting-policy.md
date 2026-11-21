# Chính sách đếm (bản nháp v0.1)

- **Item** = một bản ghi nguồn. **Case** = nhóm đã duyệt của cùng một vấn đề. **Customer** = khóa khách hàng được cung cấp.
- Luôn hiển thị item, case, customer **riêng**. Không có khóa nhóm tin cậy thì chỉ báo item.
- Nhập lặp giống hệt: tự loại. Tin chuyển tiếp: chỉ gợi ý nhóm, cần quy tắc hoặc người duyệt. Sự cố mới: case riêng.
- Mẫu số: toàn bộ bản ghi đủ điều kiện, gồm cách ly, chưa phân tích, ngày không rõ.
- Phần trăm theme đa nhãn có thể vượt 100%; luôn ghi mẫu số.
- Ngày không rõ: loại khỏi xu hướng, vẫn đếm riêng; không gán bằng ngày nhập.
- NPS = %điểm 9-10 trừ %điểm 0-6, mẫu số gồm cả 7-8, chỉ từ cột `rating`. Sentiment không bao giờ quy ra NPS/CSAT.
- Làm tròn: 1 chữ số thập phân (nửa lên). Mọi con số do code tính, LLM không được tự đưa số.
