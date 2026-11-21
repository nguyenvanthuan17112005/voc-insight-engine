# Dữ liệu

**TOÀN BỘ DỮ LIỆU TRONG REPO NÀY LÀ DỮ LIỆU TỔNG HỢP (GIẢ LẬP).**
Không phải dữ liệu thật của SongNhat hay của bất kỳ khách hàng nào. Tên, mã khách, mã sản phẩm đều là bịa.

`sample/` chứa 3 file mẫu nhỏ, cố ý có các "bẫy" theo RFP mục 13:
trống ngày (S004), nhập lặp giống hệt (S006), phản hồi mỉa mai (S007), nhiều case một khách (C005, C007),
tin chuyển tiếp (M002, M003), cờ ưu tiên (S003, M005), nguồn bị hạn chế (access_label=restricted),
rating trống (V003) và chỉ có rating không có bình luận (V002, V004).

Quy tắc: không commit dữ liệu thật; holdout (tập kiểm thử độc lập) **không** để trong repo công khai,
chỉ PO giữ (xem docs/data-policy.md).
