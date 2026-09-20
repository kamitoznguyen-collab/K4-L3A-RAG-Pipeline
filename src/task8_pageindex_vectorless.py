"""
Task 8 — PageIndex vectorless fallback.

PageIndex đánh index theo cây mục lục của tài liệu thay vì theo vector, nên nó
vẫn tìm được khi dense retrieval "lạc" — đúng tình huống mà Task 9 cần fallback.

Đây là dịch vụ ngoài nên mọi lời gọi đều có timeout và bọc try/except; khi
chưa cấu hình PAGEINDEX_API_KEY hoặc khi provider lỗi, hàm trả về danh sách
rỗng để Task 9 quay lại dùng hybrid result. Không bịa nội dung trả về.
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")

LANDING_LEGAL_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
DOC_ID_CACHE = Path(__file__).parent.parent / "pageindex_doc_ids.json"

# PageIndex xử lý bất đồng bộ; đây là trần chờ để pipeline không treo UI.
READY_TIMEOUT_SECONDS = 60
RETRIEVAL_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 2


def _get_client():
    """Trả PageIndexClient, hoặc None nếu chưa cấu hình API key."""
    if not PAGEINDEX_API_KEY:
        return None
    from pageindex import PageIndexClient

    return PageIndexClient(api_key=PAGEINDEX_API_KEY)


def _load_cache() -> dict:
    if not DOC_ID_CACHE.is_file():
        return {}
    try:
        return json.loads(DOC_ID_CACHE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    DOC_ID_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DOC_ID_CACHE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _extract_doc_id(response: dict) -> str | None:
    for key in ("doc_id", "id", "documentId", "document_id"):
        value = response.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def upload_documents() -> dict:
    """Upload PDF gốc lên PageIndex và cache lại doc_id theo tên file."""
    client = _get_client()
    if client is None:
        print("PAGEINDEX_API_KEY chưa được cấu hình — bỏ qua upload.")
        return {}

    cache = _load_cache()
    for path in sorted(LANDING_LEGAL_DIR.glob("*.pdf")):
        if path.name in cache:
            print(f"Đã có doc_id, bỏ qua: {path.name}")
            continue
        try:
            response = client.submit_document(file_path=str(path))
        except Exception as error:
            print(f"Upload thất bại {path.name}: {error}")
            continue

        doc_id = _extract_doc_id(response)
        if doc_id is None:
            print(f"Không đọc được doc_id từ response của {path.name}: {response}")
            continue
        cache[path.name] = doc_id
        print(f"Uploaded {path.name} -> {doc_id}")

    _save_cache(cache)
    return cache


def _wait_until_ready(client, doc_id: str) -> bool:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if client.is_retrieval_ready(doc_id):
            return True
        time.sleep(POLL_INTERVAL_SECONDS)
    return False


def _await_retrieval(client, retrieval_id: str) -> dict | None:
    deadline = time.monotonic() + RETRIEVAL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        response = client.get_retrieval(retrieval_id)
        status = str(response.get("status", "")).lower()
        if status in {"completed", "success", "succeeded", "done"}:
            return response
        if status in {"failed", "error"}:
            return None
        time.sleep(POLL_INTERVAL_SECONDS)
    return None


def _extract_nodes(response: dict) -> list[dict]:
    """PageIndex đổi tên field giữa các bản; thử lần lượt các khả năng."""
    for key in ("sources", "retrieved_nodes", "nodes", "results"):
        value = response.get(key)
        if isinstance(value, list) and value:
            return value
    retrieval = response.get("retrieval")
    if isinstance(retrieval, dict):
        return _extract_nodes(retrieval)
    return []


def _node_text(node: dict) -> str:
    for key in ("relevant_contents", "text", "content", "node_text", "summary"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list) and value:
            joined = "\n".join(str(item) for item in value if str(item).strip())
            if joined.strip():
                return joined.strip()
    return ""


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if top_k <= 0:
        return []

    client = _get_client()
    if client is None:
        return []

    cache = _load_cache()
    if not cache:
        cache = upload_documents()
    if not cache:
        return []

    results: list[dict] = []
    for source_name, doc_id in cache.items():
        try:
            if not _wait_until_ready(client, doc_id):
                continue
            submitted = client.submit_query(doc_id=doc_id, query=query)
            retrieval_id = submitted.get("retrieval_id")
            if not retrieval_id:
                continue
            response = _await_retrieval(client, retrieval_id)
            if response is None:
                continue
        except Exception as error:
            print(f"PageIndex lỗi trên {source_name}: {error}")
            continue

        for index, node in enumerate(_extract_nodes(response)):
            content = _node_text(node)
            if not content:
                continue
            node_id = str(node.get("node_id") or node.get("id") or index)
            results.append(
                {
                    "id": f"pageindex::{doc_id}::{node_id}",
                    "content": content,
                    # API không trả score chuẩn hoá, gán giảm dần theo rank.
                    "score": 1.0 / (index + 1),
                    "metadata": {
                        "source": source_name,
                        "title": node.get("title") or Path(source_name).stem,
                        "doc_type": "legal",
                        "url": None,
                        "chunk_index": index,
                    },
                    "retrieval_method": "pageindex",
                }
            )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    if not PAGEINDEX_API_KEY:
        print("Set PAGEINDEX_API_KEY trong .env rồi chạy lại (đăng ký tại pageindex.ai).")
    else:
        upload_documents()
        for result in pageindex_search("chính sách hoàn tiền", top_k=3):
            print(f"[{result['score']:.3f}] {result['id']} — {result['content'][:80]}...")
