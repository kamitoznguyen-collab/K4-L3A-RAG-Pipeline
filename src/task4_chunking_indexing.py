"""
Task 4 — Chunking, embedding và indexing.

Mọi Document/Chunk ở đây tuân theo docs/MODULE_CONTRACTS.md: có `id` ổn định,
metadata giữ nguyên source/title/doc_type/url xuyên suốt pipeline, chunk mang
thêm `chunk_index`. ID được sinh từ đường dẫn tương đối nên chạy lại pipeline
chỉ upsert đè lên chính nó, không tạo dữ liệu trùng.

Task 5 phải import lại embed_texts() từ đây để dense query và index luôn dùng
chung một model và một dimension.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# 500 ký tự (~100-150 từ) đủ chứa trọn một điều khoản chính sách mà không kéo
# theo quá nhiều ngữ cảnh nhiễu. Overlap 50 giữ lại câu bị cắt ở biên chunk.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

# paraphrase-multilingual-MiniLM-L12-v2 (384 chiều) thay cho bge-m3: nhẹ hơn
# nhiều lần trên CPU nhưng vẫn hiểu tiếng Việt — bắt buộc vì corpus là văn bản
# học bổng tiếng Việt.
#
# Đã thử all-MiniLM-L6-v2 (model tiếng Anh) và phải loại: trên corpus này nó
# chấm query ngoài miền bằng tiếng Việt tới 0.58-0.69, chồng lấn hoàn toàn với
# query trong miền (0.63-0.84), nên không thể đặt threshold fallback. Bản
# multilingual tách được hai vùng (xem SCORE_THRESHOLD ở Task 9).
#
# Đổi model thì phải xoá chroma_db/ và chạy lại Task 4 vì dimension và không
# gian vector không tương thích ngược.
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
)
EMBEDDING_DIM = 384

COLLECTION_NAME = "rag_documents"

# Prepend tiêu đề tài liệu vào text đem đi embed. Xem chunk_embedding_text().
CONTEXTUAL_CHUNKING = True

_MODEL = None

_HEADING_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)

# Task 1 in khối nguồn lên đầu mỗi PDF và Task 3 in lên đầu mỗi bài news, để
# người đọc truy ngược được URL. URL được tách ra metadata vì đó mới là chỗ của
# nó theo contract (DocumentMetadata.url).
#
# Đã thử loại luôn khối nguồn khỏi text trước khi chunk — lập luận là nó chiếm
# gần trọn chunk đầu và dense search chấm nó cao trong khi nó không trả lời được
# câu nào. Nhưng đo bằng eval_pipeline thì cấu hình đó KÉM HƠN, nên giữ nguyên
# text. Số liệu ở mục "Bonus experiments" trong group_project/evaluation/RESULT.md.
_SOURCE_URL_PATTERN = re.compile(
    r"^\s*(?:\*\*Source:\*\*|Nguồn:)\s*(\S+)", re.MULTILINE
)


def _get_sentence_transformer():
    """Load model local một lần rồi tái sử dụng."""
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer(EMBEDDING_MODEL)
    return _MODEL


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách text theo EMBEDDING_PROVIDER trong .env."""
    if not texts:
        return []

    if EMBEDDING_PROVIDER == "sentence_transformers":
        return _get_sentence_transformer().encode(texts).tolist()

    if EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]

    if EMBEDDING_PROVIDER == "gemini":
        from google import genai

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.embed_content(model=EMBEDDING_MODEL, contents=texts)
        return [list(item.values) for item in response.embeddings]

    raise ValueError(f"EMBEDDING_PROVIDER không hợp lệ: {EMBEDDING_PROVIDER}")


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _extract_title(content: str, fallback: str) -> str:
    """Lấy title đọc được để citation đối chiếu ra tên tài liệu, không phải slug.

    News đi qua Task 3 nên luôn có H1. Legal đi từ PDF qua MarkItDown và không
    có heading nào, nhưng dòng đầu tiên chính là tiêu đề văn bản — nhận dạng
    bằng cách nó ngắn và không kết thúc như một câu.
    """
    match = _HEADING_PATTERN.search(content)
    if match and match.group(1).strip():
        return match.group(1).strip()

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) <= 120 and not stripped.endswith((".", ":", ",", ";")):
            return stripped
        break
    return fallback


def _extract_source_url(content: str) -> str | None:
    """Lấy URL nguồn từ khối header để đưa vào metadata."""
    match = _SOURCE_URL_PATTERN.search(content)
    return match.group(1).strip() if match else None


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents: list[dict] = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            continue
        url = _extract_source_url(raw)
        # Chỉ xét phần đường dẫn bên trong data/standardized/, không xét đường
        # dẫn tuyệt đối: một thư mục cha tên "legal" sẽ làm lệch doc_type.
        relative = path.relative_to(STANDARDIZED_DIR)
        doc_type = "legal" if "legal" in relative.parts[:-1] else "news"
        documents.append(
            {
                "id": relative.as_posix(),
                "content": raw,
                "metadata": {
                    "source": path.name,
                    "title": _extract_title(raw, path.stem),
                    "doc_type": doc_type,
                    "url": url,
                },
            }
        )
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict] = []
    for document in documents:
        index = 0
        for text in splitter.split_text(document["content"]):
            if not text.strip():
                continue
            chunks.append(
                {
                    "id": f"{document['id']}::chunk-{index}",
                    "content": text,
                    "metadata": {**document["metadata"], "chunk_index": index},
                }
            )
            index += 1
    return chunks


def chunk_embedding_text(chunk: dict) -> str:
    """Text đem đi embed, có tiêu đề tài liệu làm ngữ cảnh.

    Không đụng vào `chunk["content"]`: phần đó vẫn là text gốc để đưa vào LLM
    và để contract test kiểm độ dài. Chỉ vector mới mang thêm tiêu đề.

    Lý do: chunk chứa chi tiết (danh sách điều kiện, mức tiền, tiêu chí) thường
    không mang từ khoá chủ đề nào, vì tên tài liệu chỉ xuất hiện ở chunk đầu.
    Dense search vì thế không nối được câu hỏi "điều kiện xét học bổng UET" với
    chunk chỉ liệt kê "Khá trở lên", "15 tín chỉ".
    """
    if not CONTEXTUAL_CHUNKING:
        return chunk["content"]
    title = chunk["metadata"].get("title", "")
    if not title or chunk["content"].lstrip().startswith(title):
        return chunk["content"]
    return f"{title}\n\n{chunk['content']}"


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk, giữ nguyên các field khác."""
    vectors = embed_texts([chunk_embedding_text(chunk) for chunk in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def _serialize_metadata(metadata: dict) -> dict:
    """Chroma không nhận None nên url rỗng được lưu thành chuỗi rỗng."""
    return {
        key: ("" if value is None else value) for key, value in metadata.items()
    }


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    collection = get_collection()
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=[_serialize_metadata(chunk["metadata"]) for chunk in chunks],
    )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    print(f"Chunking : {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"Embedding: {EMBEDDING_MODEL} via {EMBEDDING_PROVIDER} (dim={EMBEDDING_DIM})")
    print(f"Collection: {COLLECTION_NAME}")

    documents = load_documents()
    print(f"Loaded {len(documents)} documents")
    if not documents:
        print(f"Chưa có Markdown trong {STANDARDIZED_DIR}. Chạy Task 3 trước.")
        return

    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")

    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
