"""
Task 6 — Lexical search bằng BM25.

BM25 chạy trên đúng bộ chunks mà Task 4 sinh ra, nên ID của dense và sparse
khớp nhau và Task 7 fuse được theo ID. BM25 bù cho dense ở các truy vấn chứa
từ khóa chính xác, mã tài liệu hoặc tên riêng.
"""

import numpy as np

from .task4_chunking_indexing import chunk_documents, load_documents


CORPUS: list[dict] = []

# Cache index theo đúng object corpus đang dùng, để test monkeypatch CORPUS
# vẫn được build lại thay vì ăn phải index cũ.
_INDEX_CACHE: dict = {"corpus_key": None, "bm25": None}


def load_corpus() -> None:
    """Nạp chunks vào CORPUS nếu chưa có."""
    if CORPUS:
        return
    CORPUS.extend(chunk_documents(load_documents()))


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Okapi

    tokenized = [item["content"].lower().split() for item in corpus]
    return BM25Okapi(tokenized)


def _get_index(corpus: list[dict]):
    """Trả BM25 index đã cache cho corpus hiện tại."""
    # Gồm cả id đầu/cuối chứ không chỉ id(list) và độ dài: một list khác có thể
    # tái sử dụng cùng địa chỉ bộ nhớ sau khi list cũ bị thu hồi, và lúc đó
    # cache sẽ trả về index của corpus cũ.
    key = (
        id(corpus),
        len(corpus),
        corpus[0]["id"] if corpus else None,
        corpus[-1]["id"] if corpus else None,
    )
    if _INDEX_CACHE["corpus_key"] != key:
        _INDEX_CACHE["corpus_key"] = key
        _INDEX_CACHE["bm25"] = build_bm25_index(corpus)
    return _INDEX_CACHE["bm25"]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    if top_k <= 0:
        return []
    if not CORPUS:
        load_corpus()
    if not CORPUS:
        return []

    corpus = CORPUS
    bm25 = _get_index(corpus)
    scores = bm25.get_scores(query.lower().split())

    # Sort giảm dần, stable để các score bằng nhau giữ nguyên thứ tự corpus.
    indices = np.argsort(-scores, kind="stable")[:top_k]

    # Bỏ các chunk không khớp từ khóa nào. Nhưng khi corpus quá nhỏ, BM25Okapi
    # cho IDF = 0 cho mọi từ (log(N-1+0.5) - log(1.5) = 0 khi N = 2), lúc đó
    # toàn bộ score bằng 0 và lọc đi sẽ trả về rỗng — nên chỉ lọc khi thực sự
    # có ít nhất một chunk ghi điểm dương.
    has_positive = bool(len(scores)) and float(scores.max()) > 0

    results = []
    for index in indices:
        if has_positive and scores[index] <= 0:
            continue
        item = corpus[int(index)]
        results.append(
            {
                "id": item["id"],
                "content": item["content"],
                "score": float(scores[index]),
                "metadata": dict(item["metadata"]),
                "retrieval_method": "bm25",
            }
        )
    return results


if __name__ == "__main__":
    for result in lexical_search("phương thức thanh toán", top_k=3):
        print(f"[{result['score']:.3f}] {result['id']} — {result['content'][:80]}...")
