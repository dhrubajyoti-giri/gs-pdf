"""Raw Ghostscript argument passthrough."""

from __future__ import annotations

import typer
from rich.console import Console

from gs_pdf.engine import GsEngine

app = typer.Typer(help="Pass raw arguments directly to Ghostscript")
console = Console()
err_console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def raw(
    ctx: typer.Context,
    args: list[str] = typer.Argument(
        ..., help="Raw Ghostscript arguments (everything after 'raw' is passed through)"
    ),
) -> None:
    """Pass arbitrary arguments directly to Ghostscript.

    Example:
        gs-pdf raw -sDEVICE=pdfwrite -dPDFSETTINGS=/screen input.pdf -o out.pdf
    """
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    if not args:
        err_console.print("[red]No arguments provided to pass to Ghostscript.[/red]")
        err_console.print("Example: gs-pdf raw -sDEVICE=pdfwrite input.pdf -o output.pdf")
        raise typer.Exit(1)

    engine = GsEngine(gs_path=gs_path, timeout=timeout)

    # Use the args as-is, just prepend the gs path
    gs_binary = engine._find_gs()
    full_args = [gs_binary] + args

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(full_args)}[/dim]")

    result = engine.execute(full_args)

    if result.stdout:
        console.print(result.stdout)
    if result.stderr:
        err_console.print(result.stderr)

    if result.exit_code != 0:
        raise typer.Exit(result.exit_code)
