"""Split PDF into separate pages."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from gs_pdf.engine import GsEngine

console = Console()
err_console = Console(stderr=True)


def cmd(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: str = typer.Argument(
        ..., help="Output pattern (use %%d for page number, e.g. 'page_%%d.pdf')"
    ),
    pages: str | None = typer.Option(
        None, "--pages", "-p", help="Page range e.g. '1-10' or '1,3,5-7'"
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Split a PDF into separate page files.

    Use %d in the output pattern for page numbering.
    Example: gs-pdf split input.pdf output_%d.pdf
    """
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = []

    if pages:
        parts = pages.replace(" ", "").split(",")
        first_part = parts[0]
        if "-" in first_part:
            f, l = first_part.split("-", 1)
            opts.append(f"-dFirstPage={f}")
            opts.append(f"-dLastPage={l}")
        else:
            opts.append(f"-dFirstPage={first_part}")
            opts.append(f"-dLastPage={first_part}")
        if len(parts) > 1:
            opts.append(f"-sPageList={pages}")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], output, opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)

    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Split into [bold]{output.replace('%d', '*')}[/bold]")
