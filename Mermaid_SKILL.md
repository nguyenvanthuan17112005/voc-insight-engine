# Mermaid Diagram Formatting & Enhancement Skill (Kỹ năng Định dạng & Tối ưu Sơ đồ Mermaid)

## 🎯 Objective (Mục tiêu)
Standardize and beautify raw or unformatted Mermaid.js diagrams by adding proper Vietnamese diacritics, structured line breaks, visual hierarchy, and clean styling without altering the original architecture or logical flow.
*(Chuẩn hóa và làm đẹp các sơ đồ Mermaid.js thô bằng cách bổ sung đầy đủ dấu tiếng Việt, ngắt dòng có cấu trúc, phân cấp thị giác rõ ràng và giữ nguyên vẹn kiến trúc cũng như luồng xử lý gốc.)*

---

## 📋 Core Rules (Quy tắc cốt lõi)

### 1. Text & Typography (Văn bản & Chữ viết)
* **Vietnamese Diacritics (Dấu tiếng Việt):** Convert all unaccented Vietnamese (`khong dau`) into accurate, standard Vietnamese (`có dấu`). Preserve technical terms, variable names, file names, and English acronyms in their original form.
  *(Chuyển toàn bộ tiếng Việt không dấu thành tiếng Việt có dấu chuẩn xác. Giữ nguyên các thuật ngữ kỹ thuật, tên biến, tên tệp và từ viết tắt tiếng Anh.)*
* **Visual Hierarchy (Phân cấp thị giác):** Wrap node titles or step headers in bold HTML tags (`<b>...</b>`) to separate titles from descriptions.
  *(Bọc tiêu đề của các khối hoặc tên bước trong thẻ in đậm `<b>...</b>` để tách biệt phần tiêu đề với phần mô tả chi tiết.)*

### 2. Layout & Line Breaking (Bố cục & Ngắt dòng)
* **Explicit Line Breaks (Ngắt dòng chủ động):** Replace long single-line descriptions with `<br/>` tags so nodes remain compact, balanced, and readable on standard screens. Aim for **35–45 characters per line** maximum inside boxes.
  *(Thay thế các dòng mô tả quá dài bằng thẻ `<br/>` để các khối gọn gàng, cân đối và dễ đọc. Giới hạn khoảng **35–45 ký tự mỗi dòng** bên trong các hộp.)*
* **List Formatting inside Nodes (Định dạng danh sách trong khối):** Use clean hyphens (`- `) or bullet symbols (`• `) combined with `<br/>` for multi-point steps inside a single node.
  *(Sử dụng dấu gạch ngang (`- `) hoặc dấu chấm tròn (`• `) kết hợp `<br/>` để liệt kê nhiều ý trong cùng một khối.)*
* **Symbol Polish (Chuẩn hóa ký hiệu):** Replace ASCII arrows like `->` inside text labels with clean Unicode arrows (`→`) where appropriate.
  *(Thay thế các mũi tên ASCII như `->` bên trong nhãn văn bản bằng ký hiệu mũi tên Unicode `→` cho thẩm mỹ.)*

### 3. Structural Integrity (Tính toàn vẹn cấu trúc)
* **Preserve Syntax & IDs (Giữ nguyên cú pháp & ID):** Keep all `subgraph` IDs, node IDs, link arrows (`-->`, `---`), and theme configurations (`config: theme`) strictly intact unless requested otherwise.
  *(Giữ nguyên toàn bộ ID của `subgraph`, ID của các node, mũi tên liên kết (`-->`, `---`) và cấu hình giao diện (`config: theme`) trừ khi có yêu cầu thay đổi.)*
* **Code Block Output (Định dạng đầu ra):** Always output the final result inside a clean ` ```mermaid ` code block for immediate copy-pasting.
  *(Luôn xuất kết quả cuối cùng bên trong khối mã ` ```mermaid ` để người dùng sao chép và sử dụng ngay.)*

---

## 💡 Example Usage (Ví dụ áp dụng)

**Prompt:**
> *"Format this Mermaid diagram: add proper Vietnamese accents, clean line breaks, and bold headers."*
> *(Định dạng lại sơ đồ Mermaid này: thêm dấu tiếng Việt chuẩn, ngắt dòng gọn gàng và in đậm tiêu đề.)*

**Before (Trước):**
```mermaid
P1["1. Text Extraction<br/>CSConDa: lay luot hoi -> text"]