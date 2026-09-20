# Gói 2 — Reranker nâng cao và query expansion (bonus +6)

**Người nhận:** Nguyễn Việt Hoàng Hải — 2A202602967
**Nhánh:** `feat/advanced-rerank`
**File sẽ sửa:** `src/task7_reranking.py`, thêm module mới nếu cần

---

## Bối cảnh

Gói này ăn thẳng vào 6 điểm bonus chưa ai đụng:

| Hạng mục (theo `docs/GRADING_RUBRIC.md`) | Điểm |
|---|---:|
| Reranker nâng cao **có so sánh với RRF** | +3 |
| HyDE hoặc query expansion **có A/B chứng minh cải thiện** | +3 |

Chữ in đậm là phần dễ mất điểm nhất: rubric ghi rõ *"Bonus chỉ được tính khi
tính năng chạy được **và có demo hoặc kết quả đo kiểm chứng**"*. Code chạy được
mà không có bảng A/B thì không được tính.

Baseline hiện tại để so:

| | Config A (dense-only) | Config B (hybrid + RRF) |
|---|---:|---:|
| Faithfulness | 0.544 | 0.779 |
| Answer relevance | 0.581 | 0.843 |
| Context recall | 0.600 | 0.867 |
| Context precision | 0.372 | 0.490 |
| **Average** | 0.524 | **0.745** |

---

## Việc 1: Cross-encoder reranking (+3)

`src/task7_reranking.py` hiện **chỉ có `rerank_rrf()`** — bạn viết hàm mới:

```python
def rerank_cross_encoder(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    ...
```

Rồi gọi nó từ `retrieve()` trong `src/task9_retrieval_pipeline.py`, sau bước RRF.

Hai hướng, chọn một:

- **Jina API** — `.env.example` đã có sẵn dòng `JINA_API_KEY=`. Model
  `jina-reranker-v2-base-multilingual` hiểu tiếng Việt, phù hợp corpus này.
- **Local** — `cross-encoder/ms-marco-MiniLM-L-6-v2` qua `sentence-transformers`
  (đã nằm trong dependencies). Nhẹ nhưng là model tiếng Anh; với corpus tiếng
  Việt có thể kém. Nếu chọn hướng này thì cân nhắc bản multilingual.

**Bắt buộc:** output phải đúng `SearchResult` contract — mỗi item có `id`,
`content`, `score`, `metadata` (đủ `source`/`title`/`doc_type`/`url`/`chunk_index`)
và `retrieval_method`. Danh sách phải sort giảm dần theo score, ID không trùng,
không vượt `top_k`. Xem `src/contracts.py`; `pytest -q` sẽ bắt nếu sai.

**A/B phải ba chiều**, vì rubric đòi so với RRF:

| Config | Mô tả |
|---|---|
| A | dense-only |
| B | hybrid + RRF (baseline hiện tại) |
| C | hybrid + RRF + cross-encoder rerank |

Cách làm: thêm một entry vào dict `CONFIGS` trong
`group_project/evaluation/eval_pipeline.py`, hoặc chạy eval hai lần rồi ghép số.
Nhớ giữ nguyên golden dataset, generator, evaluator, prompt và `top_k` — chỉ đổi
chiến lược retrieval.

Cũng nên đo **latency**: cross-encoder chấm lại từng cặp (query, chunk) nên chậm
hơn RRF rõ rệt. Bảng thí nghiệm có cột "Latency/cost delta" để ghi.

---

## Việc 2: HyDE hoặc query expansion (+3)

Chọn một:

- **HyDE** (Hypothetical Document Embeddings) — cho LLM sinh một câu trả lời
  *giả định* cho câu hỏi, rồi embed câu trả lời đó thay vì embed câu hỏi. Ý
  tưởng: câu trả lời giả có văn phong giống tài liệu hơn là câu hỏi, nên gần
  chunk đúng hơn trong không gian vector.
- **Query expansion** — mở rộng câu hỏi bằng từ đồng nghĩa / thuật ngữ liên quan
  trước khi search.

**Vì sao hướng này hợp với corpus này:** có một ca đã phân tích sẵn cho thấy
dense đang yếu đúng ở chỗ HyDE giải quyết. Với câu *"điều kiện xét học bổng KKHT
của UET"*, chunk chứa đáp án **không lọt top-40 của dense** vì nội dung chunk chỉ
là danh sách điều kiện ("Kết quả học tập đạt loại Khá trở lên", "15 tín chỉ") —
không mang từ khoá chủ đề nào. Một câu trả lời giả định sinh bởi LLM sẽ chứa
đúng những cụm như "Khá trở lên", "rèn luyện", "tín chỉ", nên nhiều khả năng
kéo được chunk đó lên.

Chi tiết ca này ở `group_project/evaluation/analysis.md`, khuyến nghị số 1.

**Lưu ý chi phí:** HyDE thêm một lời gọi LLM cho *mỗi* query. Phải ghi vào cột
"Latency/cost delta" — đây là đánh đổi thật, không phải chi tiết phụ.

---

## Cách đo

```bash
pytest -q                    # phai giu 20/20
python -m group_project.evaluation.eval_pipeline
```

Một lần eval mất khoảng 10–12 phút mỗi config.

**Lưu ý về độ tin cậy:** dao động giữa hai lần chạy đã được đo là **khoảng
0.01**, ghi trong `group_project/evaluation/experiments/huy.md`. Chênh lệch dưới 0.05
thì đừng kết luận là cải thiện.

---

## Xong khi

- [ ] `rerank_cross_encoder()` chạy được, output đúng `SearchResult` contract
- [ ] Có bảng A/B ba chiều (dense / hybrid+RRF / hybrid+RRF+cross-encoder)
- [ ] HyDE hoặc query expansion chạy được, có A/B riêng
- [ ] `pytest -q` vẫn 20/20
- [ ] Thêm **2 dòng** vào bảng trong `group_project/evaluation/experiments/hai.md`,
      kèm cả cột latency — file này **chỉ của bạn**, không ai
      khác sửa nên không bao giờ conflict
- [ ] Mở PR từ `feat/advanced-rerank` vào `main`
- [ ] Viết báo cáo cá nhân `reports/2A202602967-hai.md` theo template
      `group_project/ịndividual/INDIVIDUAL_REPORT.md`

Nếu đo ra cross-encoder **không** tốt hơn RRF thì vẫn ghi đúng như vậy — một
thí nghiệm bác bỏ giả thuyết mà có số liệu vẫn được tính điểm phân tích, và
`group_project/evaluation/experiments/huy.md` đã có sẵn một ví dụ như thế để
bạn tham khảo cách trình bày.

---

## Bắt đầu

```bash
git clone https://github.com/kamitoznguyen-collab/K4-L3A-RAG-Pipeline.git
cd K4-L3A-RAG-Pipeline
git checkout Huy && git checkout -b feat/advanced-rerank

python -m venv .venv && .venv\Scripts\activate    # Windows
python -m pip install -e ".[dev]"
cp .env.example .env        # dien DEEPSEEK_API_KEY, va JINA_API_KEY neu dung Jina

python -m src.task4_chunking_indexing
pytest -q
```

Đọc thêm: [`../../src/contracts.py`](../../src/contracts.py) (schema bắt buộc),
[`../../docs/MODULE_CONTRACTS.md`](../../docs/MODULE_CONTRACTS.md) và
[`../../group_project/evaluation/RESULT.md`](../../group_project/evaluation/RESULT.md).
