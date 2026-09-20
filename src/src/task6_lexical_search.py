"""
Task 6 — Lexical Search Module (BM25).
"""

from pathlib import Path
from rank_bm25 import BM25Okapi
import numpy as np

# Load corpus
CORPUS: list[dict] = []  
_bm25_model = None

def load_corpus():
    """Load corpus from data/standardized if CORPUS is empty."""
    global CORPUS
    if CORPUS:
        return
        
    from src.task4_chunking_indexing import load_documents, chunk_documents
    docs = load_documents()
    if docs:
        CORPUS.extend(chunk_documents(docs))


def build_bm25_index(corpus: list[dict]):
    """Xây dựng BM25 index từ corpus."""
    global _bm25_model
    tokenized_corpus = [doc["content"].lower().split() for doc in corpus]
    _bm25_model = BM25Okapi(tokenized_corpus)
    return _bm25_model


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Tìm kiếm từ khóa sử dụng BM25."""
    global _bm25_model
    if not CORPUS:
        load_corpus()
    if _bm25_model is None and CORPUS:
        build_bm25_index(CORPUS)
        
    if _bm25_model is None:
        return []

    tokenized_query = query.lower().split()
    scores = _bm25_model.get_scores(tokenized_query)
    
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            results.append({
                "content": CORPUS[idx]["content"],
                "score": float(scores[idx]),
                "metadata": CORPUS[idx]["metadata"]
            })
    return results


if __name__ == "__main__":
    results = lexical_search("phương thức thanh toán shopee", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
