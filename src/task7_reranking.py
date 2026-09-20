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
