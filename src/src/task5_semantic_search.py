"""
Task 5 — Semantic Search Module.
"""

def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Tìm kiếm ngữ nghĩa sử dụng vector similarity qua ChromaDB."""
    from src.task4_chunking_indexing import get_collection, get_embedding_model

    model = get_embedding_model()
    # Embedding trả về matrix numpy, ta cần get mảng 1 chiều
    query_vector = model.encode([query])[0].tolist()

    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    # collection.query trả về list lồng nhau
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        score = max(0.0, 1.0 - dist)  # cosine distance → similarity
        output.append({"content": doc, "score": float(round(score, 4)), "metadata": meta})

    output.sort(key=lambda x: x["score"], reverse=True)
    return output[:top_k]


if __name__ == "__main__":
    # Test
    results = semantic_search("quy định trả hàng hoàn tiền shopee", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
