"""PDF compression via Ghostscript pdfwrite device."""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from gs_pdf.config import GsCompatibilityLevel, GsImageFilter, GsQualityPreset
from gs_pdf.engine import GsEngine

console = Console()
err_console = Console(stderr=True)


def _parse_size(value: str) -> int:
    """Parse a human-readable size string (e.g. '500KB', '2MB', '1.5MB') into bytes."""
    value = value.strip().upper()
    m = re.match(r"^([\d.]+)\s*(KB|MB|B)?$", value)
    if not m:
        raise typer.BadParameter(
            f"Invalid size format: '{value}'. Use e.g. '500KB', '2MB', '1048576B'."
        )
    num = float(m.group(1))
    unit = m.group(2) or "B"
    multipliers = {"B": 1, "KB": 1024, "MB": 1024 * 1024}
    return int(num * multipliers[unit])


def _try_compress(
    engine: GsEngine,
    input_path: Path,
    output_path: Path,
    opts: list[str],
) -> int | None:
    """Run Ghostscript and return output file size on success, None on failure."""
    args = engine.build_args("pdfwrite", [input_path], str(output_path), opts)
    result = engine.execute(args)
    if result.exit_code == 0 and output_path.exists():
        return output_path.stat().st_size
    return None


def _find_for_target(
    engine: GsEngine,
    input_path: Path,
    target_bytes: int,
    extra_args: list[str],
) -> tuple[list[str], int | None]:
    """Iterate compression presets to find settings that fit under target_bytes.

    Returns (best_opts, best_size) — the strongest settings that produce
    output ≤ target.  If nothing fits, returns the smallest output found.
    """
    tiers: list[tuple[GsQualityPreset, list[int]]] = [
        (GsQualityPreset.SCREEN,  [72, 100, 150, 200]),
        (GsQualityPreset.EBOOK,   [72, 100, 150, 200]),
        (GsQualityPreset.DEFAULT, [100, 150, 200, 300]),
        (GsQualityPreset.PRINTER, [150, 200, 300]),
        (GsQualityPreset.PREPRESS,[150, 200, 300]),
    ]

    tmpdir = Path(tempfile.mkdtemp(prefix="gs_pdf_size_"))
    best_opts: list[str] | None = None
    best_size: int | None = None

    try:
        for preset, resolutions in tiers:
            for res in resolutions:
                opts: list[str] = [
                    f"-dPDFSETTINGS=/{preset.value}",
                    f"-r{res}",
                    "-dDownsampleColorImages=true",
                    "-dDownsampleGrayImages=true",
                    "-dDownsampleMonoImages=true",
                    "-dEmbedAllFonts=true",
                    "-dSubsetFonts=true",
                    "-dCompressFonts=true",
                    "-dCompressPages=true",
                    "-dDetectDuplicateImages=true",
                ] + extra_args

                out = tmpdir / f"{preset.value}_{res}.pdf"
                size = _try_compress(engine, input_path, out, opts)

                if size is None:
                    continue

                if best_size is None or size < best_size:
                    best_opts = opts
                    best_size = size

                if size <= target_bytes:
                    return (opts, size)

        return (best_opts or [], best_size)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _compress_to_target(
    gs_path: str,
    timeout: int,
    input: Path,
    output: Path,
    target_size: str,
    extra_args: list[str],
    ctx: typer.Context,
) -> None:
    """Iterate compression presets to hit a target file size."""
    target_bytes = _parse_size(target_size)
    input_size = input.stat().st_size

    if target_bytes >= input_size:
        console.print(
            f"[yellow]Target size ({target_size}) is >= original size "
            f"({input_size / 1024:.1f} KB). Copying without compression.[/yellow]"
        )
        shutil.copy2(input, output)
        return

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    opts, actual_size = _find_for_target(engine, input, target_bytes, extra_args)

    if actual_size is None:
        err_console.print("[red]Could not produce compressed output.[/red]")
        raise typer.Exit(1)

    args = engine.build_args("pdfwrite", [input], str(output), opts)
    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")
    result = engine.execute(args)
    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    if not output.exists():
        err_console.print("[red]Output file not created.[/red]")
        raise typer.Exit(1)

    new_size = output.stat().st_size
    ratio = (1 - new_size / input_size) * 100

    table = Table(title="Compression Result")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Original size", f"{input_size / 1024:.1f} KB")
    table.add_row("Target size", target_size)
    table.add_row("Compressed size", f"{new_size / 1024:.1f} KB")
    table.add_row("Reduction", f"{ratio:.1f}%")
    if new_size > target_bytes:
        table.add_row(
            "Note",
            f"[yellow]Smallest achievable: {new_size / 1024:.1f} KB "
            f"(try a larger target)[/yellow]",
        )
    else:
        table.add_row("Target met", "[green]Yes[/green]")
    console.print(table)


def cmd(
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
    target_size: str | None = typer.Option(
        None, "--target-size",
        help="Target output size, e.g. '500KB', '2MB'. Iterates presets to fit.",
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

    if target_size is not None:
        _compress_to_target(gs_path, timeout, input, output, target_size, extra_args, ctx)
        return

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
    GS_FILTER_NAMES: dict[GsImageFilter, str] = {
        GsImageFilter.DCT: "DCTEncode",
        GsImageFilter.FLATE: "FlateEncode",
        GsImageFilter.JPX: "JPXEncode",
        GsImageFilter.CCITT: "CCITTFaxEncode",
    }

    if lossless:
        opts.append("-dColorImageFilter=/FlateEncode")
        opts.append("-dGrayImageFilter=/FlateEncode")
        opts.append("-dMonoImageFilter=/CCITTFaxEncode")
    else:
        opts.append(f"-dColorImageFilter=/{GS_FILTER_NAMES[color_image_filter]}")
        opts.append(f"-dGrayImageFilter=/{GS_FILTER_NAMES[gray_image_filter]}")
        opts.append(f"-dMonoImageFilter=/{GS_FILTER_NAMES[mono_image_filter]}")

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
