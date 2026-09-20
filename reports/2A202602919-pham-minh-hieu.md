# Individual contribution report

## Thông tin

- Họ và tên: Phạm Minh Hiếu
- Mã học viên: 2A202602919
- Nhóm: K4-L3A
- Thành viên nhóm:
  - Nguyễn Thị Minh Khánh — 2A202602546
  - Nguyễn Việt Hoàng Hải — 2A202602967
  - Nguyễn Quang Huy — 2A202602421
  - Phạm Minh Hiếu — 2A202602919
- Repository/branch: `kamitoznguyen-collab/K4-L3A-RAG-Pipeline`, nhánh `feat/eval-ui`

## Phần việc đã thực hiện

| Module/deliverable | Phần việc phụ trách trên nhánh | File/commit/PR | Trạng thái |
|---|---|---|---|
| Golden dataset | Mở rộng từ 15 lên 38 câu, mỗi tài liệu 3–4 câu, phủ đủ 10/10 tài liệu và bổ sung tài liệu Đinh Thiện Lý trước đó chưa có case | `group_project/evaluation/golden_dataset.json`, commit `84e615d` | Done |
| Conversation memory | Viết `rewrite_followup()` dùng ba lượt hội thoại gần nhất để biến câu hỏi phụ thuộc ngữ cảnh thành câu đứng độc lập | `app.py` | Done |
| Khả năng quan sát | Hiển thị “Hiểu câu hỏi thành…” khi query được rewrite; lỗi LLM thì quay về câu gốc thay vì làm hỏng chatbot | `app.py` | Done |
| Citation highlighting | Viết `highlight_overlap()` dùng `difflib.SequenceMatcher`, escape HTML và bôi vàng đoạn trùng giữa answer với chunk nguồn | `app.py` | Done |
| Báo cáo thí nghiệm | Ghi tác động của dataset mới, memory và highlighting cùng giới hạn đo lường | `group_project/evaluation/experiments/hieu.md` | Done |

Kiểm chứng tại thời điểm hoàn thành nhánh: `pytest -q` → 20/20 pass.

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Mở rộng dataset theo độ phủ tài liệu, không chỉ tăng số câu.
   **Lý do/evidence:** Bộ 15 câu thiếu hoàn toàn `hoc-bong-dinh-thien-ly.md` và
   mỗi câu làm trung bình dịch khoảng 0.067, lớn hơn nhiều cải tiến cần đo. Bộ 38
   câu phủ 10/10 tài liệu, mỗi câu chỉ làm trung bình dịch khoảng 0.026.
   **Trade-off:** Một lượt evaluation lâu khoảng 25 phút thay vì 10–12 phút và
   chi phí API tăng xấp xỉ 2.5 lần.

2. **Quyết định:** Highlight bằng so khớp chuỗi local, không nhờ LLM chọn bằng
   chứng.
   **Lý do/evidence:** Panel nguồn là nơi người dùng kiểm chứng câu trả lời; dùng
   thêm LLM ở bước này tạo thêm một điểm có thể bịa. `difflib` chỉ bôi text thực
   sự tồn tại trong chunk và HTML được escape trước khi render.
   **Trade-off:** Chỉ bắt được đoạn answer dùng lại gần nguyên văn; các câu diễn
   đạt lại mạnh có thể không có highlight dù citation vẫn đúng.

## Kiểm thử và kết quả

- Dataset mới có **38 câu**, phủ **10/10 tài liệu**; thống kê mỗi tài liệu 3–4
  câu và đủ `question`, `expected_answer`, `expected_context`, `source_doc_id`.
- Phép đo riêng khi đổi dataset: bộ 15 câu đạt A 0.537 / B 0.745; bộ 38 câu đạt
  A 0.552 / B 0.718. Hai cặp số **không so trực tiếp** vì đã đổi thước đo. Tỉ lệ
  từ chối gần như giữ nguyên (A 33%→32%, B 13%→16%), cho thấy bộ cũ không lệch
  lớn nhưng có độ phân giải thấp.
- Sau khi hợp nhất contextual chunking và chạy lại trên 38 câu: Config A
  **0.676**, Config B **0.803**, Config B có 4/38 câu bị từ chối.
- Kịch bản demo memory: hỏi “Học bổng Sigma Gold trị giá bao nhiêu?”, tiếp theo
  “Có bao nhiêu suất?”; UI hiển thị câu được hiểu lại trước khi retrieval.
- Kịch bản demo citation: mở panel nguồn dưới câu trả lời, đoạn văn trùng được
  bôi vàng; chuỗi HTML trong nguồn được escape để không chèn markup ngoài ý muốn.

## Điều còn hạn chế

- Golden dataset vẫn được soạn từ chính corpus, vì vậy phù hợp để so cấu hình
  nội bộ hơn là ước lượng hiệu quả ngoài thực tế.
- Conversation memory mới được kiểm chứng bằng demo, chưa có bộ hội thoại nhiều
  lượt và metric tự động.
- Highlight dựa trên overlap ký tự nên không nhận ra đầy đủ paraphrase tiếng
  Việt. Nếu có thêm thời gian, tôi sẽ bổ sung test UI và dataset hội thoại nhiều
  lượt trước khi thay đổi thuật toán highlight.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh phần việc của nhánh mình phụ trách và có thể
giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Phạm Minh Hiếu
