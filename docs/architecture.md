# Kiến trúc khối v0 (theo RFP Annex A Figure 1)

```
3 file CSV -> Kiểm soát nguồn & riêng tư -> Phân loại có bằng chứng
           -> Đếm xác định -> Báo cáo có trích dẫn -> Duyệt & đề xuất hành động
```

Stack dự kiến: Python 3.11+, PostgreSQL, FastAPI, scikit-learn, PhoBERT, Streamlit (hoặc React).
Hiện repo mới có: schema, validator, đếm xác định, dữ liệu mẫu, test. Phần còn lại làm theo sprint.
