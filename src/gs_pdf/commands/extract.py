"""Extract text, images, or fonts from PDF."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from gs_pdf.config import GsTextLayout
from gs_pdf.engine import GsEngine

app = typer.Typer(help="Extract text, images, or fonts from PDF")
console = Console()
err_console = Console(stderr=True)


@app.callback()
def extract() -> None:
    """Extract content from PDF files."""


@app.command("text")
def extract_text(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output text file"),
    encoding: str = typer.Option(
        "UTF-8", "--encoding", help="Output text encoding"
    ),
    layout: GsTextLayout = typer.Option(
        GsTextLayout.PRESERVE, "--layout",
        help="Text extraction layout mode",
    ),
    pages: str | None = typer.Option(
        None, "--pages", "-p", help="Page range e.g. '1-10'"
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Extract text content from PDF pages."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = [
        f"-sTextFormat=/{layout.value}",
        f"-sOutputEncoding={encoding}",
    ]
    if pages:
        opts.append(f"-sPageList={pages}")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("txtwrite", [input], str(output), opts + extra_args)

    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Text extracted -> [bold]{output}[/bold]")


@app.command("images")
def extract_images(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output_dir: Path = typer.Argument(..., help="Output directory for images"),
    format: str = typer.Option(
        "png", "--format", help="Image format: png, jpeg, tiff"
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Extract images from PDF pages using Ghostscript rendering."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    output_dir.mkdir(parents=True, exist_ok=True)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    device_map = {"png": "png16m", "jpeg": "jpeg", "tiff": "tiff24nc"}
    device = device_map.get(format, "png16m")

    output_pattern = str(output_dir / f"page_%d.{format}")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args(device, [input], output_pattern, extra_args)

    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Images saved to [bold]{output_dir}[/bold]")


@app.command("fonts")
def extract_fonts(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output_dir: Path = typer.Argument(..., help="Output directory for fonts"),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Extract fonts used in the PDF (dumps as output images/font data)."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    output_dir.mkdir(parents=True, exist_ok=True)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    # Use pdfwrite to preserve fonts in output
    opts: list[str] = ["-dPreserveFonts=true"]
    output_file = output_dir / "fonts.pdf"

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output_file), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Font data extracted to [bold]{output_dir}[/bold]")
