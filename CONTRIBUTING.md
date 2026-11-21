# Quy ước làm việc

- Nhánh: `main` (ổn định), `dev` (tích hợp), `feature/SCRUM-xx-mo-ta-ngan`.
- Commit: bắt đầu bằng mã Jira, ví dụ `SCRUM-12: thêm validator survey`. Jira sẽ tự liên kết.
- Mọi thay đổi vào `dev`/`main` qua Pull Request, **bắt buộc có 1 người review** (khác người viết).
- Một việc chỉ sang Done trên Jira khi PR đã merge và CI xanh.
- Tuyệt đối không commit dữ liệu thật, holdout, khóa API, file `.env`.
