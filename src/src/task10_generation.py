"""
Task 10 — Generation with Citations.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

SYSTEM_PROMPT = """Bạn là trợ lý trả lời câu hỏi về chính sách thương mại điện tử và hỗ trợ khách hàng.

Quy tắc bắt buộc:
1. Chỉ sử dụng thông tin từ context được cung cấp — KHÔNG bịa đặt
2. Mỗi khẳng định phải có trích dẫn ngay sau, ví dụ: [Document 1] hoặc [1]
3. Nếu context không đủ thông tin → trả lời: "Tôi không thể xác minh thông tin này từ nguồn hiện có"
4. Trả lời bằng tiếng Việt, có cấu trúc rõ ràng theo đoạn văn
5. Không suy luận hay mở rộng ngoài những gì được nêu trong context"""


def get_llm_client():
    if LLM_PROVIDER == "deepseek":
        from openai import OpenAI
        return OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )
    elif LLM_PROVIDER == "openai":
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY)
    elif LLM_PROVIDER == "google":
        raise NotImplementedError("Implement Google client if needed")
    elif LLM_PROVIDER == "anthropic":
        raise NotImplementedError("Implement Anthropic client if needed")
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Sắp xếp chunks để tránh "lost in the middle" effect.
    """
    if len(chunks) <= 2:
        return chunks
    
    front = chunks[::2]   # index 0, 2, 4 -> đặt ở đầu
    back = chunks[1::2]   # index 1, 3    -> đặt ở cuối (reversed)
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Format chunks thành context string cho prompt."""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("metadata", {}).get("source", f"Source {i}")
        doc_type = chunk.get("metadata", {}).get("type", "unknown")
        context_parts.append(
            f"[Document {i} | Source: {source} | Type: {doc_type}]\n"
            f"{chunk['content']}\n"
        )
    return "\n---\n".join(context_parts)


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """End-to-end RAG generation có citation."""
    from src.task9_retrieval_pipeline import retrieve
    
    chunks = retrieve(query, top_k=top_k)
    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    
    user_message = f"""Context:\n{context}\n\n---\n\nQuestion: {query}"""
    
    # Check if API key is missing for the chosen provider
    has_key = (
        (LLM_PROVIDER == "deepseek" and DEEPSEEK_API_KEY and not DEEPSEEK_API_KEY.startswith("sk-..."))
        or (LLM_PROVIDER == "openai" and OPENAI_API_KEY)
        or LLM_PROVIDER not in ("deepseek", "openai")
    )
    
    if not has_key:
        return {
            "answer": f"(MOCK ANSWER — chưa có API key) Dựa vào các tài liệu, đây là mock response cho: {query} [1].",
            "sources": chunks,
            "retrieval_source": chunks[0].get("source", "hybrid") if chunks else "none",
            "prompt_tokens": 0,
            "completion_tokens": 0
        }
        
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        answer = response.choices[0].message.content
        usage = response.usage
        
        return {
            "answer": answer,
            "sources": chunks,
            "retrieval_source": chunks[0].get("source", "hybrid") if chunks else "none",
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0
        }
    except Exception as e:
        print(f"LLM Error: {e}")
        return {
            "answer": f"Lỗi khi gọi LLM: {e}",
            "sources": chunks,
            "retrieval_source": chunks[0].get("source", "hybrid") if chunks else "none",
            "prompt_tokens": 0,
            "completion_tokens": 0
        }


if __name__ == "__main__":
    test_queries = [
        "Shopee hỗ trợ những phương thức thanh toán nào?",
        "Làm sao để yêu cầu đổi trả hay hoàn tiền?",
        "Cần chuẩn bị bằng chứng gì khi yêu cầu hoàn tiền?",
    ]

    for q in test_queries:
        print(f"\n{'='*70}")
        print(f"Q: {q}")
        print("=" * 70)
        result = generate_with_citation(q)
        print(f"\nA: {result['answer']}")
        print(f"\n[Sources: {len(result['sources'])} chunks | via {result['retrieval_source']}]")
