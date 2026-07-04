"""PDF inspection and metadata analysis."""

from __future__ import annotations

import json
import re
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from gs_pdf.engine import GsEngine
from gs_pdf.util import format_file_size

console = Console()
err_console = Console(stderr=True)


def _parse_pdf_info(stderr: str) -> dict[str, str]:
    """Parse PDF metadata from Ghostscript stderr output."""
    info: dict[str, str] = {}
    patterns = [
        (r"Title:\s*(.+)", "Title"),
        (r"Author:\s*(.+)", "Author"),
        (r"Subject:\s*(.+)", "Subject"),
        (r"Keywords:\s*(.+)", "Keywords"),
        (r"Creator:\s*(.+)", "Creator"),
        (r"Producer:\s*(.+)", "Producer"),
        (r"Pages:\s*(\d+)", "Pages"),
        (r"PDF version:\s*(.+)", "PDF Version"),
    ]
    for pattern, key in patterns:
        m = re.search(pattern, stderr, re.IGNORECASE)
        if m:
            info[key] = m.group(1).strip()
    return info


def _parse_ink_coverage(stdout: str) -> list[dict[str, float]]:
    """Parse ink coverage data from inkcov device output."""
    pages: list[dict[str, float]] = []
    for line in stdout.split("\n"):
        parts = line.strip().split()
        if len(parts) >= 4:
            try:
                pages.append({
                    "cyan": float(parts[0]),
                    "magenta": float(parts[1]),
                    "yellow": float(parts[2]),
                    "black": float(parts[3]),
                })
            except ValueError:
                continue
    return pages


def _parse_bbox(stdout: str) -> list[dict[str, float]]:
    """Parse bounding box data from bbox device output."""
    boxes: list[dict[str, float]] = []
    for line in stdout.split("\n"):
        m = re.search(
            r"%%BoundingBox:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", line
        )
        if m:
            boxes.append({
                "llx": float(m.group(1)),
                "lly": float(m.group(2)),
                "urx": float(m.group(3)),
                "ury": float(m.group(4)),
            })
    return boxes


def cmd(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed information"
    ),
    ink: bool = typer.Option(
        False, "--ink", help="Show per-page ink coverage"
    ),
    bbox: bool = typer.Option(
        False, "--bbox", help="Show per-page bounding boxes"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON"
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Display PDF document metadata, font usage, and structural information."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    # Get PDF metadata using pdfwrite with -dPDFINFO
    info_args = engine.build_args(
        "pdfwrite", [input], "/dev/null",
        ["-dPDFINFO", "-dNOPROMPT"] + extra_args,
    )
    info_result = engine.execute(info_args)
    metadata = _parse_pdf_info(info_result.stderr)

    # File info
    file_size = input.stat().st_size
    metadata["File Size"] = format_file_size(file_size)

    # Ink coverage
    ink_data: list[dict[str, float]] = []
    if ink:
        ink_args = engine.build_args(
            "inkcov", [input], "/dev/null", extra_args,
        )
        ink_result = engine.execute(ink_args)
        ink_data = _parse_ink_coverage(ink_result.stdout)

    # Bounding boxes
    bbox_data: list[dict[str, float]] = []
    if bbox:
        bbox_args = engine.build_args(
            "bbox", [input], "/dev/null", extra_args,
        )
        bbox_result = engine.execute(bbox_args)
        bbox_data = _parse_bbox(bbox_result.stderr)

    if json_output:
        output: dict[str, object] = {
            "file": str(input),
            "metadata": metadata,
        }
        if ink:
            output["ink_coverage"] = ink_data
        if bbox:
            output["bounding_boxes"] = bbox_data
        console.print(json.dumps(output, indent=2))
        return

    # Display as tables
    table = Table(title=f"PDF Info: {input.name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    for key, value in metadata.items():
        table.add_row(key, value)
    console.print(table)

    if ink_data:
        ink_table = Table(title="Ink Coverage (%)")
        ink_table.add_column("Page", style="cyan")
        for key in ("cyan", "magenta", "yellow", "black"):
            ink_table.add_column(key.capitalize(), style="green")
        for i, page in enumerate(ink_data, 1):
            ink_table.add_row(
                str(i),
                f"{page['cyan']:.1%}",
                f"{page['magenta']:.1%}",
                f"{page['yellow']:.1%}",
                f"{page['black']:.1%}",
            )
        console.print(ink_table)

    if bbox_data:
        bbox_table = Table(title="Bounding Boxes (points)")
        bbox_table.add_column("Page", style="cyan")
        bbox_table.add_column("LLx", style="green")
        bbox_table.add_column("LLy", style="green")
        bbox_table.add_column("URx", style="green")
        bbox_table.add_column("URy", style="green")
        for i, box in enumerate(bbox_data, 1):
            bbox_table.add_row(
                str(i),
                f"{box['llx']:.0f}",
                f"{box['lly']:.0f}",
                f"{box['urx']:.0f}",
                f"{box['ury']:.0f}",
            )
        console.print(bbox_table)
