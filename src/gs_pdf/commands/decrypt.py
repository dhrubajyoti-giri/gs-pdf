"""PDF decryption via Ghostscript."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from gs_pdf.engine import GsEngine

app = typer.Typer(help="Remove password protection from PDF")
console = Console()
err_console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def decrypt(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output decrypted PDF file"),
    password: str | None = typer.Option(
        None, "--password", prompt=True, hide_input=True,
        help="Password to decrypt the PDF",
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Remove password protection from a PDF.

    Ghostscript will prompt for a password if not provided.
    """
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = []
    if password:
        opts.append(f"-sPDFPassword={password}")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)

    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Decrypted [bold]{output}[/bold]")
