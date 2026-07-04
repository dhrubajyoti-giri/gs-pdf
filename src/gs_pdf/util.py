"""Shared utilities for gs-pdf commands."""

from __future__ import annotations

from pathlib import Path


def parse_page_range(spec: str, max_pages: int = 9999) -> tuple[int, int]:
    """Parse a page range string like '1-10' or '3' into (first, last)."""
    spec = spec.strip()
    if "-" in spec:
        parts = spec.split("-", 1)
        first = max(1, int(parts[0]))
        last = min(max_pages, int(parts[1]) if parts[1] else max_pages)
    else:
        n = int(spec)
        first, last = n, n
    return (first, last)


def parse_page_list(spec: str) -> list[int]:
    """Parse a page list like '1,3,5-7' into [1, 3, 5, 6, 7]."""
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return sorted(set(pages))


def format_file_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def detect_format_from_extension(path: Path) -> str | None:
    """Detect output format from file extension."""
    ext = path.suffix.lower()
    return {
        ".pdf": "pdf",
        ".png": "png",
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".tif": "tiff",
        ".tiff": "tiff",
        ".bmp": "bmp",
        ".ps": "ps",
        ".eps": "eps",
        ".svg": "svg",
        ".txt": "text",
        ".pnm": "pnm",
        ".pbm": "pbm",
        ".pgm": "pgm",
        ".ppm": "ppm",
        ".pcx": "pcx",
        ".jp2": "jp2",
    }.get(ext)


def output_path_with_pages(output: str, page: int) -> str:
    """Insert page number into output filename pattern."""
    if "%d" in output:
        return output % page
    p = Path(output)
    return str(p.parent / f"{p.stem}_{page}{p.suffix}")
