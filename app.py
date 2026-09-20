"""Chatbot RAG hỗ trợ khách hàng sàn thương mại điện tử."""

import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


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


def render_sources(sources: list[dict], retrieval_source: str) -> None:
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
            st.caption(source["content"])
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
            )

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm nguồn và soạn câu trả lời..."):
            try:
                result = generate_with_citation(query, top_k=top_k)
            except Exception as error:
                # Provider hoặc vector store lỗi thì báo rõ, không để UI chết.
                result = {
                    "answer": f"Hệ thống gặp lỗi khi xử lý câu hỏi: {error}",
                    "sources": [],
                    "retrieval_source": "none",
                }

        st.markdown(result["answer"])
        render_sources(result["sources"], result["retrieval_source"])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
            "retrieval_source": result["retrieval_source"],
        }
    )
