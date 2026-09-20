"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng theo THỨ HẠNG chứ không cộng thẳng cosine score với
BM25 score — hai thang đo đó không cùng đơn vị. Công thức:

    RRF(d) = sum(1 / (k + rank)),  rank bắt đầu từ 1

Fuse theo `id`, không theo `content`: chunk_overlap làm nhiều chunk khác nhau
có đoạn text trùng nhau, gộp theo content sẽ nuốt mất kết quả hợp lệ.

RRF score chỉ phản ánh thứ hạng nên Task 9 không được dùng nó để quyết định
fallback.
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1 / (k + rank)
            items.setdefault(item_id, item)

    ranked_ids = sorted(scores, key=lambda item_id: scores[item_id], reverse=True)

    results = []
    for item_id in ranked_ids[: max(top_k, 0)]:
        result = dict(items[item_id])
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)
    return results


if __name__ == "__main__":
    print("Implement xong; chạy `pytest tests/test_contracts.py -q` để kiểm tra.")


# =============================================================================
# Cross-encoder reranking
# =============================================================================
#
# RRF chỉ nhìn thứ hạng, không nhìn nội dung: nó không biết chunk nào thực sự
# trả lời được câu hỏi. Cross-encoder đọc cả cặp (query, chunk) cùng lúc nên
# chấm được độ liên quan thật, đổi lại phải chạy một lượt model cho mỗi cặp.
#
# Đặt sau RRF chứ không thay RRF: RRF thu hẹp từ ~20 ứng viên xuống top_k,
# cross-encoder chỉ chấm lại số ít đó nên chi phí kiểm soát được.

import os

CROSS_ENCODER_MODEL = os.getenv(
    "CROSS_ENCODER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
)

_CROSS_ENCODER = None


def _get_cross_encoder():
    """Load cross-encoder một lần rồi tái sử dụng."""
    global _CROSS_ENCODER
    if _CROSS_ENCODER is None:
        from sentence_transformers import CrossEncoder

        _CROSS_ENCODER = CrossEncoder(CROSS_ENCODER_MODEL)
    return _CROSS_ENCODER


def rerank_cross_encoder(
    query: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    """Chấm lại candidates bằng cross-encoder và sort theo điểm mới.

    Giữ nguyên `retrieval_method` của từng item: cross-encoder chỉ đổi thứ tự,
    không đổi việc chunk đó đến từ đường retrieval nào.
    """
    if not candidates or top_k <= 0:
        return []

    model = _get_cross_encoder()
    pairs = [(query, item["content"]) for item in candidates]
    scores = model.predict(pairs)

    reranked = []
    for item, score in zip(candidates, scores):
        result = dict(item)
        result["score"] = float(score)
        reranked.append(result)

    reranked.sort(key=lambda item: item["score"], reverse=True)
    return reranked[:top_k]
