# Tầng 1: Phân hệ Tiếp nhận Dữ liệu có Kiểm soát (Controlled Intake)

Tài liệu thiết kế và đặc tả kỹ thuật chi tiết cho Tầng 1 căn cứ theo Điều khoản DAT 01 - DAT 08 (Trang 5), Hợp đồng B 01 (Trang 20) và Phụ lục C (Trang 21) của tài liệu [SongNhat_Vietnam_Voice_of_Customer_Insight_Engine_RFP.md](file:///c:/Users/ACER/__SongNhat/Voice%20of%20Customer%20Insight%20Engine/SongNhat_Vietnam_Voice_of_Customer_Insight_Engine_RFP.md).

---

## 1. Sơ đồ Phạm vi Tiếp nhận và Ánh xạ Dữ liệu (Mermaid Diagram)

```mermaid
flowchart TB
    %% STYLE DEFINITIONS
    classDef hf fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#0D47A1
    classDef etl fill:#FFF3E0,stroke:#E65100,stroke-width:2px,color:#BF5700
    classDef csv fill:#F3E5F5,stroke:#6A1B9A,stroke-width:2px,color:#4A148C
    classDef core fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20
    classDef out fill:#ECEFF1,stroke:#455A64,stroke-width:2px,color:#263238
    classDef error fill:#FFEBEE,stroke:#C62828,stroke-width:2px,color:#B71C1C

    %% 1. HUGGING FACE DATA SOURCES
    subgraph HF["01 - NGUON DU LIEU THUC TE (Hugging Face Datasets)"]
        direction LR
        HF1["CSConDa HCMUT<br/>ura-hcmut/<br/>Vietnamese-Customer-Support-QA<br/><br/>Hoi thoai CSKH thuc te<br/>va xu ly su vu ky thuat"]:::hf
        HF2["UIT-VSFC<br/>uitnlp/<br/>vietnamese_students_feedback<br/><br/>Phan hoi quy trinh<br/>va van hanh"]:::hf
        HF3["UIT-ViSFD<br/>SEACrowd/uit_visfd<br/><br/>Danh gia khao sat<br/>kem diem so va khia canh"]:::hf
    end

    %% 2. ETL ADAPTER
    subgraph ETL["02 - PIPELINE ANH XA VA BO SUNG METADATA"]
        direction LR
        ETL1["Raw Text Extraction<br/>Trich xuat van ban goc<br/><br/>Bo sung metadata:<br/>record_id - case_id<br/>customer_id - event_time"]:::etl
        ETL2["Author Role Mapping<br/>Phan tach vai tro tac gia<br/><br/>Gan nhan author_role:<br/>customer / staff_note"]:::etl
        ETL3["Schema Normalization<br/>Dong goi va chuan hoa<br/>Schema CSV theo Phu luc C"]:::etl

        ETL1 --> ETL2 --> ETL3
    end

    %% 3. CSV TARGET SCHEMAS
    subgraph CSV["03 - BO 3 TEP CSV THEO CHUAN RFP"]
        direction LR
        CSV1["service_case_feedback.csv<br/><br/>Ca su co va<br/>bao tri dich vu"]:::csv
        CSV2["curated_correspondence.csv<br/><br/>Thu tu va email<br/>thuong mai B2B"]:::csv
        CSV3["survey_responses.csv<br/><br/>Khao sat diem so<br/>NPS / CSAT"]:::csv
    end

    %% 4. CONTROLLED INTAKE ENGINE
    subgraph CORE["04 - TANG 1: CONTROLLED INTAKE ENGINE"]
        direction TB
        R1["R1 - Schema Validation<br/>Xac thuc Schema va kieu du lieu<br/>DAT 01 - B 01<br/>Bat buoc du truong, dung format"]:::core
        R2["R2 - Batch Reconciliation<br/>Kiem soat lo va doi soat dong<br/>DAT 02<br/>Reconcile: received / accepted / quarantined"]:::core
        R3["R3 - Deduplication & Idempotency<br/>Loc trung lap va bao dam tinh luy dang<br/>DAT 05<br/>MD5 / SHA256 - Idempotent Retry"]:::core
        R4["R4 - Text Length Validation<br/>Kiem tra gioi han van ban<br/>DAT 03<br/>Toi da 8.000 ky tu<br/>Khong cat xen am tham"]:::core
        R5["R5 - Entity Isolation<br/>Co lap lien ket khach hang va vu viec<br/>DAT 04<br/>Khong tu dong gop Entity"]:::core
        R6["R6 - PII Redaction<br/>Khu dinh danh ca nhan<br/>SEC 03<br/>Regex che so dien thoai va email"]:::core

        R1 --> R2 --> R3 --> R4 --> R5 --> R6
    end

    %% 5. INTAKE OUTPUT
    subgraph OUTPUT["05 - DAU RA CHO TANG 2: NLP ENGINE"]
        direction LR
        OUT1["Normalized Store<br/>Kho du lieu tiep nhan hop le<br/><br/>Lineage Metadata Ledger"]:::out
        OUT2["Quarantine Review Queue<br/>Hang doi kiem duyet thu cong<br/><br/>Ban ghi loi hoac vuot nguong"]:::error
    end

    %% DATA FLOWS
    HF1 -->|Yeu cau ho tro| ETL1
    HF2 -->|Thu tu trao doi| ETL1
    HF3 -->|Phan hoi khao sat| ETL1

    ETL3 --> CSV1
    ETL3 --> CSV2
    ETL3 --> CSV3

    CSV1 --> R1
    CSV2 --> R1
    CSV3 --> R1

    R6 -->|Ban ghi dat chuan| OUT1

    R1 -.->|Loi format| OUT2
    R4 -.->|Vuot gioi han| OUT2
```

---

## 2. Bảng Ánh xạ Chi tiết từ Hugging Face sang 3 Schema CSV

| Nguồn Hugging Face | Tệp CSV đích | Trường trích xuất gốc | Metadata bổ sung theo Phụ lục C |
| :--- | :--- | :--- | :--- |
| `ura-hcmut/Vietnamese-Customer-Support-QA` (CSConDa) | `service_case_feedback.csv` | Lượt hỏi/yêu cầu hỗ trợ kỹ thuật -> cột `text` | `record_id`: Chuỗi định danh bất biến<br/>`case_id`: Mã sự cố (CASE_xxxx)<br/>`customer_id`: Mã định danh doanh nghiệp<br/>`channel`: ticket/service_sheet<br/>`event_time`: Timestamp ISO 8601<br/>`author_role`: customer hoặc staff_note<br/>`product_id`: Mã thiết bị/phụ tùng |
| `uitnlp/vietnamese_students_feedback` (UIT-VSFC) | `curated_correspondence.csv` | Đoạn văn nhận xét phản hồi -> cột `text` | `record_id`: Chuỗi định danh bất biến<br/>`case_id`: Mã hợp đồng/báo giá<br/>`customer_id`: Mã định danh doanh nghiệp<br/>`channel`: email<br/>`event_time`: Timestamp ISO 8601<br/>`author_role`: customer<br/>`subject`: Tiêu đề thư B2B |
| `SEACrowd/uit_visfd` (UIT-ViSFD) | `survey_responses.csv` | Câu đánh giá khảo sát -> cột `text`<br/>Nhãn cảm xúc / điểm số -> cột `rating` (0-10) | `record_id`: Chuỗi định danh bất biến<br/>`customer_id`: Mã định danh doanh nghiệp<br/>`channel`: survey<br/>`event_time`: Timestamp ISO 8601<br/>`rating`: Điểm số nguyên |

---

## 3. Định nghĩa Cấu trúc 3 Schema CSV Chuẩn (Data Contracts)

### 3.1. `service_case_feedback.csv` (Sự cố và dịch vụ kỹ thuật)
* `record_id` (String, PK): Định danh bất biến của bản ghi tiếp nhận.
* `case_id` (String): Mã vụ việc kỹ thuật / phiếu hỗ trợ.
* `customer_id` (String): Mã khách hàng doanh nghiệp.
* `channel` (String): Kênh tiếp nhận (`ticket`, `service_sheet`, `portal`).
* `event_time` (ISO 8601): Thời điểm phát sinh sự kiện phản hồi.
* `author_role` (String): Vai trò người viết (`customer` hoặc `staff_note`).
* `text` (String): Nội dung văn bản phản hồi.
* `product_id` (String): Mã thiết bị / động cơ liên quan.

### 3.2. `curated_correspondence.csv` (Thư từ email thương mại B2B)
* `record_id` (String, PK): Định danh duy nhất.
* `case_id` (String): Mã vụ việc hoặc mã báo giá/hợp đồng.
* `customer_id` (String): Mã khách hàng doanh nghiệp.
* `channel` (String): Cố định giá trị `email`.
* `event_time` (ISO 8601): Thời điểm gửi/nhận email.
* `author_role` (String): `customer` hoặc `staff_note`.
* `text` (String): Nội dung đoạn trao đổi đã lọc trích dẫn cũ.
* `subject` (String): Tiêu đề thư hoặc chủ đề giao dịch.

### 3.3. `survey_responses.csv` (Khảo sát điểm số)
* `record_id` (String, PK): Định danh duy nhất.
* `customer_id` (String): Mã khách hàng doanh nghiệp.
* `channel` (String): Cố định giá trị `survey`.
* `event_time` (ISO 8601): Thời điểm khách hàng hoàn tất khảo sát.
* `rating` (Integer, Nullable): Điểm số đánh giá (0-10 cho NPS, 1-5 cho CSAT).
* `text` (String, Nullable): Bình luận hoặc ý kiến đóng góp đi kèm.

---

## 4. Các Quy tắc Xử lý Nghiệp vụ Bắt buộc (DAT 01 - DAT 08, SEC 03)

* **DAT 01 (Bảo lưu nguồn gốc - Lineage):** Lưu giữ `record_id`, thời điểm nhập liệu (`import_time`), phiên bản bản ghi. Phân tách dứt khoát giữa `customer` và `staff_note`; nghiêm cấm coi ghi chú của nhân viên là trích dẫn trực tiếp của khách hàng.
* **DAT 02 (Kiểm soát lô - Batch controls):** Đối soát số lượng dòng tiếp nhận, hợp lệ và cách ly (quarantine). Quá trình nạp lại phải có tính lũy đẳng (idempotent), không để tệp cũ đè tệp mới.
* **DAT 03 (Giới hạn văn bản - Text limits):** Giới hạn tối đa 8.000 ký tự phân tích trên một bản ghi. Bản ghi vượt giới hạn hoặc lỗi mã hóa chuyển vào hàng đợi kiểm duyệt thủ công (review queue), nghiêm cấm cắt xén âm thầm (no silent truncation).
* **DAT 04 (Liên kết khách hàng và vụ việc):** Không tự động gộp (auto-merge) khách hàng hoặc vụ việc nếu thiếu khóa liên kết xác thực.
* **DAT 05 (Khử trùng lặp - Duplicate treatment):** Tự động phát hiện và loại bỏ các bản ghi trùng lặp hoàn toàn khi nạp lại.
* **SEC 03 (Khử định danh PII):** Ẩn hoặc mã hóa số điện thoại, email cá nhân và tên riêng trước khi chuyển dữ liệu sang Tầng 2.

---

## 5. Kiến trúc Module Xử lý Intake (Python Implementation)

Module tiếp nhận bao gồm 5 thành phần xử lý tuần tự:
1. `SchemaValidator`: Kiểm tra kiểu dữ liệu, các trường bắt buộc và định dạng ngày tháng ISO 8601.
2. `DeduplicationHandler`: Tạo chuỗi băm SHA-256 trên nội dung để phát hiện và ngăn chặn bản ghi trùng lặp.
3. `TextLimitEnforcer`: Kiểm đếm số ký tự Unicode, định tuyến các bản ghi quá 8.000 ký tự vào hàng đợi cách ly.
4. `PIIRedactor`: Dùng biểu thức chính quy (Regex) để che số điện thoại, email cá nhân.
5. `ManifestLogger`: Ghi nhận nhật ký tiếp nhận (Batch Manifest) để đối soát dòng dữ liệu chấp thuận và cách ly.
