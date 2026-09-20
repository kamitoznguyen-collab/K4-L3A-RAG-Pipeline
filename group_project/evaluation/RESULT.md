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
| Corpus version/commit              | 5 legal PDF + 5 news JSON, 88 chunks |
| Golden dataset size                | 38 |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.53 — đo trên 10 query in-domain (0.621–0.874) và 8 query out-of-domain (0.105–0.442) |

## Configurations

- **Config A — dense-only:** `retrieve(use_reranking=False)` — chỉ lấy top-k từ ChromaDB theo cosine similarity.
- **Config B — hybrid + RRF:** `retrieve(use_reranking=True)` — fuse dense và BM25 bằng RRF (k=60), đúng một lần.

Hai config dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| ------ | -------: | -------: | --------: |
| Faithfulness | 0.689 | 0.824 | +0.135 |
| Answer relevance | 0.693 | 0.828 | +0.135 |
| Context recall | 0.737 | 0.895 | +0.158 |
| Context precision | 0.586 | 0.663 | +0.077 |
| **Average** | 0.676 | 0.803 | +0.126 |

## A/B comparison

- Cấu hình tốt hơn: **B (hybrid + RRF)** (chênh lệch average +0.126).
- Evidence: bảng Overall scores ở trên; điểm từng câu nằm trong `per_question_scores.json`.
- Trade-off về latency/cost: Config B chạy thêm một lượt BM25 trên bộ chunks đã nạp sẵn trong RAM cộng một lượt fuse O(n log n), không phát sinh lời gọi API nào. Chi phí token của hai config bằng nhau vì cùng `top_k`.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| -: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
| 1 | Học bổng Jensen Huang dành cho sinh viên năm mấy? | B (hybrid + RRF) | 0.000 | 0.000 | 0.000 | 0.000 | retrieval | RRF đẩy chunk dense đúng ra khỏi top-5; Config A đạt 0.985 |
| 2 | Bài luận nộp hồ sơ học bổng Sigma Gold có yêu cầu gì về hình thức? | B (hybrid + RRF) | 0.000 | 0.000 | 0.000 | 0.000 | retrieval | RRF đẩy chunk dense đúng ra khỏi top-5; Config A đạt 0.995 |
| 3 | Sinh viên ứng tuyển Sigma Gold phải qua hình thức tuyển chọn nào? | B (hybrid + RRF) | 0.000 | 0.000 | 0.000 | 0.000 | retrieval | RRF đẩy chunk dense đúng ra khỏi top-5; Config A đạt 0.992 |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
| 1 | Dùng cross-encoder cho đường hybrid khi latency cho phép | Trong 38 câu, Config B vẫn từ chối 4 câu; ba câu trong số đó Config A trả lời tốt, cho thấy RRF đã làm mất chunk dense đúng. Thí nghiệm 15 câu cho thấy cross-encoder tăng Config B từ 0.745 lên 0.834 và context precision từ 0.490 lên 0.733 | Giảm các ca hybrid thua dense và tăng độ chính xác context | Chạy lại đủ 38 câu với `USE_CROSS_ENCODER=true`, so riêng bốn ca bị từ chối và báo cả latency |
| 2 | Chạy PageIndex end-to-end bằng API key hợp lệ | Code fallback đã có timeout/cache và không tạo nội dung mock, nhưng chưa từng được kiểm chứng với provider thật | Xác nhận đường vectorless hoạt động khi dense score dưới 0.53 | Dùng một query ngoài ngưỡng, kiểm tra `retrieval_method=pageindex`, citation và thời gian phản hồi |
| 3 | Đo factorial 2×2 cho cross-encoder và HyDE trên 38 câu | Hai bonus mới chỉ được cô lập trên dataset 15 câu; chưa biết hiệu ứng tương tác khi bật đồng thời trên bộ 38 câu | Chọn cấu hình production theo chất lượng, latency và chi phí thay vì suy đoán | Chạy bốn cấu hình off/off, on/off, off/on, on/on với cùng seed, evaluator và `top_k` |
| 4 | Thêm golden dataset hội thoại nhiều lượt | `rewrite_followup()` mới được kiểm chứng bằng demo; dataset hiện tại chỉ gồm câu độc lập | Đo được độ chính xác rewrite và chất lượng câu trả lời follow-up | Soạn các chuỗi 3–4 lượt có đại từ và câu rút gọn, chấm cả rewritten query lẫn answer cuối |

**Hybrid không thắng tuyệt đối.** Trên bộ 38 câu, ba câu về Jensen Huang và
Sigma Gold có Config A trả lời tốt nhưng Config B bị 0.000. RRF đã đẩy chunk mà
dense tìm đúng ra khỏi top-5. Kết luận "hybrid tốt hơn" đúng ở mức trung bình
(+0.126), không đúng với từng câu.

**Điểm 0.000 không phải hallucination.** Mọi case 0.000 đều là safe refusal —
pipeline không tìm được chunk nên trả về "Tôi không thể xác minh thông tin này
từ nguồn hiện có" thay vì bịa. Ragas chấm refusal bằng 0 ở cả 4 metric, nên điểm
thấp ở đây phản ánh **recall của retrieval**, không phải độ trung thực của LLM.

**Độ tin cậy của bảng điểm.** Corpus 10 tài liệu / 88 chunk vẫn nhỏ, và golden
dataset được soạn từ chính corpus đó nên điểm có thiên lệch lạc quan. Con số dùng
được để so sánh giữa các cấu hình, không dùng để tuyên bố chất lượng tuyệt đối.

## Bonus experiments

### So sánh ba cấu hình reranking

Bảng dưới dùng cùng bộ 15 câu, generator, evaluator và `top_k`; đây là phép đo
riêng cho cross-encoder, không trộn với kết quả chính 38 câu ở đầu báo cáo.

| Cấu hình | Average | Câu bị từ chối | So với cấu hình trước |
|---|---:|---:|---:|
| Dense-only | 0.537 | 5/15 | — |
| Hybrid + RRF | 0.745 | 2/15 | +0.208 |
| Hybrid + RRF + cross-encoder | **0.834** | **1/15** | **+0.089** |

Cross-encoder tăng latency từ khoảng 62 lên 948 ms/query (~15 lần), nhưng chạy
local và không tốn thêm API. Bảng này đáp ứng phép đối chứng ba chiều; kết quả
chi tiết theo metric nằm ở dòng thí nghiệm tương ứng bên dưới.

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| **Cross-encoder reranking sau RRF** — `rerank_cross_encoder()` dùng `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`; RRF trả `top_k*4` ứng viên rồi cross-encoder chấm lại từng cặp (query, chunk) và cắt xuống `top_k`. Bật bằng `USE_CROSS_ENCODER=true` | Config A 0.537 / Config B 0.745 | B **+0.089** (0.745 → 0.834). Mạnh nhất ở context precision: 0.490 → **0.733** (+0.243); context recall 0.867 → 0.933. Faithfulness gần như đứng yên (−0.002) | **62 → 948 ms/query** (×15). Model chạy local nên không tốn API, chỉ tốn CPU | **Tốt hơn RRF rõ rệt.** RRF chỉ nhìn thứ hạng nên không biết chunk nào thực sự trả lời được; cross-encoder đọc cả cặp nên loại được chunk lọt top chỉ nhờ xếp hạng — đúng chỗ context precision tăng mạnh. Số câu bị từ chối B giảm 2→1. Đối chứng: Config A đi 0.537 → 0.547, tức không đổi trong phạm vi nhiễu (~0.01), đúng như phải thế vì cross-encoder chỉ nằm trên đường hybrid |
| **HyDE** — `expand_query()` cho LLM sinh một đoạn 3-4 câu theo văn phong văn bản quy định rồi ghép với query gốc để embed. Bật bằng `USE_HYDE=true` | Config A 0.537 / Config B 0.745 | A **+0.075** (0.537 → 0.612), B **+0.066** (0.745 → 0.811). Context precision B 0.490 → 0.577; context recall B 0.867 → 0.933 | **62 → 2012 ms/query** (×32), và **+1 lời gọi LLM cho mỗi query** — đây là chi phí API thật, nhân theo lưu lượng | **Có cải thiện nhưng đắt.** Lý do hiệu quả: câu hỏi và tài liệu khác văn phong ("điều kiện xét học bổng là gì?" so với "Kết quả học tập đạt loại Khá trở lên"), câu trả lời giả định kéo vector query về phía văn phong tài liệu. Nội dung sinh ra thường sai (LLM bịa GPA 2.5, 12 tín chỉ) nhưng không sao vì nó chỉ dùng làm vector tìm kiếm, không hiển thị. So với cross-encoder thì HyDE kém hơn (+0.066 so với +0.089) mà đắt hơn nhiều — nếu chỉ chọn một thì chọn cross-encoder |
| **Mở rộng golden dataset 15 → 38 câu**, phủ 10/10 tài liệu (trước 9/10; `hoc-bong-dinh-thien-ly.md` là tài liệu dài nhất corpus, 17KB, trước đó không có câu hỏi nào) | Dataset 15 câu: A 0.537 / B 0.745, tỉ lệ từ chối A 33% / B 13% | Dataset 38 câu: A 0.552 / B **0.718**, tỉ lệ từ chối A **32%** / B **16%**. **Đây không phải cải thiện hay suy giảm** — đổi thước đo thì điểm không so trực tiếp được | Mỗi lượt eval lâu gấp ~2.5 lần (khoảng 25 phút thay vì 10-12), chi phí API tăng tương ứng | **Xác nhận dataset cũ không bị lệch, và tăng độ phân giải 2.5 lần.** Tỉ lệ từ chối gần như không đổi (A 33%→32%, B 13%→16%) tức bộ 15 câu vốn đã đại diện đúng cho corpus. Giá trị nằm ở chỗ khác: với 15 câu, mỗi câu đổi trạng thái làm điểm trung bình dịch ~0.067 — lớn hơn cả khoảng cách giữa hai cấu hình đang so. Với 38 câu con số đó xuống ~0.026, nên những chênh lệch cỡ 0.05-0.09 (như cross-encoder +0.089) mới đọc được một cách đáng tin |
| **Conversation memory** — `rewrite_followup()` trong `app.py` dùng LLM viết lại câu hỏi follow-up thành câu đứng độc lập, dựa trên 3 lượt hội thoại gần nhất | Mỗi câu hỏi gửi độc lập; hỏi tiếp "có bao nhiêu suất?" thì bot không biết đang nói về học bổng nào | Không đo bằng Ragas — golden dataset gồm các câu độc lập nên không phản ánh được hội thoại nhiều lượt. Kiểm chứng bằng demo | +1 lời gọi LLM mỗi lượt, chỉ khi đã có lịch sử hội thoại | Có hiển thị *"Hiểu câu hỏi thành: ..."* để người dùng thấy bot hiểu gì — quan trọng vì rewrite sai thì câu trả lời lạc đề mà không rõ tại sao. LLM lỗi thì trả về câu hỏi gốc, không làm chết chatbot. **Muốn đo được cần một golden dataset dạng hội thoại nhiều lượt** — chưa làm |
| **UI citation highlighting** — `highlight_overlap()` bôi vàng những đoạn trong chunk mà câu trả lời dùng lại gần như nguyên văn, khớp bằng `difflib.SequenceMatcher` | Panel nguồn hiển thị nguyên chunk, người đọc phải tự dò xem câu trả lời lấy từ đâu | Không đo bằng metric — đây là cải thiện khả năng kiểm chứng của người đọc | Không đáng kể; chạy local, không gọi LLM | Cố ý **không** dùng LLM để chọn đoạn highlight: khâu hiển thị nguồn là chỗ người đọc dựa vào để kiểm chứng, thêm một bước LLM vào đó là thêm một chỗ có thể bịa. `difflib` chỉ khớp chuỗi con chung nên highlight luôn là text có thật trong chunk. Ngưỡng 12 ký tự để không bôi vào hư từ |
| **Đo dao động giữa hai lần chạy** — chạy lại đúng cùng cấu hình, chỉ khác ở chỗ `url` được đưa vào metadata (metadata không được embed nên không ảnh hưởng retrieval) | Config A 0.531 / Config B 0.737 | A −0.007, B **+0.008** | Không đổi | Evaluator ổn định. Dao động giữa hai lần chạy chỉ khoảng 0.01, nên các chênh lệch lớn hơn 0.05 trong báo cáo này đọc được, không phải nhiễu |
| **Loại khối nguồn khỏi text trước khi chunk** — bỏ dòng `Nguồn:` / `Ngày thu thập:` ra khỏi nội dung đem chunk, chỉ giữ URL trong metadata | Config A 0.524 / Config B 0.745 | A −0.083, B **−0.218** | Không đổi (88 → 85 chunk, cùng số lời gọi API) | **Bác bỏ giả thuyết ban đầu.** Lập luận là khối nguồn chiếm chỗ chunk đầu và dense chấm nó cao dù nó không trả lời được gì. Nhưng đo ra thì tệ hơn hẳn: khối đó chứa tiêu đề tài liệu ở dạng text, và chính phần text đó neo chủ đề cho các chunk quanh nó. Đã revert. Kết quả này dẫn tới khuyến nghị số 1 ở trên — thay vì **bỏ bớt** text mang tiêu đề, nên **thêm** tiêu đề vào mọi chunk |
| **Contextual chunking** — prepend tiêu đề tài liệu vào text đem đi embed (`chunk_embedding_text()` trong Task 4). `chunk["content"]` giữ nguyên text gốc, chỉ vector mang thêm tiêu đề | Config A 0.537 / Config B 0.745 (đo lại với `CONTEXTUAL_CHUNKING = False`, cùng `max_workers=4`) | A **+0.210**, B **+0.106**. Context precision của B tăng mạnh nhất: 0.490 → 0.712 (+0.222); context recall 0.867 → 0.933 | Không đổi — tiêu đề chỉ thêm ~50 ký tự vào input của model embedding local, không phát sinh lời gọi API | **Xác nhận giả thuyết.** Số câu bị từ chối vì thiếu chunk giảm A 5→3, B 2→1. Ca kiểm chứng: chunk chứa điều kiện xét học bổng UET trước đó không lọt top-40 của dense (vì chỉ liệt kê "Khá trở lên", "15 tín chỉ", không mang từ khoá chủ đề), sau khi thêm tiêu đề lên hạng 34 và lọt top-5 của `retrieve()` |
