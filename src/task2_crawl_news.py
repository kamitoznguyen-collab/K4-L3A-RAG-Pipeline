"""
Task 2 — Thu thập bài viết/thông báo công khai.

Năm thông báo học bổng còn lại trong data/sources/ (phần không mang tính quy
chế, do Task 1 xử lý) được ghi ra JSON trong data/landing/news/ kèm đủ metadata
mà Task 3 cần: url, title, date_crawled, content_markdown.

Nội dung đã được nhóm thu thập sẵn từ các URL trong data/sources/sources.csv,
nên Task 2 đọc lại từ đó thay vì crawl lại mỗi lần chạy — crawl lại vừa chậm
vừa làm kết quả thay đổi giữa các lần chạy, và nhiều trang nguồn đã đổi nội
dung so với `retrieved_at` ghi trong sources.csv.

Muốn crawl trực tiếp: cài `pip install -e ".[crawl]"`, `python -m playwright
install chromium`, rồi bật lại nhánh Crawl4AI trong crawl_article().
"""

import asyncio
import json
from pathlib import Path

from .task1_collect_legal_docs import (
    LEGAL_DOC_IDS,
    load_sources,
    read_source_document,
)


ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "landing" / "news"


def news_doc_ids() -> list[str]:
    """Mọi tài liệu nguồn không thuộc nhóm quy chế của Task 1."""
    return [
        doc_id for doc_id in load_sources() if doc_id not in set(LEGAL_DOC_IDS)
    ]


def article_urls() -> list[str]:
    """URL của các bài Task 2 phụ trách.

    Đọc lúc gọi chứ không phải lúc import: import package không nên phụ thuộc
    vào việc data/sources/sources.csv đã tồn tại hay chưa.
    """
    sources = load_sources()
    return [sources[doc_id]["source_url"] for doc_id in news_doc_ids()]


async def crawl_article(url: str) -> dict:
    """Lấy nội dung một bài viết theo URL.

    Hiện đọc lại bản đã thu thập trong data/sources/. Khi muốn crawl trực tiếp,
    thay thân hàm bằng Crawl4AI/Firecrawl và giữ nguyên 4 field output:

        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return {
                "url": url,
                "title": result.metadata.get("title", "Unknown"),
                "date_crawled": datetime.now().isoformat(),
                "content_markdown": result.markdown,
            }
    """
    sources = load_sources()
    for doc_id, source in sources.items():
        if source["source_url"] != url:
            continue
        metadata, body = read_source_document(doc_id)
        return {
            "url": url,
            "title": metadata.get("title") or source["title"],
            "date_crawled": source["retrieved_at"],
            "content_markdown": body,
            "document_version": source.get("document_version", "not-stated"),
            "license_or_permission": source.get(
                "license_or_permission", "public-source"
            ),
        }
    raise ValueError(f"Không có bản thu thập nào cho URL: {url}")


async def crawl_all() -> None:
    """Ghi mỗi bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    sources = load_sources()
    for index, doc_id in enumerate(news_doc_ids(), 1):
        url = sources[doc_id]["source_url"]
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"{doc_id}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"[{index}] Saved: {output.name}")
        except Exception as error:
            print(f"[{index}] Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
