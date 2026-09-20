"""
Task 5 — Semantic search.

Query được embed bằng chính embed_texts() của Task 4 nên index và query luôn
cùng model, cùng dimension. Chroma trả cosine distance, ta đổi về similarity
để score nằm trong [0, 1] — đây cũng là score mà Task 9 dùng để so với
threshold fallback (RRF score không dùng được cho việc đó).
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if top_k <= 0:
        return []

    query_vector = embed_texts([query])[0]
    response = get_collection().query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    results = []
    for item_id, content, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        results.append(
            {
                "id": item_id,
                "content": content,
                "score": max(0.0, 1.0 - float(distance)),
                "metadata": dict(metadata),
                "retrieval_method": "dense",
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    for result in semantic_search("chính sách trả hàng hoàn tiền", top_k=3):
        print(f"[{result['score']:.3f}] {result['id']} — {result['content'][:80]}...")
