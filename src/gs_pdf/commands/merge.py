"""Merge multiple PDFs into one."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from gs_pdf.engine import GsEngine

console = Console()
err_console = Console(stderr=True)


def cmd(
    ctx: typer.Context,
    inputs: list[Path] = typer.Argument(..., exists=True, help="Input PDF files"),
    output: Path = typer.Argument(..., help="Output PDF file"),
    first_page: int | None = typer.Option(
        None, "--first-page", help="First page to include",
    ),
    last_page: int | None = typer.Option(
        None, "--last-page", help="Last page to include",
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Merge multiple PDF files into a single PDF document."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = []
    if first_page is not None:
        opts.append(f"-dFirstPage={first_page}")
    if last_page is not None:
        opts.append(f"-dLastPage={last_page}")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", inputs, str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)

    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Merged [bold]{len(inputs)}[/bold] PDFs into [bold]{output}[/bold]")
