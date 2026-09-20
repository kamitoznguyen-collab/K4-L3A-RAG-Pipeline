# Phân chia việc còn lại

> Brief chi tiết cho từng người nằm trong [`handoff/`](handoff/) — mỗi
> folder một thành viên, kèm bằng chứng cần đọc trước và lệnh chạy.

Pipeline lõi đã chạy được và pass 20/20 test. Phần dưới là **việc còn đọng**,
chia thành 3 gói độc lập để ba thành viên làm song song mà không đụng file của
nhau.

Mỗi gói đều có điểm ăn được (bonus hoặc kéo điểm hạng mục chính lên), và đều
kết thúc bằng một con số đo được — không gói nào chỉ là "đọc code cho biết".

**Cách làm:** tạo nhánh từ `Huy`, làm gói của mình, chạy `pytest -q` (phải giữ
20/20), rồi mở PR vào `main`. Xong thì tự viết báo cáo cá nhân theo template
`group_project/ịndividual/INDIVIDUAL_REPORT.md`, lưu thành
`reports/<MSSV>-<ten-ngan>.md`.

**Tránh đụng nhau:** mỗi người ghi thí nghiệm vào
`group_project/evaluation/experiments/<ten>.md` của riêng mình; `eval_pipeline.py`
tự ghép thành một bảng. `task9` có sẵn hook `expand_query()`, `post_rerank()` và
hằng `CANDIDATE_MULTIPLIER` để ba gói sửa ba chỗ khác nhau.

---

## Gói 1 — Chất lượng retrieval

**Nhánh:** `feat/retrieval-quality` · **File chính:** `src/task4_chunking_indexing.py`, `src/task9_retrieval_pipeline.py`

Đây là khuyến nghị số 1 và 2 trong `group_project/evaluation/analysis.md`, và là
điểm nghẽn lớn nhất hiện tại: 2/15 câu vẫn bị từ chối vì không lấy được chunk
chứa đáp án.

1. **Contextual chunking** — prepend tiêu đề tài liệu vào nội dung từng chunk,
   thay vì để tiêu đề chỉ nằm ở `chunk-0`.
   - Bằng chứng cần đọc trước: câu "điều kiện xét học bổng KKHT của UET" —
     chunk chứa đáp án không lọt top-40 của dense vì nó chỉ liệt kê "Khá trở
     lên", "15 tín chỉ", không có từ khoá chủ đề nào.
   - Lưu ý: thí nghiệm ngược lại (bỏ bớt text mang tiêu đề) đã đo và cho kết quả
     **tệ hơn** 0.218 điểm — xem `experiments/huy.md`. Giả thuyết này vì thế khá chắc.
2. **Nới ứng viên vào RRF** — hiện `retrieve()` chỉ lấy `top_k*2` từ mỗi ranker.
   Thử `top_k*4`, hoặc nâng `top_k` 5 → 7.
   - Bằng chứng: chunk đáp án của câu UET xếp hạng 6 sau khi fuse, trượt
     `top_k=5` đúng một bậc.
   - Cẩn thận: nâng `top_k` kéo thêm chunk nhiễu, Context precision (đang 0.490)
     có thể giảm. Phải báo cả hai chiều.

**Xong khi:** chạy `python -m group_project.evaluation.eval_pipeline`, thêm 2
dòng vào `experiments/khanh.md` với số liệu thật, và số câu bị từ chối giảm xuống dưới
2/15. Nhớ xoá `chroma_db/` rồi re-index trước mỗi lần đo.

---

## Gói 2 — Reranker nâng cao và query expansion (bonus +6)

**Nhánh:** `feat/advanced-rerank` · **File chính:** `src/task7_reranking.py`, thêm module mới

1. **Cross-encoder reranking (+3)** — viết mới `rerank_cross_encoder(query,
   candidates, top_k)` trong `task7` (hiện file chỉ có `rerank_rrf`). Cài bằng Jina API
   (`JINA_API_KEY` đã có chỗ trong `.env.example`) hoặc model local
   `cross-encoder/ms-marco-MiniLM-L-6-v2`.
   - Rubric đòi **có so sánh với RRF**, nên phải chạy A/B ba chiều: dense-only,
     hybrid+RRF, hybrid+RRF+cross-encoder.
2. **HyDE hoặc query expansion (+3)** — sinh một câu trả lời giả bằng LLM rồi
   embed nó thay vì embed câu hỏi, hoặc mở rộng query bằng từ đồng nghĩa.
   - Rubric đòi **A/B chứng minh cải thiện**, không chỉ chạy được là đủ.

**Xong khi:** cả hai tính năng chạy được, `experiments/hai.md` có số liệu A/B cho
từng cái, và output vẫn đúng `SearchResult` contract (`pytest -q` giữ 20/20).

---

## Gói 3 — Evaluation mở rộng, hội thoại và UI (bonus +4)

**Nhánh:** `feat/eval-ui` · **File chính:** `group_project/evaluation/golden_dataset.json`, `app.py`

1. **Mở rộng golden dataset lên 30–40 câu** — khuyến nghị số 3 trong
   `analysis.md`. Hiện 15 câu, phủ 9/10 tài liệu;
   `data/sources/hoc-bong-dinh-thien-ly.md` (dài nhất, 17KB) **chưa có câu nào**.
   - Mỗi case cần đủ `question`, `expected_answer`, `expected_context` (trích
     nguyên văn corpus) và `source_doc_id`.
   - Lý do cần làm: điểm từng câu hiện phân cực (hoặc ~0.85 hoặc đúng 0.000), với
     15 câu thì mỗi câu đổi trạng thái làm average dịch ~0.06 — quá thô để đọc
     chênh lệch nhỏ.
2. **Conversation memory (+2)** — `app.py` hiện gửi mỗi câu hỏi độc lập. Thêm
   xử lý follow-up ("còn học bổng nào khác không?") bằng cách rewrite câu hỏi
   dựa trên lịch sử hội thoại trước khi đưa vào `retrieve()`.
3. **UI citation highlighting (+2)** — panel nguồn đã có title, link URL, score
   và retrieval method. Thêm highlight đoạn text trong chunk mà câu trả lời trích
   dẫn, để người đọc đối chiếu bằng mắt được.

**Xong khi:** `pytest -q` vẫn 20/20 (acceptance test đòi golden dataset ≥15 câu
đủ field), follow-up question trả lời đúng trong demo, và UI highlight chạy được.

---

## Việc Huy giữ

Pipeline lõi Task 1–10, hạ tầng evaluation, và xác minh PageIndex fallback
end-to-end khi có `PAGEINDEX_API_KEY` (hiện `task8` viết xong nhưng chưa chạy
thật lần nào).

---

## Phân công

Phân theo thứ tự trong `TEAMMATES.md`, **không theo năng lực hay nguyện vọng** —
các bạn tự đổi gói cho nhau thoải mái, chỉ cần cập nhật lại `TEAMMATES.md` và
`WORK_SPLIT.md` cho khớp trước khi nộp.

| Thành viên | Gói |
|---|---|
| Nguyễn Thị Minh Khánh | Gói 1 — Chất lượng retrieval |
| Nguyễn Việt Hoàng Hải | Gói 2 — Reranker nâng cao và query expansion |
| Phạm Minh Hiếu | Gói 3 — Evaluation mở rộng, hội thoại và UI |
| Nguyễn Quang Huy | Pipeline lõi + hạ tầng evaluation |
