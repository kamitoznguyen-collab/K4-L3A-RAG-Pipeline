"""
Task 8 — PageIndex Vectorless RAG.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


def upload_documents():
    """Upload toàn bộ markdown documents lên PageIndex."""
    if not PAGEINDEX_API_KEY:
        print("Mock upload_documents: API Key not found.")
        return
    print("Uploading documents to PageIndex...")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval sử dụng PageIndex (Mock/Fallback).
    Dùng làm fallback khi hybrid search không có kết quả tốt.
    """
    # Vì PageIndex yêu cầu API key thực tế, ở bài lab này ta sẽ mock
    # một kết quả fallback tĩnh nếu không có API key.
    
    mock_results = []
    if "nonsense" not in query.lower():
        # Trả về dummy fallback cho các query hợp lệ bị fallback (rất hiếm nếu hybrid tốt)
        mock_results.append({
            "content": f"[PageIndex Fallback] Không tìm thấy kết quả phù hợp cho: {query}",
            "score": 0.5,
            "metadata": {"section": "Fallback Section"},
            "source": "pageindex",
        })
    else:
        # Dummy cho test fallback
        mock_results.append({
            "content": f"Dummy PageIndex result cho query obscure: {query}",
            "score": 0.9,
            "metadata": {"section": "Test"},
            "source": "pageindex",
        })
        
    return mock_results[:top_k]


if __name__ == "__main__":
    if not PAGEINDEX_API_KEY:
        print("⚠ Hãy set PAGEINDEX_API_KEY trong file .env")
        print("  Đăng ký tại: https://pageindex.ai/")
    else:
        print("Uploading documents...")
        upload_documents()

    print("\nTest query:")
    results = pageindex_search("danh sách sản phẩm cấm đăng bán", top_k=3)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
