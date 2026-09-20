"""Day 8 — RAG Pipeline: chatbot tra cứu dịch vụ đại học (học bổng, thư viện)."""

import sys

# Console Windows mặc định là cp1252, không encode được tiếng Việt, nên mọi
# script demo `python -m src.taskN` sẽ chết vì UnicodeEncodeError. Ép UTF-8
# ngay khi import package để repo chạy được trên cả Windows lẫn Unix.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        # Stream đã bị pytest/Streamlit thay thế hoặc không hỗ trợ; bỏ qua.
        pass
