# Day 8 — RAG Pipeline

Chatbot RAG tra cứu **dịch vụ đại học**: điều kiện và mức học bổng, chính sách
hỗ trợ tài chính, học phí và nội quy mượn tài liệu thư viện.

## Nguồn dữ liệu

Corpus gồm **10 tài liệu do nhóm thu thập từ cổng thông tin chính thức** của các
trường đại học và quỹ học bổng. Mỗi tài liệu có `source_url`, `retrieved_at`,
`document_version` và `license_or_permission`, đối chiếu 1-1 trong
[`data/sources/sources.csv`](data/sources/sources.csv).

| Nhóm | Số lượng | Nguồn |
| ---- | -------: | ----- |
| Quy chế, quy định (`data/landing/legal/`) | 5 | PTIT (nội quy thư viện, 2 bản), FPT, UET, TDTU |
| Thông báo học bổng (`data/landing/news/`) | 5 | HUST, VIASM, IU-VNUHCM, LSTF, VJU |

Tổng ~42.000 ký tự, 88 chunk sau khi chunking.

Các cổng thông tin này publish dưới dạng HTML chứ không phát hành PDF, nên Task 1
render các văn bản quy chế ra PDF trong `data/landing/legal/` để pipeline có định
dạng đồng nhất. **Nội dung là nguyên văn nguồn đã thu thập, PDF chỉ là vật chứa
local**; mỗi PDF đều in kèm URL gốc, ngày thu thập và phiên bản ở đầu tài liệu
nên người chấm truy ngược được.

Task 2 đọc lại bản đã thu thập trong `data/sources/` thay vì crawl lại mỗi lần
chạy, vì crawl lại làm kết quả đổi giữa các lần chạy và nhiều trang nguồn đã thay
đổi so với `retrieved_at`. Muốn crawl trực tiếp: `pip install -e ".[crawl]"` rồi
bật lại nhánh Crawl4AI trong `crawl_article()`.

## Sản phẩm phải nộp

- Repository nhóm chạy được.
- Tối thiểu 3 tài liệu chính sách và 5 bài viết/page do nhóm tự thu thập.
- Pipeline: convert → chunk → index → dense + BM25 → RRF → fallback → generation có citation.
- Chatbot Streamlit hiển thị câu trả lời và nguồn đã dùng.
- Golden dataset tối thiểu 15 câu; đánh giá 4 metric và so sánh A/B.
- `group_project/evaluation/RESULT.md`.
- Mỗi thành viên nộp báo cáo cá nhân theo template trong `group_project/ịndividual/INDIVIDUAL_REPORT.md`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
cp .env.example .env
```

Điền API key cần dùng trong `.env`; không commit file này.

> `crawl4ai` đã được chuyển sang extra `[crawl]` vì nó kéo theo toolchain Rust và
> fail khi cài trên khá nhiều máy. Pipeline không cần nó để chạy.

```bash
# 1. Dựng corpus từ nguồn đã thu thập và chuẩn hoá
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown

# 2. Index và kiểm tra contract
python -m src.task4_chunking_indexing
pytest -q

# 3. Chạy sản phẩm
streamlit run app.py

# 4. Đánh giá và xuất RESULT.md
python -m group_project.evaluation.eval_pipeline
```

## Các lựa chọn kỹ thuật

| Hạng mục | Lựa chọn | Lý do |
| -------- | -------- | ----- |
| Chunking | `RecursiveCharacterTextSplitter`, size 500, overlap 50 | 500 ký tự (~100–150 từ) đủ chứa trọn một điều khoản; overlap 50 giữ câu bị cắt ở biên |
| Embedding | `paraphrase-multilingual-MiniLM-L12-v2` (384 chiều, local) | Nhẹ hơn `bge-m3` nhiều lần trên CPU nhưng vẫn hiểu tiếng Việt |
| Vector store | ChromaDB persistent, cosine | Chạy local, không cần dịch vụ ngoài |
| Lexical | BM25Okapi trên cùng bộ chunks | ID khớp với dense nên RRF fuse được theo ID |
| Fusion | RRF `k=60`, fuse đúng một lần | Gộp theo thứ hạng, không cộng thẳng cosine với BM25 |
| Fallback | PageIndex khi cosine dense < `SCORE_THRESHOLD` | Vectorless, tìm theo cây mục lục nên bù được khi dense lạc |
| Generation | DeepSeek `deepseek-chat` | Rẻ, nhanh, tương thích chuẩn OpenAI SDK |

### Vì sao không dùng `all-MiniLM-L6-v2`

Nhóm thử trước bằng `all-MiniLM-L6-v2` (model tiếng Anh) và phải loại. Đo trên
corpus tiếng Việt, nó chấm query **ngoài miền** ngang với query trong miền — tức
là nó chỉ nhận ra "đây là tiếng Việt" chứ không hiểu nội dung, nên không thể đặt
ngưỡng fallback ở đâu cả.

### Hiệu chỉnh `SCORE_THRESHOLD`

Đo cosine của chunk tốt nhất, trên chính corpus này:

| | dải cosine |
| --- | --- |
| 10 query in-domain | 0.621 – 0.874 |
| 8 query out-of-domain | 0.105 – 0.442 |

`SCORE_THRESHOLD = 0.53` nằm giữa, cách mỗi bên khoảng 0.09. Khoảng trống rộng
0.18 này có được là nhờ corpus đủ lớn (88 chunk) và tập trung đúng một miền chủ
đề — một bản corpus nhỏ hơn thử trước đó chỉ tách được 0.024. Đổi corpus hoặc
embedding model thì phải đo lại.

## Lưu ý quy tắc để có code quality tốt:

- Dense và BM25 nên cùng trả về `SearchResult` theo một schema.
- RRF chỉ nên dùng để gộp thứ hạng và chỉ chạy một lần.
- Fallback dùng cosine score gốc của dense retrieval.
- Threshold phải được hiệu chỉnh trên query in domain và out of domain, không có một con số đúng cho mọi corpus.

## Tài liệu

- [Module contracts](docs/MODULE_CONTRACTS.md): schema, interface và invariant mà code/test nên tuân theo.
- [Step-by-step guide](docs/STEP_BY_STEP.md): thứ tự triển khai và tiêu chí hoàn thành từng bước.
- [Grading rubric](docs/GRADING_RUBRIC.md): Rubric thang điểm.
- [Individual report](group_project/ịndividual/INDIVIDUAL_REPORT.md): template báo cáo cá nhân.
- [Suggested topics](docs/SUGGESTED_TOPICS.md): danh sách chủ đề tham khảo, không bắt buộc.
- [Thành viên nhóm](TEAMMATES.md) và [phân chia việc còn lại](WORK_SPLIT.md).

## Kiểm tra

```bash
# Contract tests
pytest tests/test_contracts.py -q

# Acceptance tests
pytest tests/test_acceptance.py -q

# Toàn bộ
pytest -q
```

## Khắc phục sự cố

**`UnicodeEncodeError` khi chạy `python -m src.taskN` trên Windows** — console
Windows mặc định là cp1252, không encode được tiếng Việt. `src/__init__.py` đã ép
`sys.stdout` sang UTF-8 nên trường hợp này đã được xử lý; nếu vẫn gặp ở script
nằm ngoài package `src`, chạy `set PYTHONIOENCODING=utf-8` trước.

**`400 Invalid n value` khi chạy evaluation** — Ragas mặc định gọi metric
`answer_relevancy` với `n=3`, nhưng DeepSeek và nhiều endpoint OpenAI-compatible
khác chỉ nhận `n=1`. `eval_pipeline.py` đã đặt `strictness=1` để tránh lỗi này.

**`FileNotFoundError` về font khi chạy Task 1** — cần một file `.ttf` Unicode để
render tiếng Việt. Thêm đường dẫn font của máy bạn vào `FONT_CANDIDATES` trong
`src/task1_collect_legal_docs.py`.

**Đổi embedding model** — phải xoá `chroma_db/` rồi chạy lại
`python -m src.task4_chunking_indexing`, vì dimension và không gian vector không
tương thích ngược.
