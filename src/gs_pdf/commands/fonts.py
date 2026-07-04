"""Font introspection and embedding."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from gs_pdf.engine import GsEngine

app = typer.Typer(help="List, embed, and subset fonts")
console = Console()
err_console = Console(stderr=True)


@app.callback()
def fonts() -> None:
    """Font operations."""


@app.command("list")
def fonts_list(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
) -> None:
    """List fonts used in a PDF document."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    engine = GsEngine(gs_path=gs_path, timeout=timeout)

    # Use pdfwrite with verbose to get font info
    args = engine.build_args("pdfwrite", [input], "/dev/null", ["-dPDFINFO"])
    result = engine.execute(args)

    if result.exit_code != 0 and result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    # Parse font info from stderr
    fonts_found: list[str] = []
    for line in result.stderr.split("\n"):
        if "font" in line.lower() or "Font" in line:
            fonts_found.append(line.strip())

    if not fonts_found:
        # Fall back to showing available system fonts
        args2 = engine.build_args("pdfwrite", [input], "/dev/null", [])
        result2 = engine.execute(args2)
        for line in result2.stderr.split("\n"):
            if "Font" in line or "font" in line:
                fonts_found.append(line.strip())

    if fonts_found:
        table = Table(title=f"Fonts in: {input.name}")
        table.add_column("Font Info", style="cyan")
        for font in fonts_found:
            cleaned = font.replace("%%", "").replace("[", "").replace("]", "").strip()
            if cleaned:
                table.add_row(cleaned)
        console.print(table)
    else:
        console.print("[yellow]No font information available.[/yellow]")
        console.print("[dim]Try: gs-pdf inspect --verbose input.pdf[/dim]")


@app.command("embed")
def fonts_embed(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output PDF file"),
    font_path: list[Path] = typer.Option(
        [], "--font-path", exists=True,
        help="Additional font directories (repeatable)",
    ),
    always_embed: str | None = typer.Option(
        None, "--always-embed", help="Comma-separated font names to always embed",
    ),
    never_embed: str | None = typer.Option(
        None, "--never-embed", help="Comma-separated font names to never embed",
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Embed missing fonts into a PDF."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = [
        "-dEmbedAllFonts=true",
        "-dSubsetFonts=false",
    ]

    if always_embed:
        opts.append(f"-sAlwaysEmbed={always_embed}")
    if never_embed:
        opts.append(f"-sNeverEmbed={never_embed}")
    for fp in font_path:
        opts.append(f"-sFONTPATH={fp}")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Fonts embedded -> [bold]{output}[/bold]")


@app.command("subset")
def fonts_subset(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output PDF file"),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Subset all embedded fonts to reduce file size."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = [
        "-dEmbedAllFonts=true",
        "-dSubsetFonts=true",
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

    console.print(f"[green]✓[/green] Fonts subset -> [bold]{output}[/bold]")
