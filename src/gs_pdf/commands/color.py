"""PDF color space conversion."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from gs_pdf.config import GsColorModel, GsRenderingIntent
from gs_pdf.engine import GsEngine

app = typer.Typer(help="Convert PDF color space")
console = Console()
err_console = Console(stderr=True)


COLOR_STRATEGIES: dict[GsColorModel, str] = {
    GsColorModel.RGB: "sRGB",
    GsColorModel.CMYK: "CMYK",
    GsColorModel.GRAY: "Gray",
}


@app.callback(invoke_without_command=True)
def color(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output PDF file"),
    to: GsColorModel = typer.Option(
        GsColorModel.GRAY, "--to", help="Target color space"
    ),
    color_conversion_strategy: str = typer.Option(
        "LeaveColorUnchanged", "--color-conversion-strategy",
        help="Color conversion strategy",
    ),
    icc_profile: Path | None = typer.Option(
        None, "--icc-profile", exists=True,
        help="ICC profile file for output intent",
    ),
    rendering_intent: GsRenderingIntent = typer.Option(
        GsRenderingIntent.RELATIVE_COLORIMETRIC, "--rendering-intent",
        help="Rendering intent for color conversion",
    ),
    preserve_overprint: bool = typer.Option(
        True, "--preserve-overprint/--simulate-overprint",
        help="Preserve or simulate overprint",
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Convert PDF between RGB, CMYK, and Grayscale color spaces."""
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = [
        f"-sColorConversionStrategy={color_conversion_strategy}",
        f"-dRenderIntent={rendering_intent.value}",
        f"-dPreserveOverprint={str(preserve_overprint).lower()}",
    ]

    if to != GsColorModel.UNCHANGED:
        strategy = COLOR_STRATEGIES.get(to, "LeaveColorUnchanged")
        if color_conversion_strategy == "LeaveColorUnchanged":
            opts.append(f"-sColorConversionStrategy={strategy}")
        # Set the process color model
        pm = to.value.upper()
        opts.append(f"-sProcessColorModel=Device{pm}")

    if icc_profile:
        opts.append(f"-sOutputICCProfile={icc_profile}")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Converted to {to.value.upper()} -> [bold]{output}[/bold]")
