# Gói 1 — Chất lượng retrieval

**Người nhận:** Nguyễn Thị Minh Khánh — 2A202602546
**Nhánh:** `feat/retrieval-quality`
**File sẽ sửa:** `src/task4_chunking_indexing.py`, `src/task9_retrieval_pipeline.py`

---

## Bối cảnh: vấn đề bạn đang giải

Pipeline hiện chạy được, nhưng điểm từng câu trong evaluation **phân cực hoàn
toàn** — hoặc khoảng 0.85, hoặc đúng 0.000, không có giá trị trung gian.

Mọi ca 0.000 đều là **safe refusal**: pipeline không lấy được chunk chứa đáp án
nên trả lời "Tôi không thể xác minh thông tin này từ nguồn hiện có" thay vì bịa.
Tức đây là lỗi **recall của retrieval**, không phải lỗi của LLM.

| | Config A (dense-only) | Config B (hybrid + RRF) |
|---|---:|---:|
| Số câu bị từ chối | 6/15 | **2/15** |
| Context recall | 0.600 | 0.867 |
| Context precision | 0.372 | 0.490 |
| Average | 0.524 | 0.745 |

Việc của bạn là kéo con số 2/15 kia xuống.

---

## Bằng chứng: đọc kỹ ca này trước khi code

Câu hỏi: *"Sinh viên chương trình chuẩn của UET cần đạt điều kiện gì để được xét
học bổng khuyến khích học tập?"*

Đáp án nằm ở `legal/hoc-bong-uet-2025-2026.md::chunk-1`. Đo thực tế:

| Ranker | Thứ hạng của chunk chứa đáp án |
|---|---|
| Dense (semantic) | **không lọt top-40** |
| BM25 (lexical) | hạng 3 |
| Sau khi RRF fuse | hạng 6 — trượt `top_k=5` đúng một bậc |

Hai nguyên nhân tách bạch:

1. **Dense mù chunk đó.** Nội dung chunk-1 chỉ là danh sách điều kiện: "Kết quả
   học tập đạt loại Khá trở lên", "15 tín chỉ"… Không có từ "UET", không có
   "học bổng khuyến khích học tập". Tên tài liệu chỉ xuất hiện ở `chunk-0`, nên
   embedding của chunk-1 không nối được với câu hỏi.

2. **RRF ưu tiên chunk xuất hiện ở cả hai danh sách.** Chunk-1 chỉ có mặt bên
   BM25 nên chỉ được `1/(60+3) = 0.0159`, thua những chunk kém liên quan hơn
   nhưng góp mặt ở cả hai bên.

Tái hiện lại bằng lệnh này:

```bash
python -c "
from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search
q='Sinh viên chương trình chuẩn của UET cần đạt điều kiện gì để được xét học bổng khuyến khích học tập?'
target='legal/hoc-bong-uet-2025-2026.md::chunk-1'
for name, fn in (('dense', semantic_search), ('bm25', lexical_search)):
    res = fn(q, top_k=40)
    rank = next((i for i,r in enumerate(res,1) if r['id']==target), None)
    print(name, '-> hang', rank)
"
```

---

## Việc 1: Contextual chunking

Prepend tiêu đề tài liệu vào nội dung **từng chunk**, thay vì để tiêu đề chỉ nằm
ở `chunk-0`. Sửa trong `chunk_documents()` của `src/task4_chunking_indexing.py`.

Đại ý:

```python
title = document["metadata"]["title"]
content = f"{title}\n\n{text}"   # thay vì chỉ text
```

Cân nhắc khi làm:
- `chunk_size = 500`, thêm tiêu đề vào sẽ ăn mất một phần ngân sách ký tự. Thử
  cả hai cách: thêm tiêu đề vào phần đem đi **embed** nhưng giữ `content` gốc để
  đưa vào LLM, so với thêm vào cả hai. Cách một sạch hơn nhưng phải sửa cả
  `embed_chunks()`.
- Contract test kiểm `len(chunk["content"]) <= CHUNK_SIZE * 1.1` (= 550). Nếu
  bạn nhét tiêu đề vào `content` thì phải giảm `chunk_size` tương ứng, không thì
  `pytest` sẽ đỏ.

**Có một manh mối mạnh ủng hộ hướng này:** thí nghiệm ngược đã được chạy và ghi
trong `group_project/evaluation/experiments/huy.md` — khi **bỏ bớt** phần text mang
tiêu đề ra khỏi chunk, điểm Config B tụt từ 0.745 xuống 0.527 (−0.218). Tức là
text mang tiêu đề đang giúp retrieval; thêm vào nhiều hơn nhiều khả năng giúp
tiếp.

---

## Việc 2: Nới số ứng viên đưa vào RRF

Trong `src/task9_retrieval_pipeline.py`, hàm `retrieve()` hiện lấy `top_k * 2`
ứng viên từ mỗi ranker rồi mới fuse. Thử:

- `top_k * 4` ứng viên (giữ `top_k = 5` ở đầu ra), hoặc
- nâng `DEFAULT_TOP_K` từ 5 lên 7.

**Phải báo cả hai chiều:** nâng `top_k` kéo thêm chunk nhiễu vào context, nên
Context precision (đang 0.490) nhiều khả năng giảm trong khi recall tăng. Kết
luận phải nói rõ đánh đổi, đừng chỉ khoe cái tăng.

Đừng sửa chữ ký hàm — `pytest` kiểm `retrieve` phải có đúng tham số
`query, top_k, score_threshold, use_reranking`.

---

## Cách đo

```bash
# Moi lan doi chunking: phai xoa index cu roi dung lai
rm -rf chroma_db
python -m src.task4_chunking_indexing

pytest -q                    # phai giu 20/20
python -m group_project.evaluation.eval_pipeline
```

Một lần eval mất khoảng 10–12 phút (15 câu × 2 config, gọi DeepSeek).

**Lưu ý về độ tin cậy:** dao động giữa hai lần chạy đã được đo là **khoảng
0.01**. Nên chênh lệch dưới 0.05 thì đừng kết luận gì; trên 0.05 mới đọc được.

---

## Xong khi

- [ ] Số câu bị từ chối của Config B giảm xuống dưới 2/15 (đếm số điểm `0.000`
      trong `group_project/evaluation/per_question_scores.json`)
- [ ] `pytest -q` vẫn 20/20
- [ ] Thêm **2 dòng** vào bảng trong `group_project/evaluation/experiments/khanh.md`,
      mỗi việc một dòng, với số liệu thật. File này **chỉ của bạn**, không ai
      khác sửa nên không bao giờ conflict
- [ ] Mở PR từ `feat/retrieval-quality` vào `main`
- [ ] Viết báo cáo cá nhân `reports/2A202602546-khanh.md` theo template
      `group_project/ịndividual/INDIVIDUAL_REPORT.md`

Template yêu cầu chỉ kê khai việc đối chiếu được bằng file/commit/test/kết quả
evaluation — nên viết sau khi đã push và có số đo.

---

## Bắt đầu

```bash
git clone https://github.com/kamitoznguyen-collab/K4-L3A-RAG-Pipeline.git
cd K4-L3A-RAG-Pipeline
git checkout Huy && git checkout -b feat/retrieval-quality

python -m venv .venv && .venv\Scripts\activate    # Windows
python -m pip install -e ".[dev]"
cp .env.example .env        # dien DEEPSEEK_API_KEY

python -m src.task4_chunking_indexing
pytest -q
```

Đọc thêm: [`../../group_project/evaluation/analysis.md`](../../group_project/evaluation/analysis.md)
(khuyến nghị 1 và 2 chính là gói này) và
[`../../group_project/evaluation/RESULT.md`](../../group_project/evaluation/RESULT.md).
