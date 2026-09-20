# Bàn giao việc

Mỗi folder là brief của một thành viên: bối cảnh, bằng chứng cần đọc trước, việc
phải làm, cách đo và tiêu chí hoàn thành.

| Folder | Người nhận | Nhánh | File sẽ sửa |
|---|---|---|---|
| [`Khánh/`](Kh%C3%A1nh/README.md) | Nguyễn Thị Minh Khánh — 2A202602546 | `feat/retrieval-quality` | `src/task4_chunking_indexing.py`, `src/task9_retrieval_pipeline.py` |
| [`Hải/`](H%E1%BA%A3i/README.md) | Nguyễn Việt Hoàng Hải — 2A202602967 | `feat/advanced-rerank` | `src/task7_reranking.py` |
| [`Hiếu/`](Hi%E1%BA%BFu/README.md) | Phạm Minh Hiếu — 2A202602919 | `feat/eval-ui` | `group_project/evaluation/golden_dataset.json`, `app.py` |

## Làm ở đâu

Sửa **file thật** trong `src/`, `app.py`, `group_project/` — không sửa bản sao
trong folder này. Folder này chỉ chứa brief.

Lý do: chỉ có file thật mới được `pytest` kiểm và được
`group_project/evaluation/eval_pipeline.py` chạy. Sửa một bản sao thì không đo
được kết quả của chính mình, và cuối cùng phải merge tay ba bản đã phân kỳ.

Tiến trình riêng của từng người được ghi nhận bằng **nhánh git** — ba nhánh đã
tạo sẵn trên remote, mỗi người checkout nhánh của mình rồi commit lên đó:

```bash
git clone https://github.com/kamitoznguyen-collab/K4-L3A-RAG-Pipeline.git
cd K4-L3A-RAG-Pipeline
git checkout feat/retrieval-quality     # hoac feat/advanced-rerank / feat/eval-ui
```

Commit trên nhánh của bạn mang tên bạn, nên `git log` chính là bằng chứng đóng
góp đối chiếu được — đúng thứ mà template báo cáo cá nhân yêu cầu.

## File dùng chung

Không còn file dùng chung nào phải tranh nhau sửa:

- `group_project/evaluation/experiments/<ten>.md` — mỗi người một file, script
  `eval_pipeline.py` tự ghép lại thành một bảng trong `RESULT.md`.
- `group_project/evaluation/per_question_scores.json` đã được gitignore vì nó
  sinh lại mỗi lần chạy eval.
- `RESULT.md` vẫn commit (acceptance test đọc nó), nhưng **chỉ regenerate trên
  `main` sau khi merge** — đừng commit nó từ nhánh feature.
- `src/task9_retrieval_pipeline.py` có sẵn hai hook `expand_query()` và
  `post_rerank()` cùng hằng `CANDIDATE_MULTIPLIER`, nên ba gói sửa ba chỗ khác
  nhau trong cùng file mà không chồng dòng.

## Xong thì

1. `pytest -q` phải giữ 20/20
2. Mở PR từ nhánh của mình vào `main`
3. Viết báo cáo cá nhân `reports/<MSSV>-<ten-ngan>.md` theo template
   [`group_project/ịndividual/INDIVIDUAL_REPORT.md`](../group_project/%E1%BB%8Bndividual/INDIVIDUAL_REPORT.md)

Template yêu cầu *"chỉ kê khai công việc có thể đối chiếu bằng file, commit,
pull request, test hoặc kết quả evaluation"*, nên viết báo cáo sau khi đã push
và có số đo.
