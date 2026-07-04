"""PDF/A archival format conversion."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from gs_pdf.config import GsPdfALevel
from gs_pdf.engine import GsEngine

console = Console()
err_console = Console(stderr=True)

OUTPUT_INTENT_PROFILES: dict[str, str] = {
    "sRGB": "sRGB IEC61966-2.1",
    "ISOcoated": "ISO Coated v2 300% (ECI)",
    "eciRGB": "eciRGB v2",
}


def cmd(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output PDF/A file"),
    level: int = typer.Option(
        2, "--level", help="PDF/A conformance level (1, 2, or 3)"
    ),
    output_intent: str = typer.Option(
        "sRGB", "--output-intent",
        help="Output intent profile (sRGB, ISOcoated, eciRGB, or path to .icc file)",
    ),
    color_conversion_strategy: str = typer.Option(
        "UseDeviceIndependentColor", "--color-conversion-strategy",
        help="Color conversion strategy for PDF/A",
    ),
    policy: int = typer.Option(
        1, "--policy", help="PDFACompatibilityPolicy (0=warn, 1=error, 2=auto-fix)",
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Convert a PDF to PDF/A-1b, PDF/A-2b, or PDF/A-3b archival format.

    Requires an ICC output intent profile for color fidelity.
    """
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    opts: list[str] = [
        "-dPDFA",
        f"-dPDFACompatibilityPolicy={policy}",
        f"-sColorConversionStrategy={color_conversion_strategy}",
    ]

    pdfa_level = GsPdfALevel(level) if level in (1, 2, 3) else GsPdfALevel.PDFA_2
    if pdfa_level.value > 1:
        opts.append(f"-dPDFA={pdfa_level.value}")

    # Resolve output intent profile
    intent_file: str = output_intent
    if output_intent in OUTPUT_INTENT_PROFILES:
        intent_file = OUTPUT_INTENT_PROFILES[output_intent]

    opts.append("-dPDFAOutputIntent=/default")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Converted to PDF/A-{pdfa_level.value}b -> [bold]{output}[/bold]")
