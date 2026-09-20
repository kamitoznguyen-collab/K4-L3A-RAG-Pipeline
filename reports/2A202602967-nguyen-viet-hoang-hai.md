# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Việt Hoàng Hải
- Mã học viên: 2A202602967
- Nhóm: K4-L3A
- Thành viên nhóm:
  - Nguyễn Thị Minh Khánh — 2A202602546
  - Nguyễn Việt Hoàng Hải — 2A202602967
  - Nguyễn Quang Huy — 2A202602421
  - Phạm Minh Hiếu — 2A202602919
- Repository/branch: `kamitoznguyen-collab/K4-L3A-RAG-Pipeline`, nhánh `feat/advanced-rerank`

## Phần việc đã thực hiện

| Module/deliverable | Phần việc phụ trách trên nhánh | File/commit/PR | Trạng thái |
|---|---|---|---|
| Cross-encoder reranking | Cài `rerank_cross_encoder()` bằng model multilingual, chấm lại từng cặp query/chunk sau RRF | `src/task7_reranking.py`, commit `2de1a32` | Done |
| Tích hợp reranker | Mở rộng pool RRF lên `top_k*4`, gọi cross-encoder rồi cắt về `top_k`; lỗi model thì giữ nguyên thứ tự RRF | `src/task9_retrieval_pipeline.py` | Done |
| HyDE query expansion | Dùng LLM sinh đoạn trả lời giả định theo văn phong quy định, ghép với query gốc trước dense retrieval; provider lỗi thì dùng query gốc | `src/task9_retrieval_pipeline.py` | Done |
| Cấu hình A/B | Thêm `USE_CROSS_ENCODER` và `USE_HYDE`, mặc định tắt để đo từng biến độc lập | `.env.example`, `src/task9_retrieval_pipeline.py` | Done |
| Báo cáo thí nghiệm | Đo chất lượng, latency và chi phí của từng tính năng so với baseline | `group_project/evaluation/experiments/hai.md` | Done |

Kiểm chứng tại thời điểm hoàn thành nhánh: `pytest -q` → 20/20 pass.

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Đặt cross-encoder sau RRF, không thay thế dense/BM25/RRF.
   **Lý do/evidence:** RRF rẻ và phù hợp để rút khoảng 20 ứng viên xuống một pool
   nhỏ; cross-encoder chỉ cần đọc pool đó để đánh giá mức liên quan thực sự của
   từng cặp query/chunk. Config B tăng 0.089, chủ yếu nhờ context precision tăng
   0.243.
   **Trade-off:** Latency tăng từ 62 lên 948 ms/query (~15 lần), nhưng model chạy
   local và không phát sinh API call.

2. **Quyết định:** HyDE giữ cả query gốc bên cạnh câu trả lời giả định.
   **Lý do/evidence:** Đoạn HyDE giúp thu hẹp khoảng cách văn phong giữa câu hỏi
   và văn bản quy định, nhưng LLM có thể bịa số liệu. Query gốc đóng vai trò neo
   để vector không trôi hoàn toàn theo nội dung giả.
   **Trade-off:** Config B tăng 0.066 nhưng latency lên 2012 ms/query (~32 lần)
   và tốn thêm một lời gọi LLM mỗi query.

## Kiểm thử và kết quả

- **Cross-encoder A/B trên bộ 15 câu:**

  | Chỉ số | Baseline | Cross-encoder | Thay đổi |
  |---|---:|---:|---:|
  | Config A average | 0.537 | 0.547 | +0.010 |
  | Config B average | 0.745 | 0.834 | +0.089 |
  | Config B context precision | 0.490 | 0.733 | +0.243 |
  | Config B context recall | 0.867 | 0.933 | +0.066 |
  | Latency | 62 ms/query | 948 ms/query | ×15 |

- **Đối chứng ba cấu hình theo yêu cầu rubric, trên cùng bộ 15 câu:**

  | Cấu hình | Average | Câu bị từ chối | Chênh lệch liền trước |
  |---|---:|---:|---:|
  | Dense-only | 0.537 | 5/15 | — |
  | Hybrid + RRF | 0.745 | 2/15 | +0.208 |
  | Hybrid + RRF + cross-encoder | **0.834** | **1/15** | **+0.089** |

- **HyDE A/B trên bộ 15 câu:**

  | Chỉ số | Baseline | HyDE | Thay đổi |
  |---|---:|---:|---:|
  | Config A average | 0.537 | 0.612 | +0.075 |
  | Config B average | 0.745 | 0.811 | +0.066 |
  | Config B context precision | 0.490 | 0.577 | +0.087 |
  | Config B context recall | 0.867 | 0.933 | +0.066 |
  | Latency | 62 ms/query | 2012 ms/query | ×32 |

- Kết luận từ phép đo: nếu chỉ bật một tính năng, ưu tiên cross-encoder vì tăng
  điểm nhiều hơn và không tốn API. Hai tính năng vẫn để mặc định tắt nhằm giữ
  đường baseline nhanh và cho phép demo A/B sạch.
- Kết quả tích hợp mặc định trên 38 câu (chưa bật hai cờ): Config B **0.803**.

## Điều còn hạn chế

- Model cross-encoder cần tải lần đầu và chạy CPU khá chậm; máy demo yếu có thể
  thấy độ trễ lớn hơn số đo hiện tại.
- HyDE không bảo đảm nội dung giả định đúng. Dù nó chỉ phục vụ retrieval, query
  expansion sai vẫn có thể làm thứ hạng xấu đi ở từng câu.
- Chưa có bảng factorial 2×2 trên toàn bộ 38 câu cho bốn trạng thái
  cross-encoder/HyDE. Nếu có thêm thời gian, đây là phép đo đầu tiên tôi bổ sung.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh phần việc của nhánh mình phụ trách và có thể
giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Việt Hoàng Hải
