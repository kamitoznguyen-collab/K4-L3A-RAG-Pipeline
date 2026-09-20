"""
Task 10 — Generation có citation.

Luồng: retrieve -> reorder chống lost-in-the-middle -> format context có title
và source -> gọi LLM -> trả GenerationResult.

Khi không retrieve được gì, hoặc provider lỗi/chưa cấu hình, hàm trả safe
refusal thay vì bịa câu trả lời. Không có nhánh nào sinh nội dung giả lập.
"""

import os

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

# openai | deepseek | gemini | anthropic
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

DEEPSEEK_BASE_URL = "https://api.deepseek.com"

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "gemini": "gemini-2.0-flash",
    "anthropic": "claude-haiku-4-5-20251001",
}

REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

SYSTEM_PROMPT = f"""Bạn là trợ lý tra cứu thông tin dịch vụ đại học: học bổng, hỗ trợ tài chính và nội quy thư viện.

Quy tắc bắt buộc:
1. Chỉ dùng thông tin có trong context được cung cấp. Không suy luận, không bổ sung kiến thức ngoài.
2. Mỗi khẳng định phải kèm citation dạng [Document N] trỏ đúng document đã dùng.
3. Nếu context không đủ thông tin để trả lời, chỉ trả lời đúng câu: "{REFUSAL}"
4. Trả lời bằng tiếng Việt, ngắn gọn, có cấu trúc."""


def _resolve_model() -> str:
    return LLM_MODEL or DEFAULT_MODELS.get(LLM_PROVIDER, "")


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context.

    LLM chú ý kém nhất ở giữa context, nên chunk hạng cao được xếp ra hai đầu:
    hạng chẵn chạy xuôi ở đầu, hạng lẻ chạy ngược ở cuối.
    """
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label để citation đối chiếu được."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        parts.append(
            f"[Document {index} | Title: {metadata.get('title', 'Unknown')} | "
            f"Source: {metadata.get('source', 'Unknown')}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi provider được chọn trong .env và trả về text thuần."""
    model = _resolve_model()

    if LLM_PROVIDER in {"openai", "deepseek"}:
        from openai import OpenAI

        if LLM_PROVIDER == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        else:
            api_key = os.getenv("OPENAI_API_KEY", "")
            client = OpenAI(api_key=api_key)
        if not api_key:
            raise RuntimeError(f"Chưa cấu hình API key cho provider {LLM_PROVIDER}")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""

    if LLM_PROVIDER == "gemini":
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("Chưa cấu hình GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )
        return response.text or ""

    if LLM_PROVIDER == "anthropic":
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("Chưa cấu hình ANTHROPIC_API_KEY")
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        )

    raise ValueError(f"LLM_PROVIDER không hợp lệ: {LLM_PROVIDER}")


def _retrieval_source(chunks: list[dict]) -> str:
    """Quy về đúng 3 giá trị mà GenerationResult cho phép."""
    if not chunks:
        return "none"
    return "pageindex" if chunks[0].get("retrieval_method") == "pageindex" else "hybrid"


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {"answer": REFUSAL, "sources": [], "retrieval_source": "none"}

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\n---\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"LLM lỗi: {error}")
        answer = REFUSAL

    return {
        "answer": answer.strip() or REFUSAL,
        "sources": chunks,
        "retrieval_source": _retrieval_source(chunks),
    }


if __name__ == "__main__":
    for query in [
        "Học bổng FPT có những mức nào?",
        "Học bổng Sigma Gold có bao nhiêu suất?",
    ]:
        result = generate_with_citation(query)
        print(f"\nQ: {query}")
        print(f"A: {result['answer']}")
        print(f"[{len(result['sources'])} sources via {result['retrieval_source']}]")
