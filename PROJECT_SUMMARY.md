# Tổng kết dự án: K4-L3A-RAG-Pipeline

Chatbot RAG tra cứu dịch vụ đại học — học bổng, hỗ trợ tài chính, học phí và nội
quy thư viện. File này ghi lại những gì đã làm và **những gì chưa làm**, để người
đọc không phải suy đoán.

Số liệu đánh giá không nằm ở đây — chúng nằm trong
[`group_project/evaluation/RESULT.md`](group_project/evaluation/RESULT.md), do
`eval_pipeline.py` sinh ra từ lần chạy thật.

## 1. Dữ liệu (Task 1, 2, 3)

- **10 tài liệu thu thập từ nguồn công khai**: cổng thông tin PTIT, FPT, UET,
  TDTU, HUST, VIASM, IU-VNUHCM, LSTF, VJU. Danh mục nguồn đầy đủ với `source_url`,
  `retrieved_at`, `document_version` và `license_or_permission` nằm trong
  `data/sources/sources.csv`.
- Chia 5 văn bản quy chế (Task 1, render ra PDF) và 5 thông báo học bổng (Task 2,
  ghi ra JSON). Các trang nguồn publish dạng HTML chứ không phát hành PDF, nên
  PDF là vật chứa local; nội dung nguyên văn, mỗi PDF in kèm URL gốc ở đầu tài
  liệu để truy ngược được.
- Task 3 convert PDF bằng `markitdown`, JSON render thủ công kèm metadata header.
  MarkItDown trích text từ PDF chèn khoảng trắng đôi giữa các từ nên có bước gom
  lại một space trước khi ghi.

## 2. Chunking & Indexing (Task 4)

- `RecursiveCharacterTextSplitter`, `chunk_size=500`, `chunk_overlap=50` → 88 chunks.
- Embedding: **`paraphrase-multilingual-MiniLM-L12-v2`** (384 chiều, chạy local).
- Đã thử `all-MiniLM-L6-v2` trước và **phải loại**: model tiếng Anh chấm query
  ngoài miền bằng tiếng Việt ngang với query trong miền, khiến không thể đặt
  ngưỡng fallback. Chi tiết trong README.
- Lưu vào ChromaDB persistent, cosine distance. ID chunk sinh từ đường dẫn tương
  đối (`legal/hoc-bong-uet-2025-2026.md::chunk-0`) nên chạy lại pipeline là upsert
  đè, không sinh bản trùng.

## 3. Retrieval (Task 5, 6, 7, 8)

- **Semantic (Task 5):** query đi qua đúng `embed_texts()` của Task 4 nên index
  và query luôn cùng model, cùng dimension.
- **Lexical (Task 6):** BM25Okapi trên cùng bộ chunks, nên ID khớp với dense.
- **RRF (Task 7):** fuse theo `id`, không theo `content` — `chunk_overlap` làm
  nhiều chunk có đoạn text trùng nhau, fuse theo content sẽ nuốt mất kết quả.
- **Fallback (Task 8):** gọi PageIndex API thật, có timeout và cache doc ID.
  **Chưa chạy được end-to-end** vì nhóm chưa có `PAGEINDEX_API_KEY`. Khi thiếu
  key hoặc khi provider lỗi, hàm trả về danh sách rỗng và Task 9 quay lại dùng
  hybrid result — không có nhánh nào sinh nội dung giả.

## 4. Pipeline & Generation (Task 9, 10)

- `retrieve()`: dense + BM25 → RRF một lần → so ngưỡng với **cosine score gốc
  của dense**, không so với RRF score (hai thang đo khác nhau).
- `SCORE_THRESHOLD = 0.53`, hiệu chỉnh bằng 10 query in-domain (0.621–0.874) và
  8 query out-of-domain (0.105–0.442). Khoảng trống rộng 0.18.
- **Generation (Task 10):** DeepSeek `deepseek-chat`. Có lost-in-the-middle
  reordering, context kèm title + source để citation `[Document N]` đối chiếu
  được, và safe refusal khi không retrieve được gì hoặc provider lỗi.

## 5. UI và đánh giá

- **Streamlit (`app.py`):** hiển thị câu trả lời kèm panel nguồn — tiêu đề, link
  URL gốc, tên file, loại tài liệu, chunk index, score và retrieval method.
- **Evaluation:** golden dataset 38 cặp Q&A bám nguyên văn corpus, phủ 10/10 tài
  liệu; mỗi case kèm đoạn văn gốc trong `expected_context` và `source_doc_id`.
  Đo 4 metric Ragas và so sánh A/B giữa dense-only và hybrid + RRF.
- Kết quả tích hợp cuối: Config A đạt **0.676**, Config B đạt **0.803**; hybrid
  + RRF hơn dense-only **+0.126** điểm trung bình. Config B có 4/38 câu bị từ
  chối an toàn do không lấy được đủ ngữ cảnh.
- `eval_pipeline.py` hỗ trợ cả Ragas 0.1.x và 0.4.x, và **không có nhánh sinh
  điểm giả**: thiếu API key thì script dừng và báo lỗi; nếu toàn bộ phép chấm
  đồng loạt trả 0 do provider throttle, guard sẽ dừng thay vì ghi đè một báo cáo
  0.000. Phần phân tích và thí nghiệm giữ ở `analysis.md` / `experiments/` nên
  chạy lại eval không xoá mất.

Ba gói cải tiến đã được hợp nhất trên nhánh `integration`:

- Contextual chunking: thêm tiêu đề vào text đem embed nhưng giữ nguyên content.
- Cross-encoder reranking và HyDE: bật/tắt độc lập bằng biến môi trường để A/B.
- Dataset 38 câu, conversation memory và citation highlighting trên Streamlit.

## 6. Kiểm thử

`pytest -q` → 20/20 pass (15 contract tests + 5 acceptance tests), chạy trên
Python 3.12, không gọi network.

## 7. Những chỗ còn hạn chế

- Một số câu vẫn nhận 0.000 do safe refusal khi retrieval không lấy được chunk
  chứa đáp án. Đây là điểm nghẽn retrieval, không phải hallucination của bước
  generation.
- Corpus 10 tài liệu / 88 chunk vẫn nhỏ, và golden dataset soạn từ chính corpus
  đó nên điểm có thiên lệch lạc quan. Bộ 38 câu hiện phủ đủ 10/10 tài liệu nhưng
  chưa thay thế được đánh giá trên dữ liệu độc lập.
- Hybrid không thắng tuyệt đối: câu về học bổng JAIF của VJU bị RRF làm tệ đi so
  với dense-only.
- PageIndex fallback chưa được kiểm chứng end-to-end (thiếu API key).
- Cross-encoder tăng chất lượng nhưng tăng latency khoảng 15 lần; HyDE tăng chi
  phí khoảng 32 lần và thêm một lời gọi LLM mỗi query, nên cả hai mặc định tắt.
- Conversation memory mới được kiểm chứng bằng demo; chưa có golden dataset hội
  thoại nhiều lượt để chấm tự động.
