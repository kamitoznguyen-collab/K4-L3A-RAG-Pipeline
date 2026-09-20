"""
Task 9 — Retrieval Pipeline Hoàn Chỉnh.
"""

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank, rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


# =============================================================================
# CONFIGURATION
# =============================================================================
# 0.3 là một mức tham chiếu tốt khi dùng bge-m3. 
# Nếu query hoàn toàn rác, cosine sẽ tụt dưới 0.3.
SCORE_THRESHOLD = 0.3
DEFAULT_TOP_K = 5
RERANK_METHOD = "rrf"


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Retrieval pipeline hoàn chỉnh với fallback logic."""
    
    # Bước 1: Semantic Search (để lấy điểm cosine gốc)
    try:
        dense_results = semantic_search(query, top_k=top_k * 2)
    except Exception as e:
        print(f"Semantic search error: {e}")
        dense_results = []
        
    best_dense_score = dense_results[0]["score"] if dense_results else 0.0

    # Nếu điểm dense tốt nhất quá thấp, fallback ngay
    if best_dense_score < score_threshold:
        print(f"  ⚠ Semantic best score ({best_dense_score:.3f}) < threshold ({score_threshold})")
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return fallback
        except Exception as e:
            print(f"Fallback error: {e}")
    
    # Bước 2: Lexical search
    try:
        sparse_results = lexical_search(query, top_k=top_k * 2)
    except Exception as e:
        print(f"Lexical search error: {e}")
        sparse_results = []

    # Bước 3: Reranking & Merge
    if use_reranking and (dense_results or sparse_results):
        merged_results = rerank_rrf([dense_results, sparse_results], top_k=top_k)
        for item in merged_results:
            item["source"] = "hybrid"
        return merged_results
    else:
        # Nếu ko reranking, cứ ưu tiên dense
        for item in dense_results:
            item["source"] = "hybrid"
        return dense_results[:top_k]


if __name__ == "__main__":
    test_queries = [
        "What payment methods does Shopee support?",
        "How do I request a return or refund?",
        "What evidence do I need for a refund request?",
        "xyzabc123nonsense",  # Query không có kết quả → test fallback
    ]

    for q in test_queries:
        print(f"\nQuery: {q}")
        print("-" * 60)
        results = retrieve(q, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r['score']:.3f}] [{r['source']}] {r['content'][:80]}...")
