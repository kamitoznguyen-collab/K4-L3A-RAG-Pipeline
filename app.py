"""Chatbot RAG tra cứu dịch vụ đại học: học bổng, hỗ trợ tài chính, thư viện."""

import difflib
import html

import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import call_llm, generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="RAG Chatbot — Dịch vụ đại học",
    page_icon="🎓",
    layout="wide",
)

RETRIEVAL_LABELS = {
    "hybrid": "Hybrid (dense + BM25 + RRF)",
    "pageindex": "PageIndex fallback (vectorless)",
    "none": "Không tìm được nguồn nào",
}

# Số lượt hội thoại gần nhất đưa vào prompt rewrite. Đủ để hiểu "cái đó", "còn
# gì nữa" mà không làm prompt phình ra theo độ dài cuộc trò chuyện.
HISTORY_TURNS = 3

# Đoạn trùng ngắn hơn mức này thường là hư từ ("và", "của"), highlight vào chỉ
# làm rối mắt.
MIN_HIGHLIGHT_CHARS = 12

REWRITE_PROMPT = """Viết lại câu hỏi cuối thành một câu đứng độc lập, hiểu được
mà không cần đọc lịch sử hội thoại.

Chỉ trả về đúng câu hỏi đã viết lại, không giải thích, không thêm dấu ngoặc.
Nếu câu hỏi cuối vốn đã đứng độc lập được thì trả lại nguyên văn."""


def rewrite_followup(query: str, history: list[dict]) -> str:
    """Biến câu hỏi phụ thuộc ngữ cảnh thành câu đứng độc lập.

    Không có lịch sử thì trả nguyên query. LLM lỗi cũng trả nguyên query —
    retrieval kém đi ở câu đó chứ chatbot không chết.
    """
    if not history:
        return query

    lines = []
    for message in history[-HISTORY_TURNS * 2 :]:
        role = "Người dùng" if message["role"] == "user" else "Trợ lý"
        lines.append(f"{role}: {message['content'][:300]}")

    conversation = "\n".join(lines)
    try:
        rewritten = call_llm(
            REWRITE_PROMPT,
            f"Lịch sử hội thoại:\n{conversation}\n\nCâu hỏi cuối: {query}",
        ).strip()
    except Exception as error:
        print(f"Rewrite follow-up lỗi, dùng câu hỏi gốc: {error}")
        return query

    return rewritten or query


def highlight_overlap(chunk_text: str, answer: str) -> str:
    """Bôi vàng những đoạn trong chunk mà câu trả lời dùng lại gần như nguyên văn.

    Dùng difflib so khớp chuỗi con chung thay vì gọi LLM: rẻ, tức thì, và không
    thêm một nguồn bịa đặt nữa vào khâu hiển thị nguồn.
    """
    if not answer.strip():
        return html.escape(chunk_text)

    matcher = difflib.SequenceMatcher(None, chunk_text, answer, autojunk=False)
    spans = [
        (block.a, block.a + block.size)
        for block in matcher.get_matching_blocks()
        if block.size >= MIN_HIGHLIGHT_CHARS
    ]

    if not spans:
        return html.escape(chunk_text)

    # Gộp các đoạn dính liền nhau, tránh sinh ra </mark><mark> vô nghĩa.
    merged: list[list[int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    spans = [(start, end) for start, end in merged]

    parts = []
    cursor = 0
    for start, end in spans:
        parts.append(html.escape(chunk_text[cursor:start]))
        parts.append(
            "<mark style='background:#fde68a;color:inherit;'>"
            + html.escape(chunk_text[start:end])
            + "</mark>"
        )
        cursor = end
    parts.append(html.escape(chunk_text[cursor:]))
    return "".join(parts)


if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("🎓 RAG Chatbot")
    st.caption(
        "Trả lời câu hỏi về học bổng, hỗ trợ tài chính và nội quy thư viện của "
        "các trường đại học, kèm trích dẫn nguồn."
    )
    top_k = st.slider("Số chunks đưa vào context", 3, 10, 5)
    st.divider()
    st.caption(
        "Corpus: 5 văn bản quy định + 5 thông báo học bổng, thu thập từ cổng "
        "thông tin chính thức của các trường và quỹ học bổng. Nguồn và ngày thu "
        "thập ghi trong data/sources/sources.csv. Bot chỉ trả lời dựa trên "
        "corpus này."
    )
    if st.button("Xoá hội thoại", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


def render_sources(
    sources: list[dict], retrieval_source: str, answer: str = ""
) -> None:
    """Hiển thị nguồn để người đọc đối chiếu được từng citation."""
    label = RETRIEVAL_LABELS.get(retrieval_source, retrieval_source)
    if not sources:
        st.caption(f"Nguồn: {label}")
        return

    with st.expander(f"📎 {len(sources)} nguồn tham khảo — {label}"):
        for index, source in enumerate(sources, 1):
            metadata = source.get("metadata", {})
            url = metadata.get("url") or ""
            heading = f"**[Document {index}] {metadata.get('title', 'Unknown')}**"
            if url:
                # Link nguồn để người dùng kiểm chứng citation tận trang gốc.
                heading += f"  \n[{url}]({url})"
            st.markdown(
                f"{heading}  \n"
                f"`{metadata.get('source', '?')}` · loại: "
                f"`{metadata.get('doc_type', '?')}` · chunk "
                f"`{metadata.get('chunk_index', '?')}` · score "
                f"`{source.get('score', 0):.4f}` · "
                f"`{source.get('retrieval_method', '?')}`"
            )
            st.markdown(
                "<div style='font-size:0.85em;opacity:0.85;white-space:pre-wrap;'>"
                + highlight_overlap(source["content"], answer)
                + "</div>",
                unsafe_allow_html=True,
            )
            if index < len(sources):
                st.divider()


st.title("Chatbot tra cứu dịch vụ đại học")
st.caption(
    "Hỏi về điều kiện xét học bổng, mức học bổng, hỗ trợ tài chính hoặc nội quy "
    "mượn tài liệu thư viện. Mỗi câu trả lời đều kèm [Document N] trỏ về nguồn ở "
    "phần mở rộng bên dưới."
)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(
                message.get("sources", []),
                message.get("retrieval_source", "none"),
                message["content"],
            )

query = st.chat_input("Nhập câu hỏi...")

if query:
    # Rewrite trước khi append, để lịch sử chưa chứa chính câu hỏi này.
    history = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm nguồn và soạn câu trả lời..."):
            try:
                search_query = rewrite_followup(query, history)
                if search_query != query:
                    st.caption(f"Hiểu câu hỏi thành: *{search_query}*")
                result = generate_with_citation(search_query, top_k=top_k)
            except Exception as error:
                # Provider hoặc vector store lỗi thì báo rõ, không để UI chết.
                result = {
                    "answer": f"Hệ thống gặp lỗi khi xử lý câu hỏi: {error}",
                    "sources": [],
                    "retrieval_source": "none",
                }

        st.markdown(result["answer"])
        render_sources(
            result["sources"], result["retrieval_source"], result["answer"]
        )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
            "retrieval_source": result["retrieval_source"],
        }
    )
