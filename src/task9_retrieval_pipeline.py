"""
Task 9 — Retrieval pipeline hoàn chỉnh.

Luồng xử lý:
    1. Chạy semantic_search và lexical_search.
    2. Fuse hai danh sách bằng RRF đúng một lần.
    3. Lấy best cosine score gốc từ dense results.
    4. Nếu score dưới threshold, thử PageIndex fallback.
    5. Nếu fallback lỗi hoặc rỗng, trả hybrid results thay vì crash.

Threshold so với cosine score gốc của dense, KHÔNG so với RRF score: RRF score
chỉ là tổng nghịch đảo thứ hạng (cỡ 0.01-0.03) nên không có ý nghĩa về độ
tương đồng.
"""

import os

from dotenv import load_dotenv

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


load_dotenv()

# Hiệu chỉnh trên corpus của nhóm với paraphrase-multilingual-MiniLM-L12-v2,
# đo bằng 10 query in-domain và 8 query out-of-domain:
#   in-domain      : 0.621 - 0.874
#   out-of-domain  : 0.105 - 0.442
# 0.53 nằm giữa hai vùng, cách mỗi bên khoảng 0.09. Khoảng trống rộng 0.18 này
# là nhờ corpus đủ lớn (88 chunk) và đúng một miền chủ đề; bản corpus nhỏ
# trước đó chỉ tách được 0.024. Đổi corpus hoặc embedding model phải đo lại.
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD") or 0.53)
DEFAULT_TOP_K = 5

# Số ứng viên lấy từ mỗi ranker trước khi fuse, tính theo bội của top_k. Nới
# rộng giúp những chunk chỉ một ranker tìm ra có cơ hội lọt vào kết quả, nhưng
# cũng kéo thêm chunk nhiễu — phải đo cả recall lẫn precision khi đổi.
CANDIDATE_MULTIPLIER = 2


def expand_query(query: str) -> str:
    """Hook biến đổi query trước khi dense search (HyDE, query expansion...).

    Mặc định trả nguyên query. Ai làm HyDE thì thay thân hàm này, không cần
    sửa retrieve().
    """
    return query


def post_rerank(query: str, results: list[dict], top_k: int) -> list[dict]:
    """Hook xếp hạng lại sau RRF (cross-encoder, LLM rerank...).

    Mặc định trả nguyên kết quả. Ai làm cross-encoder thì thay thân hàm này.
    Output phải giữ đúng SearchResult contract.
    """
    return results


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid hoặc pageindex SearchResult."""
    candidates = top_k * CANDIDATE_MULTIPLIER

    try:
        dense = semantic_search(expand_query(query), top_k=candidates)
    except Exception as error:
        print(f"Semantic search lỗi: {error}")
        dense = []

    try:
        sparse = lexical_search(query, top_k=candidates)
    except Exception as error:
        print(f"Lexical search lỗi: {error}")
        sparse = []

    if use_reranking:
        hybrid = post_rerank(query, rerank_rrf([dense, sparse], top_k=top_k), top_k)
    else:
        hybrid = dense[:top_k]

    best_dense_score = dense[0]["score"] if dense else 0.0
    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return fallback
        except Exception as error:
            print(f"PageIndex fallback lỗi: {error}")

    return hybrid[:top_k]


if __name__ == "__main__":
    queries = [
        "Điều kiện xét học bổng UET là gì?",
        "Thư viện PTIT cho sinh viên mượn bao nhiêu tài liệu?",
        "xyzabc123nonsense",
    ]
    for query in queries:
        print(f"\nQuery: {query}")
        for result in retrieve(query, top_k=3):
            print(
                f"  [{result['score']:.4f}] ({result['retrieval_method']}) "
                f"{result['id']} — {result['content'][:70]}..."
            )
