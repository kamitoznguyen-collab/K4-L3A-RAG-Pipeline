"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

PDF/DOCX được convert bằng MarkItDown, JSON được render thủ công kèm metadata ở
đầu file. Chạy lại nhiều lần là idempotent: mỗi file nguồn luôn map tới đúng một
file .md cùng stem nên không sinh bản trùng.
"""

import json
import re
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

# Ngắn hơn mức này thì chunk gần như chắc chắn vô dụng cho retrieval.
MIN_CONTENT_CHARS = 200

# MarkItDown trích text từ PDF theo vị trí ký tự nên chèn khoảng trắng đôi/ba
# giữa các từ ("Shopee  hỗ  trợ"). Gom lại một space để BM25 và embedding đọc
# đúng văn bản; xuống dòng giữ nguyên để không phá cấu trúc Markdown.
_MULTISPACE = re.compile(r"[ \t]{2,}")


def _normalize_spacing(text: str) -> str:
    lines = (_MULTISPACE.sub(" ", line).rstrip() for line in text.splitlines())
    return "\n".join(lines)


def _write_markdown(output_path: Path, content: str) -> bool:
    """Ghi Markdown và bỏ qua nội dung rỗng/quá ngắn."""
    text = content.strip()
    if len(text) < MIN_CONTENT_CHARS:
        print(f"  Skipped (chỉ {len(text)} ký tự): {output_path.name}")
        return False
    output_path.write_text(text + "\n", encoding="utf-8")
    print(f"  Saved: {output_path}")
    return True


def convert_legal_docs() -> None:
    """Convert PDF/DOCX vào standardized/legal."""
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = MarkItDown()
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        print(f"Converting: {path.name}")
        try:
            result = converter.convert(str(path))
        except Exception as error:
            print(f"  Failed: {error}")
            continue
        _write_markdown(
            output_dir / f"{path.stem}.md", _normalize_spacing(result.text_content)
        )


def convert_news_articles() -> None:
    """Convert JSON vào standardized/news, giữ metadata ở header."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        print(f"Converting: {path.name}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            print(f"  Failed: {error}")
            continue

        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        _write_markdown(output_dir / f"{path.stem}.md", header + data["content_markdown"])


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("--- Legal documents ---")
    convert_legal_docs()
    print("\n--- News articles ---")
    convert_news_articles()
    print(f"\nSaved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
