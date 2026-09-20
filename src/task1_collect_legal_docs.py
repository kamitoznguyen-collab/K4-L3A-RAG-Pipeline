"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Chủ đề nhóm: dịch vụ đại học — học bổng, hỗ trợ tài chính và nội quy thư viện.

Nguồn dữ liệu:
    Toàn bộ nội dung được nhóm thu thập từ cổng thông tin chính thức của các
    trường và quỹ học bổng. Mỗi tài liệu có `source_url`, `retrieved_at` và
    `document_version` ghi trong YAML frontmatter của file gốc ở data/sources/,
    đối chiếu 1-1 với data/sources/sources.csv.

    Các trang này publish dưới dạng HTML chứ không phát hành PDF. Task 1 render
    chúng ra PDF trong data/landing/legal/ để pipeline có định dạng tài liệu
    chính sách đồng nhất; nội dung là nguyên văn nguồn đã thu thập, PDF chỉ là
    vật chứa local. URL gốc luôn đi kèm nên người chấm kiểm chứng được.
"""

import csv
from pathlib import Path


ROOT = Path(__file__).parent.parent
SOURCES_DIR = ROOT / "data" / "sources"
SOURCES_CSV = SOURCES_DIR / "sources.csv"
DATA_DIR = ROOT / "data" / "landing" / "legal"

# Tài liệu mang tính quy chế/quy định — phần còn lại là thông báo, Task 2 xử lý.
LEGAL_DOC_IDS = (
    "noi-quy-thu-vien-ptit-sinh-vien",
    "noi-quy-thu-vien-ptit-can-bo",
    "hoc-bong-fpt-2024",
    "hoc-bong-uet-2025-2026",
    "hoc-bong-tdtu-2026",
)

# Font Unicode để render được tiếng Việt; fpdf2 core font chỉ có latin-1.
FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
)


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def load_sources() -> dict[str, dict]:
    """Đọc sources.csv thành mapping doc_id -> metadata."""
    with SOURCES_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return {row["doc_id"]: row for row in csv.DictReader(handle)}


def read_source_document(doc_id: str) -> tuple[dict, str]:
    """Tách YAML frontmatter và body của một file nguồn."""
    path = SOURCES_DIR / f"{doc_id}.md"
    text = path.read_text(encoding="utf-8")

    metadata: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        _, _, remainder = text.partition("---")
        front_matter, separator, body = remainder.partition("---")
        if not separator:
            body = remainder
        for line in front_matter.splitlines():
            key, sep, value = line.partition(":")
            if sep and key.strip():
                metadata[key.strip()] = value.strip()
    return metadata, body.strip()


def find_unicode_font() -> Path:
    """Tìm một TTF có sẵn trên máy để render tiếng Việt."""
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Không tìm thấy font Unicode (.ttf) để render tiếng Việt. "
        f"Đã thử: {', '.join(str(path) for path in FONT_CANDIDATES)}. "
        "Hãy thêm đường dẫn font của máy bạn vào FONT_CANDIDATES."
    )


def render_pdf(doc_id: str, metadata: dict, body: str, source: dict) -> Path:
    """Render một tài liệu nguồn ra PDF kèm khối trích dẫn nguồn."""
    from fpdf import FPDF

    font_path = find_unicode_font()
    filepath = DATA_DIR / f"{doc_id}.pdf"
    title = metadata.get("title") or source.get("title") or doc_id

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("body", "", str(font_path))

    pdf.set_font("body", size=14)
    pdf.multi_cell(0, 9, title, align="C")
    pdf.ln(4)

    # Khối nguồn nằm ngay trong tài liệu để citation truy ngược được tới URL.
    pdf.set_font("body", size=9)
    pdf.multi_cell(
        0,
        5,
        f"Nguồn: {source.get('source_url', 'n/a')}\n"
        f"Ngày thu thập: {source.get('retrieved_at', 'n/a')} | "
        f"Phiên bản: {source.get('document_version', 'n/a')} | "
        f"Quyền sử dụng: {source.get('license_or_permission', 'n/a')}",
    )
    pdf.ln(4)

    pdf.set_font("body", size=11)
    pdf.multi_cell(0, 7, body)

    pdf.output(str(filepath))
    print(f"Saved: {filepath.name} ({filepath.stat().st_size} bytes)")
    return filepath


def download_documents() -> None:
    """Dựng tài liệu chính sách vào data/landing/legal/ từ nguồn đã thu thập."""
    sources = load_sources()
    missing = [doc_id for doc_id in LEGAL_DOC_IDS if doc_id not in sources]
    if missing:
        raise KeyError(f"Thiếu trong sources.csv: {', '.join(missing)}")

    for doc_id in LEGAL_DOC_IDS:
        metadata, body = read_source_document(doc_id)
        render_pdf(doc_id, metadata, body, sources[doc_id])


if __name__ == "__main__":
    setup_directory()
    download_documents()
