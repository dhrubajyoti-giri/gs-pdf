"""PDF format conversion via Ghostscript output devices."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from gs_pdf.config import (
    GsConvertFormat,
    GsTextLayout,
    GsTiffCompression,
    device_for_format,
)
from gs_pdf.engine import GsEngine
from gs_pdf.util import detect_format_from_extension

console = Console()
err_console = Console(stderr=True)


def cmd(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input file"),
    output: Path = typer.Argument(..., help="Output file"),
    format: str | None = typer.Option(
        None, "--format", "-f", help="Output format (auto-detect from extension if omitted)"
    ),
    resolution: int = typer.Option(
        150, "--resolution", "-r", min=9, max=2400, help="Output resolution in DPI"
    ),
    pages: str | None = typer.Option(
        None, "--pages", "-p", help="Page range e.g. '1-10' or '1,3,5-7'"
    ),
    gray: bool = typer.Option(False, "--gray", help="Grayscale output"),
    mono: bool = typer.Option(False, "--mono", help="Monochrome (1-bit) output"),
    alpha: bool = typer.Option(False, "--alpha", help="Include alpha channel (PNG only)"),
    quality: int = typer.Option(
        90, "--quality", "-q", min=1, max=100, help="JPEG/JPEG2000 quality"
    ),
    tiff_compression: GsTiffCompression = typer.Option(
        GsTiffCompression.DEFLATE, "--tiff-compression",
        help="TIFF compression type",
    ),
    text_layout: GsTextLayout = typer.Option(
        GsTextLayout.PRESERVE, "--text-layout",
        help="Text extraction layout (text format only)",
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Convert PDF to images (PNG, JPEG, TIFF, BMP), PostScript, EPS, SVG, or text.

    Automatically detects output format from file extension.
    Use --format to override.
    """
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    # Determine format
    fmt_str: str = format or detect_format_from_extension(output) or "png"
    try:
        fmt = GsConvertFormat(fmt_str.lower())
    except ValueError:
        err_console.print(f"[red]Unsupported format: {fmt_str}[/red]")
        raise typer.Exit(1)

    device = device_for_format(fmt, gray=gray, mono=mono, alpha=alpha)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = [f"-r{resolution}"]

    if pages:
        parts = pages.replace(" ", "").split(",")
        if parts:
            first = parts[0]
            if "-" in first:
                f, l = first.split("-", 1)
                opts.append(f"-dFirstPage={f}")
                opts.append(f"-dLastPage={l}")
            else:
                opts.append(f"-dFirstPage={first}")
                opts.append(f"-dLastPage={first}")
            if len(parts) > 1:
                opts.append(f"-sPageList={pages}")

    if fmt in (GsConvertFormat.JPEG, GsConvertFormat.JP2):
        opts.append(f"-dJPEGQ={quality}")

    if fmt == GsConvertFormat.TIFF:
        comp_map = {
            GsTiffCompression.NONE: "none",
            GsTiffCompression.PACKBITS: "packbits",
            GsTiffCompression.DEFLATE: "deflate",
            GsTiffCompression.LZW: "lzw",
            GsTiffCompression.G3: "g3",
            GsTiffCompression.G4: "g4",
        }
        opts.append(f"-sTIFFCompression={comp_map[tiff_compression]}")

    if fmt == GsConvertFormat.TEXT:
        TEXT_LAYOUT_MAP = {
            GsTextLayout.PHYSICAL: 0,
            GsTextLayout.PRESERVE: 1,
            GsTextLayout.SIMPLE: 2,
            GsTextLayout.TABLE: 3,
        }
        opts.append(f"-dTextFormat={TEXT_LAYOUT_MAP[text_layout]}")

    # For image output, use %d pattern for multi-page
    output_str = str(output)
    if fmt in (GsConvertFormat.PNG, GsConvertFormat.JPEG, GsConvertFormat.TIFF,
               GsConvertFormat.BMP, GsConvertFormat.PNM, GsConvertFormat.PBM,
               GsConvertFormat.PGM, GsConvertFormat.PPM, GsConvertFormat.PCX,
               GsConvertFormat.JP2):
        if pages is None:
            output_str = str(output.parent / f"{output.stem}_%d{output.suffix}")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args(device, [input], output_str, opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)

    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Converted to [bold]{output}[/bold]")
