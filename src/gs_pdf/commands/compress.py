"""PDF compression via Ghostscript pdfwrite device."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from gs_pdf.config import GsCompatibilityLevel, GsImageFilter, GsQualityPreset
from gs_pdf.engine import GsEngine

app = typer.Typer(help="Reduce PDF file size using Ghostscript")
console = Console()
err_console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def compress(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output PDF file"),
    preset: GsQualityPreset = typer.Option(
        GsQualityPreset.DEFAULT, "--preset", help="Quality preset"
    ),
    resolution: int = typer.Option(
        150, "--resolution", min=72, max=2400, help="Output resolution in DPI"
    ),
    downsample_images: bool = typer.Option(
        True, "--downsample-images/--no-downsample-images",
        help="Downsample images above threshold",
    ),
    color_image_resolution: int = typer.Option(
        150, "--color-image-resolution", min=9, max=2400,
        help="Downsampling resolution for color images",
    ),
    gray_image_resolution: int = typer.Option(
        150, "--gray-image-resolution", min=9, max=2400,
        help="Downsampling resolution for gray images",
    ),
    mono_image_resolution: int = typer.Option(
        300, "--mono-image-resolution", min=9, max=2400,
        help="Downsampling resolution for monochrome images",
    ),
    color_image_filter: GsImageFilter = typer.Option(
        GsImageFilter.DCT, "--color-image-filter",
        help="Compression filter for color images",
    ),
    gray_image_filter: GsImageFilter = typer.Option(
        GsImageFilter.DCT, "--gray-image-filter",
        help="Compression filter for gray images",
    ),
    mono_image_filter: GsImageFilter = typer.Option(
        GsImageFilter.CCITT, "--mono-image-filter",
        help="Compression filter for monochrome images",
    ),
    auto_filter_color: bool = typer.Option(
        True, "--auto-filter-color/--no-auto-filter-color",
        help="Auto-select color image filter",
    ),
    auto_filter_gray: bool = typer.Option(
        True, "--auto-filter-gray/--no-auto-filter-gray",
        help="Auto-select gray image filter",
    ),
    auto_filter_mono: bool = typer.Option(
        True, "--auto-filter-mono/--no-auto-filter-mono",
        help="Auto-select monochrome image filter",
    ),
    embed_fonts: bool = typer.Option(
        True, "--embed-fonts/--no-embed-fonts",
        help="Embed all fonts",
    ),
    subset_fonts: bool = typer.Option(
        True, "--subset-fonts/--no-subset-fonts",
        help="Subset embedded fonts",
    ),
    compress_fonts: bool = typer.Option(
        True, "--compress-fonts/--no-compress-fonts",
        help="Compress font streams",
    ),
    compress_pages: bool = typer.Option(
        True, "--compress-pages/--no-compress-pages",
        help="Compress page content streams",
    ),
    linearize: bool = typer.Option(
        False, "--linearize/--no-linearize",
        help="Optimize for fast web viewing (PDF linearization)",
    ),
    detect_duplicates: bool = typer.Option(
        True, "--detect-duplicates/--no-detect-duplicates",
        help="Detect and merge duplicate images",
    ),
    preserve_metadata: bool = typer.Option(
        True, "--preserve-metadata/--no-preserve-metadata",
        help="Preserve document metadata",
    ),
    preserve_annotations: bool = typer.Option(
        True, "--preserve-annotations/--flatten-annotations",
        help="Preserve or flatten annotations",
    ),
    preserve_forms: bool = typer.Option(
        True, "--preserve-forms/--flatten-forms",
        help="Preserve or flatten form fields",
    ),
    color_conversion_strategy: str = typer.Option(
        "LeaveColorUnchanged", "--color-conversion-strategy",
        help="Color conversion strategy",
    ),
    compatibility_level: GsCompatibilityLevel = typer.Option(
        GsCompatibilityLevel.V1_7, "--compatibility-level",
        help="PDF version compatibility",
    ),
    grayscale: bool = typer.Option(
        False, "--grayscale/--no-grayscale",
        help="Convert to grayscale",
    ),
    lossless: bool = typer.Option(
        False, "--lossless/--no-lossless",
        help="Maximum quality, no downsampling, flate compression",
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Compress a PDF file using Ghostscript's pdfwrite device.

    Supports quality presets, fine-grained image downsampling control,
    font embedding/subsetting, metadata preservation, and more.
    """
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    # Build options dict for pdfwrite device
    opts: list[str] = [
        f"-dPDFSETTINGS=/{preset.value}",
        f"-r{resolution}",
    ]

    # Image downsampling
    if downsample_images or lossless:
        opts.append(f"-dDownsampleColorImages={str(not lossless).lower()}")
        opts.append(f"-dDownsampleGrayImages={str(not lossless).lower()}")
        opts.append(f"-dDownsampleMonoImages={str(not lossless).lower()}")
        if not lossless:
            opts.append(f"-dColorImageResolution={color_image_resolution}")
            opts.append(f"-dGrayImageResolution={gray_image_resolution}")
            opts.append(f"-dMonoImageResolution={mono_image_resolution}")

    # Image filters
    if lossless:
        opts.append("-dColorImageFilter=/FlateEncode")
        opts.append("-dGrayImageFilter=/FlateEncode")
        opts.append("-dMonoImageFilter=/CCITTFaxEncode")
    else:
        opts.append(f"-dColorImageFilter=/{color_image_filter.value.upper()}Encode")
        opts.append(f"-dGrayImageFilter=/{gray_image_filter.value.upper()}Encode")
        opts.append(f"-dMonoImageFilter=/{mono_image_filter.value.upper()}Encode")

    # Auto filter
    opts.append(f"-dAutoFilterColorImages={str(auto_filter_color).lower()}")
    opts.append(f"-dAutoFilterGrayImages={str(auto_filter_gray).lower()}")
    opts.append(f"-dAutoFilterMonoImages={str(auto_filter_mono).lower()}")

    # Fonts
    opts.append(f"-dEmbedAllFonts={str(embed_fonts).lower()}")
    opts.append(f"-dSubsetFonts={str(subset_fonts).lower()}")
    opts.append(f"-dCompressFonts={str(compress_fonts).lower()}")

    # Pages
    opts.append(f"-dCompressPages={str(compress_pages).lower()}")

    # Optimization
    opts.append(f"-dDetectDuplicateImages={str(detect_duplicates).lower()}")
    if linearize:
        opts.append("-dOptimize=true")

    # Preservation
    opts.append(f"-dPreserveMetadata={str(preserve_metadata).lower()}")
    opts.append(f"-dPreserveAnnots={str(preserve_annotations).lower()}")
    opts.append(f"-dPreserveForm={str(preserve_forms).lower()}")

    # Color
    opts.append(f"-sColorConversionStrategy={color_conversion_strategy}")
    opts.append(f"-dCompatibilityLevel={compatibility_level.value}")
    if grayscale:
        opts.append("-sProcessColorModel=DeviceGray")
        opts.append("-dColorConversionStrategy=/Gray")

    # Apply lossless overrides last
    if lossless:
        opts.append("-dColorImageDownsampleType=/Bicubic")
        opts.append("-dGrayImageDownsampleType=/Bicubic")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)

    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    # Show compression summary
    if output.exists():
        orig_size = input.stat().st_size
        new_size = output.stat().st_size
        ratio = (1 - new_size / orig_size) * 100 if orig_size > 0 else 0

        table = Table(title="Compression Result")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Original size", f"{orig_size / 1024:.1f} KB")
        table.add_row("Compressed size", f"{new_size / 1024:.1f} KB")
        table.add_row("Reduction", f"{ratio:.1f}%")
        console.print(table)
