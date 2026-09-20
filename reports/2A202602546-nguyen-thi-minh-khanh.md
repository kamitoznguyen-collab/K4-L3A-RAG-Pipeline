# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Thị Minh Khánh
- Mã học viên: 2A202602546
- Nhóm: K4-L3A
- Thành viên nhóm:
  - Nguyễn Thị Minh Khánh — 2A202602546
  - Nguyễn Việt Hoàng Hải — 2A202602967
  - Nguyễn Quang Huy — 2A202602421
  - Phạm Minh Hiếu — 2A202602919
- Repository/branch: `kamitoznguyen-collab/K4-L3A-RAG-Pipeline`, nhánh `feat/retrieval-quality`

## Phần việc đã thực hiện

| Module/deliverable | Phần việc phụ trách trên nhánh | File/commit/PR | Trạng thái |
|---|---|---|---|
| Contextual chunking | Viết `chunk_embedding_text()` để thêm tiêu đề tài liệu vào text đem embed; giữ nguyên `chunk["content"]` cho generation và contract | `src/task4_chunking_indexing.py`, commit `cefa2c3` | Done |
| A/B evaluation | Cho phép bật/tắt contextual chunking, đo cùng cấu hình và ghi số liệu trước/sau | `group_project/evaluation/eval_pipeline.py`, `group_project/evaluation/experiments/khanh.md` | Done |
| Độ tin cậy evaluator | Hạ Ragas xuống `max_workers=4`, tăng retry/timeout và thêm guard dừng khi toàn bộ phép chấm đồng loạt trả 0 | `group_project/evaluation/eval_pipeline.py`, commit `cefa2c3` | Done |
| Phân tích lỗi retrieval | Theo dõi ca UET: chunk chứa “Khá trở lên”, “15 tín chỉ” trước đó không lọt top-40 dense; sau cải tiến lên hạng 34 và lọt top-5 pipeline | `group_project/evaluation/experiments/khanh.md` | Done |

Kiểm chứng tại thời điểm hoàn thành nhánh: `pytest -q` → 20/20 pass.

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Chỉ thêm tiêu đề vào đầu vào embedding, không sửa nội dung
   chunk được trả về.
   **Lý do/evidence:** Các chunk chi tiết thường chỉ chứa con số và điều kiện,
   không lặp lại tên học bổng/trường nên dense search khó nối với câu hỏi. Giữ
   nguyên `content` tránh làm citation khác văn bản gốc và không phá giới hạn
   kích thước chunk trong contract.
   **Trade-off:** Vector có thêm khoảng 50 ký tự tiêu đề; chi phí embedding tăng
   rất nhỏ nhưng index phải được dựng lại để thay đổi có hiệu lực.

2. **Quyết định:** Chặn kết quả evaluation toàn 0 thay vì tin rằng đó là lỗi hệ
   thống RAG.
   **Lý do/evidence:** Khi DeepSeek bị throttle, Ragas từng âm thầm trả 0 cho cả
   60 phép chấm mà không ghi lỗi. Guard kiểm tra kết quả đồng loạt 0 và yêu cầu
   giảm concurrency/chạy lại.
   **Trade-off:** Một hệ thống thực sự rất kém và cho toàn 0 cũng bị dừng để kiểm
   tra thủ công; đổi lại không thể vô tình công bố một báo cáo sai hoàn toàn.

## Kiểm thử và kết quả

- **A/B trên cùng bộ 15 câu, chỉ đổi `CONTEXTUAL_CHUNKING`:**

  | Chỉ số | Baseline | Contextual | Thay đổi |
  |---|---:|---:|---:|
  | Config A average | 0.537 | 0.747 | +0.210 |
  | Config B average | 0.745 | 0.851 | +0.106 |
  | Config B context precision | 0.490 | 0.712 | +0.222 |
  | Config B context recall | 0.867 | 0.933 | +0.066 |
  | Câu bị từ chối Config A | 5/15 | 3/15 | −2 |
  | Câu bị từ chối Config B | 2/15 | 1/15 | −1 |

- Latency/cost gần như không đổi: không thêm API call, chỉ thêm tiêu đề ngắn vào
  input model embedding local.
- Kết quả tích hợp cuối trên 38 câu: Config A **0.676**, Config B **0.803**;
  contextual chunking được bật mặc định trong bản tích hợp.
- Lỗi quan trọng đã xử lý: Ragas throttle trả toàn 0; hạ `max_workers` từ mặc
  định 16 xuống 4 và thêm fail-fast guard.

## Điều còn hạn chế

- Cải tiến phụ thuộc chất lượng metadata `title`; tài liệu thiếu hoặc đặt tiêu
  đề quá chung sẽ hưởng lợi ít.
- Thí nghiệm riêng của nhánh chạy trên 15 câu. Kết quả 38 câu là phép đo tích
  hợp, không thể dùng để cô lập hoàn toàn đóng góp của contextual chunking.
- Nếu có thêm thời gian, tôi sẽ thử context sinh tự động 1–2 câu cho từng chunk
  và đo thêm latency/index size, thay vì chỉ prepend tiêu đề.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh phần việc của nhánh mình phụ trách và có thể
giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Thị Minh Khánh
