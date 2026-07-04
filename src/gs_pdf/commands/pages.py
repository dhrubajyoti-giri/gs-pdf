"""Page geometry operations: rotate, crop, resize, select."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from gs_pdf.engine import GsEngine

app = typer.Typer(help="Page operations: rotate, crop, resize, select")
console = Console()
err_console = Console(stderr=True)


@app.callback()
def pages() -> None:
    """Page geometry operations."""


@app.command("rotate")
def pages_rotate(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output PDF file"),
    angle: int = typer.Option(
        90, "--angle", help="Rotation angle: 90, 180, or 270"
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Rotate pages by 90, 180, or 270 degrees."""
    if angle not in (90, 180, 270):
        err_console.print("[red]Angle must be 90, 180, or 270[/red]")
        raise typer.Exit(1)

    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = [f"-dRotatePages={angle}"]
    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Rotated pages by {angle}° -> [bold]{output}[/bold]")


@app.command("crop")
def pages_crop(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output PDF file"),
    bbox: str = typer.Option(
        ..., "--bbox", help="Bounding box: 'llx lly urx ury' in points"
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Crop pages to a bounding box."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    coords = bbox.split()
    if len(coords) != 4:
        err_console.print("[red]--bbox requires 4 values: llx lly urx ury[/red]")
        raise typer.Exit(1)

    opts: list[str] = [
        "-dUseCropBox",
        f"-dDEVICEWIDTHPOINTS={float(coords[2]) - float(coords[0])}",
        f"-dDEVICEHEIGHTPOINTS={float(coords[3]) - float(coords[1])}",
        f"-dPageOffset={coords[0]} {coords[1]}",
    ]

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Cropped to {bbox} -> [bold]{output}[/bold]")


PAGE_SIZES: dict[str, tuple[int, int]] = {
    "a3": (842, 1191),
    "a4": (595, 842),
    "a5": (420, 595),
    "letter": (612, 792),
    "legal": (612, 1008),
    "tabloid": (792, 1224),
    "executive": (522, 756),
    "b5": (499, 709),
}


@app.command("resize")
def pages_resize(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output PDF file"),
    fit: str = typer.Option(
        ..., "--fit", help="Page size: a3, a4, letter, legal, tabloid, or WxH in points"
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Resize pages to a standard or custom size."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    size = fit.lower()
    if size in PAGE_SIZES:
        w, h = PAGE_SIZES[size]
        opts = [f"-sPAPERSIZE={size}"]
    elif "x" in size:
        parts = size.split("x")
        try:
            w = int(parts[0])
            h = int(parts[1])
        except (ValueError, IndexError):
            err_console.print("[red]Custom size must be WxH (e.g. '600x800')[/red]")
            raise typer.Exit(1)
        opts = [f"-g{w}x{h}", f"-dDEVICEWIDTHPOINTS={w}", f"-dDEVICEHEIGHTPOINTS={h}"]
    else:
        err_console.print(f"[red]Unknown page size: {fit}[/red]")
        raise typer.Exit(1)

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Resized to {fit} -> [bold]{output}[/bold]")


@app.command("select")
def pages_select(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output PDF file"),
    pages: str = typer.Option(
        ..., "--pages", "-p", help="Page range e.g. '1,3,5-7' or '1-10'"
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Select specific pages from the PDF."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = [f"-sPageList={pages}"]
    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Selected pages {pages} -> [bold]{output}[/bold]")
