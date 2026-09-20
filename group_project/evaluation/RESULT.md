# RAG evaluation results

Mọi con số trong file này do `group_project/evaluation/eval_pipeline.py` sinh ra
từ một lần chạy thật trên golden dataset. Không có giá trị nào được điền tay.

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Ragas 0.1.21 |
| Evaluator model                    | deepseek-chat (deepseek) |
| Generator model                    | deepseek-chat (deepseek) |
| Embedding model                    | paraphrase-multilingual-MiniLM-L12-v2 (sentence_transformers) |
| Corpus version/commit              | 3 legal PDF + 5 news JSON, 16 chunks |
| Golden dataset size                | 15 |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.53 — đo trên 10 query in-domain (0.621–0.874) và 8 query out-of-domain (0.105–0.442) |

## Configurations

- **Config A — dense-only:** `retrieve(use_reranking=False)` — chỉ lấy top-k từ ChromaDB theo cosine similarity.
- **Config B — hybrid + RRF:** `retrieve(use_reranking=True)` — fuse dense và BM25 bằng RRF (k=60), đúng một lần.

Hai config dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| ------ | -------: | -------: | --------: |
| Faithfulness | 0.544 | 0.779 | +0.234 |
| Answer relevance | 0.581 | 0.843 | +0.262 |
| Context recall | 0.600 | 0.867 | +0.267 |
| Context precision | 0.372 | 0.490 | +0.118 |
| **Average** | 0.524 | 0.745 | +0.220 |

## A/B comparison

- Cấu hình tốt hơn: **B (hybrid + RRF)** (chênh lệch average +0.220).
- Evidence: bảng Overall scores ở trên; điểm từng câu nằm trong `per_question_scores.json`.
- Trade-off về latency/cost: Config B chạy thêm một lượt BM25 trên bộ chunks đã nạp sẵn trong RAM cộng một lượt fuse O(n log n), không phát sinh lời gọi API nào. Chi phí token của hai config bằng nhau vì cùng `top_k`.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| -: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
| 1 | Sinh viên chương trình chuẩn của UET cần đạt điều kiện gì để được xét  | A (dense-only) | 0.000 | 0.000 | 0.000 | 0.000 | retrieval | safe refusal do thiếu chunk — xem Recommendations |
| 2 | Quỹ học bổng khuyến khích học tập của UET được trích từ nguồn nào và b | A (dense-only) | 0.000 | 0.000 | 0.000 | 0.000 | retrieval | safe refusal do thiếu chunk — xem Recommendations |
| 3 | Học bổng Jensen Huang yêu cầu GPA và chứng chỉ ngoại ngữ tối thiểu bao | A (dense-only) | 0.000 | 0.000 | 0.000 | 0.000 | retrieval | safe refusal do thiếu chunk — xem Recommendations |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
| 1 | Prepend tiêu đề tài liệu vào nội dung từng chunk (contextual chunking) thay vì chỉ để nó ở chunk đầu | Với câu "điều kiện xét học bổng KKHT của UET", chunk chứa đáp án (`hoc-bong-uet-2025-2026.md::chunk-1`) **không lọt top-40 của dense**, trong khi BM25 xếp nó hạng 3. Chunk đó chỉ liệt kê "Khá trở lên", "Giỏi trở lên", "15 tín chỉ" — không có từ khoá chủ đề nào để dense nối với câu hỏi. Tên tài liệu chỉ xuất hiện ở chunk-0. Thí nghiệm ở bảng Bonus bên dưới củng cố giả thuyết này: khi **bỏ bớt** phần text chứa tiêu đề ra khỏi chunk, điểm Config B tụt từ 0.745 xuống 0.527 | Giảm số câu bị từ chối vì không tìm được chunk (hiện A 6/15, B 2/15). Đây là điểm nghẽn lớn nhất của hệ thống | Chạy lại `eval_pipeline.py`, đếm lại số câu có điểm 0.000 trong `per_question_scores.json` và so Context recall với mức hiện tại (A 0.600 / B 0.867) |
| 2 | Nới số ứng viên đưa vào RRF (hiện `top_k*2`) hoặc nâng `top_k` từ 5 lên 7 | Cũng ở câu UET: sau khi fuse, chunk chứa đáp án xếp **hạng 6** — trượt `top_k=5` đúng một bậc. Lý do là RRF cộng điểm theo thứ hạng nên ưu tiên chunk xuất hiện ở **cả hai** danh sách; chunk này chỉ có mặt trong danh sách BM25 nên chỉ được 1/63, thua các chunk kém liên quan hơn nhưng góp mặt ở cả hai bên | Cứu được nhóm câu mà đúng một ranker tìm ra — chính là nhóm mà hybrid sinh ra để phục vụ | So Context recall trước/sau. Cần cẩn thận: nâng `top_k` kéo thêm chunk nhiễu nên Context precision (đang 0.490) có thể giảm |
| 3 | Mở rộng golden dataset lên 30–40 câu, phủ đều cả 10 tài liệu | Điểm từng câu **phân cực hoàn toàn**: hoặc ~0.8–1.0, hoặc đúng 0.000, không có giá trị trung gian. 0.000 luôn là do pipeline từ chối trả lời vì thiếu chunk. Với 15 câu, mỗi câu đổi trạng thái làm average dịch ~0.06, nên chênh lệch nhỏ không đọc được. Tài liệu `hoc-bong-dinh-thien-ly.md` (dài nhất, 17KB) hiện chưa có câu hỏi nào | A/B và mọi thí nghiệm sau đó có độ phân giải đủ để kết luận | Lặp lại A/B trên dataset mới; chênh lệch đáng tin khi nó lớn hơn dao động giữa hai lần chạy (đo được ~0.01, xem Bonus) |

**Hybrid không thắng tuyệt đối.** Câu 14 (học bổng JAIF của VJU) đi ngược xu hướng:
Config A đạt 0.853 còn Config B bị 0.000. RRF đã đẩy chunk mà dense tìm đúng ra
khỏi top-5. Kết luận "hybrid tốt hơn" đúng ở mức trung bình (+0.220) chứ không
đúng với từng câu.

**Điểm 0.000 không phải hallucination.** Mọi case 0.000 đều là safe refusal —
pipeline không tìm được chunk nên trả về "Tôi không thể xác minh thông tin này
từ nguồn hiện có" thay vì bịa. Ragas chấm refusal bằng 0 ở cả 4 metric, nên điểm
thấp ở đây phản ánh **recall của retrieval**, không phải độ trung thực của LLM.

**Độ tin cậy của bảng điểm.** Corpus 10 tài liệu / 88 chunk vẫn nhỏ, và golden
dataset được soạn từ chính corpus đó nên điểm có thiên lệch lạc quan. Con số dùng
được để so sánh giữa các cấu hình, không dùng để tuyên bố chất lượng tuyệt đối.

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| **Đo dao động giữa hai lần chạy** — chạy lại đúng cùng cấu hình, chỉ khác ở chỗ `url` được đưa vào metadata (metadata không được embed nên không ảnh hưởng retrieval) | Config A 0.531 / Config B 0.737 | A −0.007, B **+0.008** | Không đổi | Evaluator ổn định. Dao động giữa hai lần chạy chỉ khoảng 0.01, nên các chênh lệch lớn hơn 0.05 trong báo cáo này đọc được, không phải nhiễu |
| **Loại khối nguồn khỏi text trước khi chunk** — bỏ dòng `Nguồn:` / `Ngày thu thập:` ra khỏi nội dung đem chunk, chỉ giữ URL trong metadata | Config A 0.524 / Config B 0.745 | A −0.083, B **−0.218** | Không đổi (88 → 85 chunk, cùng số lời gọi API) | **Bác bỏ giả thuyết ban đầu.** Lập luận là khối nguồn chiếm chỗ chunk đầu và dense chấm nó cao dù nó không trả lời được gì. Nhưng đo ra thì tệ hơn hẳn: khối đó chứa tiêu đề tài liệu ở dạng text, và chính phần text đó neo chủ đề cho các chunk quanh nó. Đã revert. Kết quả này dẫn tới khuyến nghị số 1 ở trên — thay vì **bỏ bớt** text mang tiêu đề, nên **thêm** tiêu đề vào mọi chunk |

Cả hai thí nghiệm dùng chung golden dataset, generator, evaluator, prompt và
`top_k`; biến duy nhất là thứ được nêu ở cột Experiment. Số liệu lấy từ các lần
chạy thật của `eval_pipeline.py`, không nội suy.
