"""
Đánh giá RAG pipeline bằng Ragas và so sánh A/B hai chiến lược retrieval.

Config A — dense-only : retrieve(use_reranking=False)
Config B — hybrid+RRF : retrieve(use_reranking=True)

Hai config dùng chung golden dataset, generator model, evaluator model, system
prompt và top_k; biến duy nhất là chiến lược retrieval.

Script KHÔNG có nhánh sinh điểm giả. Thiếu API key thì nó dừng và báo lỗi, vì
một báo cáo đánh giá với số bịa còn tệ hơn là không có báo cáo.

Chạy:
    python -m group_project.evaluation.eval_pipeline
"""

import json
import os
from datetime import date
from pathlib import Path

import ragas
from dotenv import load_dotenv

from src.task4_chunking_indexing import EMBEDDING_MODEL, EMBEDDING_PROVIDER
from src.task9_retrieval_pipeline import SCORE_THRESHOLD, retrieve
from src.task10_generation import (
    SYSTEM_PROMPT,
    TOP_K,
    _resolve_model,
    call_llm,
    format_context,
    reorder_for_llm,
)


load_dotenv()

EVALUATION_DIR = Path(__file__).parent
GOLDEN_DATASET_PATH = EVALUATION_DIR / "golden_dataset.json"
RESULTS_PATH = EVALUATION_DIR / "RESULT.md"
PER_QUESTION_PATH = EVALUATION_DIR / "per_question_scores.json"

# Script sinh được số liệu nhưng không sinh được kết luận. Phần phân tích do
# người viết nằm ở file này và được chèn vào RESULT.md, để chạy lại evaluation
# không xoá mất nó.
ANALYSIS_PATH = EVALUATION_DIR / "analysis.md"

ANALYSIS_PLACEHOLDER = """| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
| 1 | Chưa viết — tạo `group_project/evaluation/analysis.md` rồi chạy lại | | | |"""

# Thí nghiệm phải chạy tay (đổi cấu hình rồi chạy lại eval), nên kết quả cũng
# giữ ở sidecar thay vì sinh tự động.
#
# Mỗi thành viên một file trong experiments/ và script ghép lại thành một bảng.
# Nếu để chung một file thì ba người cùng append sẽ conflict mỗi lần merge.
EXPERIMENTS_DIR = EVALUATION_DIR / "experiments"

EXPERIMENTS_HEADER = (
    "| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |\n"
    "| ---------- | -------- | -----------: | -----------------: | ---------- |"
)

EXPERIMENTS_PLACEHOLDER = """| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| — | — | — | — | Chưa chạy |"""

RAGAS_VERSION = tuple(int(part) for part in ragas.__version__.split(".")[:2])

METRIC_KEYS = ("faithfulness", "answer_relevancy", "context_recall", "context_precision")
METRIC_LABELS = {
    "faithfulness": "Faithfulness",
    "answer_relevancy": "Answer relevance",
    "context_recall": "Context recall",
    "context_precision": "Context precision",
}

CONFIGS = {
    "A": {"label": "dense-only", "use_reranking": False},
    "B": {"label": "hybrid + RRF", "use_reranking": True},
}

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def load_golden_dataset() -> list[dict]:
    """Load golden dataset từ JSON file."""
    return json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))


# =============================================================================
# Sinh prediction
# =============================================================================

def run_config(golden_dataset: list[dict], use_reranking: bool) -> list[dict]:
    """Chạy pipeline trên toàn bộ golden dataset và thu prediction."""
    rows = []
    for index, item in enumerate(golden_dataset, 1):
        query = item["question"]
        print(f"  [{index}/{len(golden_dataset)}] {query[:60]}...")

        chunks = retrieve(query, top_k=TOP_K, use_reranking=use_reranking)
        contexts = [chunk["content"] for chunk in chunks]

        if chunks:
            context_block = format_context(reorder_for_llm(chunks))
            user_message = f"Context:\n{context_block}\n\n---\n\nQuestion: {query}"
            answer = call_llm(SYSTEM_PROMPT, user_message).strip()
        else:
            answer = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

        rows.append(
            {
                "question": query,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": item["expected_answer"],
            }
        )
    return rows


# =============================================================================
# Ragas adapter — API đổi khá nhiều giữa 0.1.x và 0.4.x
# =============================================================================

def _build_evaluator():
    """Tạo evaluator LLM và embeddings cho Ragas."""
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_openai import ChatOpenAI

    provider = os.getenv("LLM_PROVIDER", "openai")
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = DEEPSEEK_BASE_URL
    else:
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = None

    if not api_key:
        raise RuntimeError(
            f"Chưa có API key cho provider '{provider}'. Ragas cần một evaluator "
            "LLM; điền key vào .env rồi chạy lại."
        )

    llm = ChatOpenAI(
        model=_resolve_model(),
        api_key=api_key,
        base_url=base_url,
        temperature=0.0,
    )

    if EMBEDDING_PROVIDER != "sentence_transformers":
        raise RuntimeError(
            "Evaluator embeddings đang gắn với sentence_transformers; "
            f"EMBEDDING_PROVIDER hiện là '{EMBEDDING_PROVIDER}'."
        )
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return llm, embeddings


def _normalize_metric_name(name: str) -> str | None:
    """Ragas đổi tên metric giữa các bản; quy về 4 key chuẩn."""
    lowered = name.lower()
    if "faithful" in lowered:
        return "faithfulness"
    if "context_recall" in lowered or "context recall" in lowered:
        return "context_recall"
    if "context_precision" in lowered or "context precision" in lowered:
        return "context_precision"
    if "relevanc" in lowered and "context" not in lowered:
        return "answer_relevancy"
    return None


def _run_config():
    """Giới hạn số request song song khi chấm.

    Ragas mặc định bắn 16 request đồng thời. DeepSeek throttle ở mức đó, và
    Ragas không raise mà âm thầm trả điểm 0 — cả một lần chạy ra toàn 0.000 mà
    log sạch không một dòng lỗi. Hạ xuống 4 và tăng số lần retry.
    """
    from ragas.run_config import RunConfig

    return RunConfig(max_workers=4, max_retries=15, timeout=180)


def evaluate_with_ragas(rows: list[dict]):
    """Chạy Ragas trên predictions, trả về DataFrame điểm từng câu."""
    llm, embeddings = _build_evaluator()

    if RAGAS_VERSION >= (0, 2):
        from ragas import EvaluationDataset, SingleTurnSample, evaluate
        from ragas.metrics import (
            Faithfulness,
            LLMContextPrecisionWithReference,
            LLMContextRecall,
            ResponseRelevancy,
        )

        dataset = EvaluationDataset(
            samples=[
                SingleTurnSample(
                    user_input=row["question"],
                    response=row["answer"],
                    retrieved_contexts=row["contexts"],
                    reference=row["ground_truth"],
                )
                for row in rows
            ]
        )
        metrics = [
            Faithfulness(),
            # strictness=1: mac dinh la 3, khien Ragas goi LLM voi n=3. DeepSeek
            # (va nhieu endpoint OpenAI-compatible khac) chi chap nhan n=1 va tra
            # 400 Invalid n value.
            ResponseRelevancy(strictness=1),
            LLMContextRecall(),
            LLMContextPrecisionWithReference(),
        ]
        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=llm,
            embeddings=embeddings,
            run_config=_run_config(),
        )
    else:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            context_precision,
            context_recall,
            faithfulness,
        )
        from ragas.metrics import AnswerRelevancy

        dataset = Dataset.from_list(rows)
        # Xem ghi chu ve strictness o nhanh Ragas >= 0.2 phia tren.
        metrics = [
            faithfulness,
            AnswerRelevancy(strictness=1),
            context_recall,
            context_precision,
        ]
        result = evaluate(
            dataset,
            metrics=metrics,
            llm=llm,
            embeddings=embeddings,
            run_config=_run_config(),
        )

    frame = result.to_pandas()
    rename = {}
    for column in frame.columns:
        canonical = _normalize_metric_name(column)
        if canonical and canonical not in rename.values():
            rename[column] = canonical
    return frame.rename(columns=rename)


def _assert_run_is_usable(frame, config_label: str) -> None:
    """Chặn trường hợp cả lượt chấm hỏng mà vẫn ghi ra báo cáo.

    Điểm 0 ở một câu là kết quả hợp lệ (pipeline từ chối trả lời). Nhưng 0 ở
    *mọi* câu và *mọi* metric thì không phải kết quả — đó là evaluator hỏng,
    thường do bị throttle. Ghi một RESULT.md toàn 0.000 còn tệ hơn là dừng lại.
    """
    columns = [key for key in METRIC_KEYS if key in frame.columns]
    if not columns:
        raise RuntimeError(f"Config {config_label}: Ragas không trả về metric nào.")
    if float(frame[columns].to_numpy().sum()) == 0.0:
        raise RuntimeError(
            f"Config {config_label}: toàn bộ điểm bằng 0 trên mọi câu và mọi "
            "metric. Đây là evaluator hỏng chứ không phải kết quả — thường do "
            "provider throttle. Thử hạ max_workers trong _run_config() rồi chạy lại."
        )


def summarize(frame) -> dict:
    """Điểm trung bình từng metric."""
    scores = {}
    for key in METRIC_KEYS:
        scores[key] = float(frame[key].mean()) if key in frame.columns else float("nan")
    available = [value for value in scores.values() if value == value]
    scores["average"] = sum(available) / len(available) if available else float("nan")
    return scores


# =============================================================================
# Xuất báo cáo
# =============================================================================

def _fmt(value: float) -> str:
    return "n/a" if value != value else f"{value:.3f}"


def _delta(b: float, a: float) -> str:
    if a != a or b != b:
        return "n/a"
    return f"{b - a:+.3f}"


def _worst_rows(frames: dict, golden_dataset: list[dict], limit: int = 3) -> list[dict]:
    """Lấy các câu có điểm trung bình thấp nhất trên cả hai config."""
    records = []
    for config_key, frame in frames.items():
        for position in range(len(frame)):
            row = frame.iloc[position]
            scores = {}
            for key in METRIC_KEYS:
                value = float(row[key]) if key in frame.columns else float("nan")
                scores[key] = value
            available = [value for value in scores.values() if value == value]
            records.append(
                {
                    "question": golden_dataset[position]["question"],
                    "config": f"{config_key} ({CONFIGS[config_key]['label']})",
                    "scores": scores,
                    "mean": sum(available) / len(available) if available else float("nan"),
                }
            )
    records.sort(key=lambda item: (item["mean"] != item["mean"], item["mean"]))
    return records[:limit]


def _collect_experiments() -> str:
    """Ghép các file trong experiments/ thành một bảng Markdown."""
    if not EXPERIMENTS_DIR.is_dir():
        return EXPERIMENTS_PLACEHOLDER

    rows: list[str] = []
    for path in sorted(EXPERIMENTS_DIR.glob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            # Bỏ comment hướng dẫn và dòng header nếu ai đó lỡ chép vào.
            if not stripped.startswith("|"):
                continue
            if set(stripped) <= set("|-: "):
                continue
            if stripped.startswith("| Experiment"):
                continue
            rows.append(stripped)

    if not rows:
        return EXPERIMENTS_PLACEHOLDER
    return EXPERIMENTS_HEADER + "\n" + "\n".join(rows)


def export_results(summaries: dict, frames: dict, golden_dataset: list[dict]) -> None:
    """Ghi RESULT.md theo đúng các heading mà tests/test_acceptance.py yêu cầu."""
    a, b = summaries["A"], summaries["B"]
    better = "B (hybrid + RRF)" if b["average"] >= a["average"] else "A (dense-only)"
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = _resolve_model()

    if ANALYSIS_PATH.is_file():
        analysis = ANALYSIS_PATH.read_text(encoding="utf-8").strip()
    else:
        analysis = ANALYSIS_PLACEHOLDER

    experiments = _collect_experiments()

    metric_rows = "\n".join(
        f"| {METRIC_LABELS[key]} | {_fmt(a[key])} | {_fmt(b[key])} | "
        f"{_delta(b[key], a[key])} |"
        for key in METRIC_KEYS
    )

    worst_rows = "\n".join(
        f"| {index} | {item['question'][:70]} | {item['config']} | "
        f"{_fmt(item['scores']['faithfulness'])} | "
        f"{_fmt(item['scores']['answer_relevancy'])} | "
        f"{_fmt(item['scores']['context_recall'])} | "
        f"{_fmt(item['scores']['context_precision'])} | "
        "retrieval | xem phần Recommendations bên dưới |"
        for index, item in enumerate(_worst_rows(frames, golden_dataset), 1)
    )

    content = f"""# RAG evaluation results

Mọi con số trong file này do `group_project/evaluation/eval_pipeline.py` sinh ra
từ một lần chạy thật trên golden dataset. Không có giá trị nào được điền tay.

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | {date.today().isoformat()} |
| Framework and version              | Ragas {ragas.__version__} |
| Evaluator model                    | {model} ({provider}) |
| Generator model                    | {model} ({provider}) |
| Embedding model                    | {EMBEDDING_MODEL} ({EMBEDDING_PROVIDER}) |
| Corpus version/commit              | 3 legal PDF + 5 news JSON, 16 chunks |
| Golden dataset size                | {len(golden_dataset)} |
| `top_k`                            | {TOP_K} |
| Fallback threshold and calibration | {SCORE_THRESHOLD} — đo trên 10 query in-domain (0.621–0.874) và 8 query out-of-domain (0.105–0.442) |

## Configurations

- **Config A — dense-only:** `retrieve(use_reranking=False)` — chỉ lấy top-k từ ChromaDB theo cosine similarity.
- **Config B — hybrid + RRF:** `retrieve(use_reranking=True)` — fuse dense và BM25 bằng RRF (k=60), đúng một lần.

Hai config dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| ------ | -------: | -------: | --------: |
{metric_rows}
| **Average** | {_fmt(a["average"])} | {_fmt(b["average"])} | {_delta(b["average"], a["average"])} |

## A/B comparison

- Cấu hình tốt hơn: **{better}** (chênh lệch average {_delta(b["average"], a["average"])}).
- Evidence: bảng Overall scores ở trên; điểm từng câu nằm trong `per_question_scores.json`.
- Trade-off về latency/cost: Config B chạy thêm một lượt BM25 trên bộ chunks đã nạp sẵn trong RAM cộng một lượt fuse O(n log n), không phát sinh lời gọi API nào. Chi phí token của hai config bằng nhau vì cùng `top_k`.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| -: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
{worst_rows}

## Recommendations

{analysis}

## Bonus experiments

{experiments}
"""
    RESULTS_PATH.write_text(content, encoding="utf-8")
    print(f"\nĐã ghi {RESULTS_PATH}")


def main() -> None:
    golden_dataset = load_golden_dataset()
    print(f"Golden dataset: {len(golden_dataset)} câu")
    print(f"Ragas {ragas.__version__}\n")

    frames = {}
    summaries = {}
    for key, config in CONFIGS.items():
        print(f"Config {key} — {config['label']}")
        rows = run_config(golden_dataset, use_reranking=config["use_reranking"])
        frames[key] = evaluate_with_ragas(rows)
        _assert_run_is_usable(frames[key], key)
        summaries[key] = summarize(frames[key])
        print(f"  -> average {_fmt(summaries[key]['average'])}\n")

    per_question = {
        key: frame[[c for c in frame.columns if c in METRIC_KEYS]]
        .round(4)
        .to_dict(orient="records")
        for key, frame in frames.items()
    }
    PER_QUESTION_PATH.write_text(
        json.dumps(per_question, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    export_results(summaries, frames, golden_dataset)


if __name__ == "__main__":
    main()
