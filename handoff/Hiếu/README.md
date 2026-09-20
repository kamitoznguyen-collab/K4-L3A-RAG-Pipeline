# Gói 3 — Evaluation mở rộng, hội thoại và UI (bonus +4)

**Người nhận:** Phạm Minh Hiếu — 2A202602919
**Nhánh:** `feat/eval-ui`
**File sẽ sửa:** `group_project/evaluation/golden_dataset.json`, `app.py`

---

## Bối cảnh

Gói này gồm một việc kéo chất lượng đo lường và hai việc ăn bonus:

| Việc | Điểm |
|---|---:|
| Mở rộng golden dataset lên 30–40 câu | Kéo hạng mục "Golden dataset, 4 metrics, A/B và phân tích lỗi" (10đ) |
| Conversation memory cho follow-up question | +2 |
| Deploy online **hoặc** UI citation/source highlighting | +2 |

---

## Việc 1: Mở rộng golden dataset

Hiện có 15 câu trong `group_project/evaluation/golden_dataset.json`, phủ 9/10
tài liệu. **`hoc-bong-dinh-thien-ly.md` chưa có câu nào** — mà nó là tài liệu
dài nhất corpus (17KB, gần bằng 40% tổng số chữ).

**Vì sao cần làm:** điểm từng câu hiện phân cực hoàn toàn — hoặc khoảng 0.85,
hoặc đúng 0.000, không có gì ở giữa (0.000 = pipeline từ chối trả lời vì không
lấy được chunk chứa đáp án). Với 15 câu, mỗi câu đổi trạng thái làm điểm trung
bình dịch khoảng 0.06. Trong khi dao động giữa hai lần chạy chỉ khoảng 0.01.
Nghĩa là dataset đang quá thô: các bạn Khánh và Hải sẽ đo cải tiến của họ trên
chính dataset này, và nếu nó chỉ có 15 câu thì họ không phân biệt được cải thiện
thật với may rủi.

Định dạng mỗi case (xem file hiện có để theo mẫu):

```json
{
  "question": "...",
  "expected_answer": "...",
  "expected_context": "trích nguyên văn đoạn trong corpus",
  "source_doc_id": "hoc-bong-dinh-thien-ly"
}
```

Nguyên tắc soạn:
- `expected_context` phải **trích nguyên văn** từ `data/sources/<doc_id>.md`,
  không diễn đạt lại. Đây là căn cứ để đối chiếu khi phân tích lỗi.
- `source_doc_id` khớp tên file trong `data/sources/` (bỏ đuôi `.md`).
- Phủ đều: mỗi tài liệu nên có ít nhất 3 câu. Ưu tiên câu hỏi về **con số cụ
  thể** (mức tiền, số suất, GPA tối thiểu, hạn nộp) — loại này kiểm chứng được
  rạch ròi, không tranh cãi được.
- Trộn cả câu dễ (đáp án nằm gọn một chunk) và câu khó (đáp án trải hai chunk),
  để dataset phân biệt được cấu hình tốt với cấu hình kém.

Acceptance test đang kiểm `>= 15` case và đủ 3 field bắt buộc — đừng làm hỏng
cấu trúc, `pytest` sẽ đỏ.

---

## Việc 2: Conversation memory (+2)

`app.py` hiện gửi mỗi câu hỏi độc lập: `generate_with_citation(query, top_k)`.
Nên hỏi tiếp *"còn học bổng nào khác không?"* là bot không hiểu "khác" so với
cái gì.

Hướng làm: trước khi gọi `retrieve()`, dùng LLM rewrite câu hỏi thành câu đứng
độc lập dựa trên lịch sử hội thoại.

```
Lịch sử:
  User: Học bổng Sigma Gold trị giá bao nhiêu?
  Bot:  Hỗ trợ 100% học phí và sinh hoạt phí tới 15 triệu/tháng...
  User: Có bao nhiêu suất?
Rewrite thành: "Học bổng Sigma Gold có bao nhiêu suất?"
```

`st.session_state.messages` đã lưu sẵn toàn bộ lịch sử, dùng luôn. Tái sử dụng
`call_llm()` trong `src/task10_generation.py` để không phải viết lại phần dispatch
provider.

Nhớ giữ nguyên chữ ký `generate_with_citation(query, top_k)` — `pytest` kiểm
chữ ký các hàm public.

**Cần demo được:** rubric ghi *"Bonus chỉ được tính khi tính năng chạy được và
có demo hoặc kết quả đo kiểm chứng"*. Chuẩn bị sẵn một chuỗi 3–4 câu follow-up
để chạy trong buổi demo.

---

## Việc 3: UI citation highlighting (+2)

Panel nguồn trong `app.py` hiện đã hiển thị tiêu đề, link URL gốc, tên file,
loại tài liệu, chunk index, score và retrieval method.

Còn thiếu: người đọc chưa đối chiếu được **câu nào trong câu trả lời** ứng với
**đoạn nào trong chunk**. Thêm highlight đoạn text trong chunk mà câu trả lời
trích dẫn.

Gợi ý đơn giản mà hiệu quả: khớp cụm từ chung dài nhất giữa answer và chunk rồi
bôi vàng bằng `st.markdown` với HTML inline. Không cần LLM.

Lựa chọn thay thế cùng điểm: **deploy online** (Streamlit Community Cloud miễn
phí). Nếu chọn hướng này thì nhớ cấu hình secrets cho API key, đừng commit `.env`.

---

## Cách đo

```bash
pytest -q                    # phai giu 20/20
python -m group_project.evaluation.eval_pipeline    # sau khi mo rong dataset
streamlit run app.py         # test follow-up va highlight
```

Sau khi mở rộng dataset lên 30–40 câu, một lần eval sẽ mất khoảng 20–25 phút
(gấp đôi hiện tại). Báo trước cho Khánh và Hải để hai bạn tính thời gian đo.

---

## Xong khi

- [ ] Golden dataset 30–40 câu, phủ cả 10 tài liệu, mỗi tài liệu ≥3 câu
- [ ] Chạy lại eval và cập nhật `RESULT.md` với dataset mới
- [ ] Follow-up question trả lời đúng, có kịch bản demo 3–4 câu
- [ ] UI highlight đoạn trích dẫn (hoặc deploy online)
- [ ] `pytest -q` vẫn 20/20
- [ ] Thêm dòng vào bảng trong `group_project/evaluation/experiments/hieu.md` nếu có
      đo A/B — file này **chỉ của bạn**, không ai khác sửa
      nên không bao giờ conflict
- [ ] Mở PR từ `feat/eval-ui` vào `main`
- [ ] Viết báo cáo cá nhân `reports/2A202602919-hieu.md` theo template
      `group_project/ịndividual/INDIVIDUAL_REPORT.md`

**Phối hợp:** việc mở rộng dataset đổi mẫu số của mọi phép đo, nên số cũ và số
mới không so trực tiếp được. Làm sớm và báo cho Khánh với Hải, hoặc thống nhất
là hai bạn ấy đo trên dataset 15 câu rồi cuối cùng chạy lại một lượt trên
dataset đầy đủ.

---

## Bắt đầu

```bash
git clone https://github.com/kamitoznguyen-collab/K4-L3A-RAG-Pipeline.git
cd K4-L3A-RAG-Pipeline
git checkout Huy && git checkout -b feat/eval-ui

python -m venv .venv && .venv\Scripts\activate    # Windows
python -m pip install -e ".[dev]"
cp .env.example .env        # dien DEEPSEEK_API_KEY

python -m src.task4_chunking_indexing
pytest -q
streamlit run app.py
```

Đọc thêm: [`../../group_project/evaluation/analysis.md`](../../group_project/evaluation/analysis.md),
[`../../group_project/evaluation/golden_dataset.json`](../../group_project/evaluation/golden_dataset.json)
và [`../../data/sources/`](../../data/sources/) (corpus gốc để soạn câu hỏi).
