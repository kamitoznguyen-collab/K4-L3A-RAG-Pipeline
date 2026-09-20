# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Quang Huy
- Mã học viên: 2A202602421
- Nhóm: K4-L3A
- Thành viên nhóm:
  - Nguyễn Thị Minh Khánh — 2A202602546
  - Nguyễn Việt Hoàng Hải — 2A202602967
  - Nguyễn Quang Huy — 2A202602421
  - Phạm Minh Hiếu — 2A202602919
- Repository/branch: `kamitoznguyen-collab/K4-L3A-RAG-Pipeline`, nhánh `Huy`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1–3: thu thập & chuẩn hoá | Dựng corpus từ 10 tài liệu nhóm thu thập (5 quy chế render ra PDF kèm URL gốc, 5 thông báo ra JSON), convert sang Markdown bằng MarkItDown, chuẩn hoá khoảng trắng do PDF trích ra | `src/task1_collect_legal_docs.py`, `src/task2_crawl_news.py`, `src/task3_convert_markdown.py` | Done |
| Task 4: chunking & indexing | `RecursiveCharacterTextSplitter` (500/50), `embed_texts()` dispatch theo provider, upsert ChromaDB cosine với ID ổn định | `src/task4_chunking_indexing.py` | Done |
| Task 5–6: dense & lexical | Semantic search qua ChromaDB, BM25Okapi trên cùng bộ chunks để ID khớp nhau | `src/task5_semantic_search.py`, `src/task6_lexical_search.py` | Done |
| Task 7: RRF | Fuse nhiều ranked list theo `sum(1/(k+rank))`, dedupe theo `id` | `src/task7_reranking.py` | Done |
| Task 8: vectorless fallback | Gọi PageIndex API thật, timeout + cache doc ID, thiếu key thì trả rỗng | `src/task8_pageindex_vectorless.py` | Partial — chưa có API key để chạy end-to-end |
| Task 9: retrieval pipeline | Điều phối dense + BM25 → RRF một lần → fallback theo cosine score gốc; hiệu chỉnh `SCORE_THRESHOLD` | `src/task9_retrieval_pipeline.py` | Done |
| Task 10: generation | Lost-in-the-middle reordering, context kèm title/source, citation `[Document N]`, safe refusal | `src/task10_generation.py` | Done |
| Chatbot UI | Streamlit hiển thị câu trả lời + panel nguồn (title, file, doc_type, chunk index, score, retrieval method) | `app.py` | Done |
| Evaluation nền | Dựng golden dataset ban đầu 15 câu bám nguyên văn corpus, pipeline Ragas 4 metric, A/B dense-only với hybrid + RRF và xuất báo cáo | `group_project/evaluation/`, các commit từ `b4e7322` đến `1da5193` | Done |
| Tích hợp | Chuẩn bị các hook độc lập `expand_query()` / `post_rerank()`, chia nhánh tính năng và hợp nhất ba gói cải tiến không xung đột | `src/task9_retrieval_pipeline.py`, `WORK_SPLIT.md`, nhánh `integration` | Done |

Kiểm chứng: `pytest -q` → 20/20 pass (15 contract + 5 acceptance).

Các commit `7a43099`–`6a2a2d4` là bộ khung đề bài có sẵn (docs/, `src/contracts.py`,
các file task ở dạng stub, template báo cáo), không phải phần code của nhóm.

Phần việc kê ở bảng trên nằm trong các commit của tôi trên nhánh `Huy`
(`b4e7322` trở đi). Các thành viên còn lại đóng góp ở phần việc riêng, xem báo
cáo cá nhân của từng người trong `reports/`.

Corpus dịch vụ đại học được nhóm thu thập từ Lab 7 (Embedding & Vector Store) và
tái sử dụng cho bài này; danh mục nguồn đầy đủ ở `data/sources/sources.csv`.

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Bỏ `all-MiniLM-L6-v2`, chuyển sang `paraphrase-multilingual-MiniLM-L12-v2`.
   **Lý do/evidence:** Model tiếng Anh chấm query **ngoài miền bằng tiếng Việt** ngang với query trong miền — nó chỉ nhận ra "đây là tiếng Việt" chứ không hiểu nội dung, nên không thể đặt ngưỡng fallback ở đâu cả. Bản multilingual tách được hai vùng rõ rệt trên corpus hiện tại: in-domain 0.621–0.874, out-of-domain 0.105–0.442, nên chọn `SCORE_THRESHOLD = 0.53`.
   **Trade-off:** Model multilingual nặng hơn bản tiếng Anh (118M so với 22M params) nên index chậm hơn; đổi lại fallback mới có cơ sở hoạt động.

2. **Quyết định:** RRF fuse theo `id`, không theo `content`.
   **Lý do/evidence:** `chunk_overlap = 50` làm nhiều chunk khác nhau có đoạn text trùng nhau. Fuse theo `content` sẽ gộp chúng làm một và nuốt mất kết quả hợp lệ. Contract test `test_rrf_uses_rank_deduplicates_and_marks_hybrid` bắt đúng trường hợp này.
   **Trade-off:** Phải đảm bảo dense và BM25 dùng chung bộ chunks để ID khớp nhau — BM25 vì thế chạy trên output của `chunk_documents()` chứ không tự tokenize lại tài liệu gốc.

## Kiểm thử và kết quả

- **Test đã dùng:** `pytest tests/test_contracts.py` (15 test, không gọi network) và `pytest tests/test_acceptance.py` (5 test kiểm tra corpus, golden dataset và báo cáo). Kết quả: 20/20 pass.
- **Kết quả A/B (Ragas, 15 câu, DeepSeek làm generator và evaluator):**

  | Metric | A (dense-only) | B (hybrid + RRF) | Δ |
  |---|---:|---:|---:|
  | Faithfulness | 0.544 | 0.779 | +0.234 |
  | Answer relevance | 0.581 | 0.843 | +0.262 |
  | Context recall | 0.600 | 0.867 | +0.267 |
  | Context precision | 0.372 | 0.490 | +0.118 |
  | **Average** | 0.524 | 0.745 | **+0.220** |

- **Kết quả bản tích hợp cuối (Ragas, 38 câu):** Config A đạt **0.676**,
  Config B đạt **0.803**; Config B cao hơn **+0.126** và có 4/38 câu bị từ
  chối. Đây là kết quả sau khi hợp nhất contextual chunking với dataset/UI mở
  rộng; cross-encoder và HyDE vẫn là tùy chọn A/B, mặc định tắt.

- **Lỗi đã phát hiện và cách xử lý:**
  - Ragas gọi `answer_relevancy` với `n=3` nhưng DeepSeek chỉ nhận `n=1` → trả `400 Invalid n value`. Xử lý: đặt `strictness=1`.
  - `BM25Okapi` cho IDF = 0 với mọi từ khi corpus chỉ có 2 tài liệu, khiến filter `score > 0` xoá sạch kết quả. Xử lý: chỉ lọc khi thực sự có chunk ghi điểm dương, và dùng stable sort để thứ tự không đảo khi score bằng nhau.
  - Console Windows (cp1252) không encode được tiếng Việt, mọi script `python -m src.taskN` đều chết với `UnicodeEncodeError`. Xử lý: ép `sys.stdout` sang UTF-8 trong `src/__init__.py`.
  - Hai câu có faithfulness 0.667 nhưng đọc kỹ thì **câu trả lời đúng và có citation đầy đủ**. Nguyên nhân là Ragas tách answer thành từng statement, nên "Có." đứng riêng thành một statement không kiểm chứng được. Đây là lỗi đo chứ không phải lỗi hệ thống — đã ghi vào `group_project/evaluation/analysis.md`.

## Điều còn hạn chế

- Corpus 10 tài liệu / 88 chunk vẫn là nhỏ so với hệ thống thật, và golden dataset được soạn từ chính corpus đó nên điểm Ragas có thiên lệch lạc quan.
- Golden dataset hiện có 38 câu, phủ 10/10 tài liệu, nhưng vẫn được soạn từ
  chính corpus nên phù hợp để so cấu hình hơn là tuyên bố chất lượng tuyệt đối.
- PageIndex fallback viết xong nhưng chưa kiểm chứng end-to-end vì chưa có `PAGEINDEX_API_KEY`.
- **Nếu có thêm thời gian:** việc đầu tiên tôi làm là chạy PageIndex thật với
  API key hợp lệ và bổ sung integration test cho đường fallback.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Nguyễn Quang Huy
