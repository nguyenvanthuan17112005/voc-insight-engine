# Voice of Customer Insight Engine

Đồ án nhóm (đề tài AI-12) theo RFP của SongNhat: hệ thống đọc phản hồi khách hàng tiếng Việt, phân loại chủ đề và cảm xúc theo khía cạnh, đếm số liệu xác định, và tạo báo cáo có trích dẫn nguồn để nhân viên duyệt.

> **Lưu ý:** dữ liệu trong repo là **tổng hợp (giả lập)**, không phải dữ liệu thật của SongNhat.

## Nguyên tắc cốt lõi
1. Mọi nhận định truy được về văn bản gốc.
2. Số liệu do code tính; LLM không được tự đưa số.
3. Tách riêng item, case, customer.
4. Sentiment không bao giờ thành NPS/CSAT.
5. Khách phản ánh không phải sự thật đã xác nhận; không kết luận nguyên nhân hay lỗi.
6. Cờ ưu tiên bằng luật, không bị tắt vì mô hình kém tự tin.
7. Con người duyệt; hệ thống không tự liên hệ khách hay ghi vào CRM.

## Cấu trúc
```
src/voc/         schemas, validator, counting, cli
tests/           unit test
data/sample/     3 file CSV mẫu tổng hợp (có các ca bẫy)
configs/         taxonomy v0.1, từ khóa ưu tiên
docs/            ma trận tuân thủ, chính sách, kiến trúc
.github/         CI, mẫu PR, mẫu issue
```

## Chạy thử
```bash
make test
make validate-sample
# hoặc
PYTHONPATH=src python -m voc.cli validate data/sample/survey_response.csv survey_response
```

## Lộ trình (16 tuần)
| Tuần | Mục tiêu |
|---|---|
| 1-2 | Discovery, G0 + G1 (schema, taxonomy, chính sách đếm) |
| 3-4 | Intake, baseline, đếm xác định |
| 5-6 | Aspect sentiment, cờ ưu tiên, workspace v1 |
| 7-8 | Báo cáo có trích dẫn, bảo mật, G2 |
| 9-12 | Quan sát 20 ngày làm việc, đánh giá độc lập, load/security/recovery |
| 13-14 | Sửa lỗi, hồ sơ G3 |
| 15-16 | Bàn giao, demo, G4 |

Xem `CONTRIBUTING.md` cho quy ước nhánh, commit và review.
