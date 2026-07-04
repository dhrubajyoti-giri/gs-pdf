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


GS_FILTER_NAMES: dict[GsImageFilter, str] = {
    GsImageFilter.DCT: "DCTEncode",
    GsImageFilter.FLATE: "FlateEncode",
    GsImageFilter.JPX: "JPXEncode",
    GsImageFilter.CCITT: "CCITTFaxEncode",
}


def _build_standard_opts(
    preset: GsQualityPreset,
    resolution: int,
    jpeg_quality: int | None,
    color_image_resolution: int,
    gray_image_resolution: int,
    mono_image_resolution: int,
    color_image_filter: GsImageFilter,
    gray_image_filter: GsImageFilter,
    mono_image_filter: GsImageFilter,
    auto_filter_color: bool,
    auto_filter_gray: bool,
    auto_filter_mono: bool,
    embed_fonts: bool,
    subset_fonts: bool,
    compress_fonts: bool,
    compress_pages: bool,
    linearize: bool,
    detect_duplicates: bool,
    preserve_metadata: bool,
    preserve_annotations: bool,
    preserve_forms: bool,
    color_conversion_strategy: str,
    compatibility_level: GsCompatibilityLevel,
    grayscale: bool,
    lossless: bool,
    downsample_images: bool,
    extra_args: list[str],
) -> list[str]:
    """Build standard Ghostscript pdfwrite options matching the compress command defaults."""
    opts: list[str] = [
        f"-dPDFSETTINGS=/{preset.value}",
        f"-r{resolution}",
    ]

    if jpeg_quality is not None:
        opts.append(f"-dJPEGQ={jpeg_quality}")

    if downsample_images or lossless:
        opts.append(f"-dDownsampleColorImages={str(not lossless).lower()}")
        opts.append(f"-dDownsampleGrayImages={str(not lossless).lower()}")
        opts.append(f"-dDownsampleMonoImages={str(not lossless).lower()}")
        if not lossless:
            opts.append(f"-dColorImageResolution={color_image_resolution}")
            opts.append(f"-dGrayImageResolution={gray_image_resolution}")
            opts.append(f"-dMonoImageResolution={mono_image_resolution}")

    if lossless:
        opts.append("-dColorImageFilter=/FlateEncode")
        opts.append("-dGrayImageFilter=/FlateEncode")
        opts.append("-dMonoImageFilter=/CCITTFaxEncode")
    else:
        opts.append(f"-dColorImageFilter=/{GS_FILTER_NAMES[color_image_filter]}")
        opts.append(f"-dGrayImageFilter=/{GS_FILTER_NAMES[gray_image_filter]}")
        opts.append(f"-dMonoImageFilter=/{GS_FILTER_NAMES[mono_image_filter]}")

    opts.append(f"-dAutoFilterColorImages={str(auto_filter_color).lower()}")
    opts.append(f"-dAutoFilterGrayImages={str(auto_filter_gray).lower()}")
    opts.append(f"-dAutoFilterMonoImages={str(auto_filter_mono).lower()}")
    opts.append(f"-dEmbedAllFonts={str(embed_fonts).lower()}")
    opts.append(f"-dSubsetFonts={str(subset_fonts).lower()}")
    opts.append(f"-dCompressFonts={str(compress_fonts).lower()}")
    opts.append(f"-dCompressPages={str(compress_pages).lower()}")
    opts.append(f"-dDetectDuplicateImages={str(detect_duplicates).lower()}")
    if linearize:
        opts.append("-dOptimize=true")
    opts.append(f"-dPreserveMetadata={str(preserve_metadata).lower()}")
    opts.append(f"-dPreserveAnnots={str(preserve_annotations).lower()}")
    opts.append(f"-dPreserveForm={str(preserve_forms).lower()}")
    opts.append(f"-sColorConversionStrategy={color_conversion_strategy}")
    opts.append(f"-dCompatibilityLevel={compatibility_level.value}")
    if grayscale:
        opts.append("-sProcessColorModel=DeviceGray")
        opts.append("-dColorConversionStrategy=/Gray")
    if lossless:
        opts.append("-dColorImageDownsampleType=/Bicubic")
        opts.append("-dGrayImageDownsampleType=/Bicubic")

    return opts + extra_args


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


def _build_target_opts(jpeg_quality: int, resolution: int, extra_args: list[str]) -> list[str]:
    """Build compress options for a given JPEG quality and resolution.

    Uses prepress preset (gentlest) without forced downsampling.
    JPEG quality is the primary size control, resolution fine-tunes.
    """
    return _build_standard_opts(
        preset=GsQualityPreset.PREPRESS,
        resolution=resolution,
        jpeg_quality=jpeg_quality,
        color_image_resolution=resolution,
        gray_image_resolution=resolution,
        mono_image_resolution=max(resolution, 300),
        color_image_filter=GsImageFilter.DCT,
        gray_image_filter=GsImageFilter.DCT,
        mono_image_filter=GsImageFilter.CCITT,
        auto_filter_color=True,
        auto_filter_gray=True,
        auto_filter_mono=True,
        embed_fonts=True,
        subset_fonts=True,
        compress_fonts=True,
        compress_pages=True,
        linearize=False,
        detect_duplicates=True,
        preserve_metadata=True,
        preserve_annotations=True,
        preserve_forms=True,
        color_conversion_strategy="LeaveColorUnchanged",
        compatibility_level=GsCompatibilityLevel.V1_7,
        grayscale=False,
        lossless=False,
        downsample_images=False,
        extra_args=extra_args,
    )


def _find_for_target(
    engine: GsEngine,
    input_path: Path,
    target_bytes: int,
    extra_args: list[str],
) -> tuple[list[str], int | None]:
    """Two-stage search: binary-search JPEGQ, then fine-tune with resolution.

    Stage 1: Binary search -dJPEGQ (1-100) at default resolution.
    Stage 2: Try best JPEGQ at multiple resolutions for closest match.
    Returns settings closest to target.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="gs_pdf_size_"))
    TARGET_TOLERANCE = int(target_bytes * 0.03)

    def _try(jq: int, res: int) -> tuple[int, list[str]] | None:
        """Try a (jpegq, resolution) combo, return (size, opts) or None."""
        opts = _build_target_opts(jq, res, extra_args)
        out = tmpdir / f"q{jq}_r{res}.pdf"
        size = _try_compress(engine, input_path, out, opts)
        if size is not None:
            return size, opts
        return None

    def _best_of(candidates: list[tuple[int, int]]) -> tuple[int, int, int, list[str]]:
        """From list of (jpegq, res), return (jq, res, size, opts) closest to target."""
        best_jq, best_res, best_size, best_opts = 0, 0, 0, []
        for jq, res in candidates:
            result = _try(jq, res)
            if result is None:
                continue
            size, opts = result
            if best_size == 0 or abs(size - target_bytes) < abs(best_size - target_bytes):
                best_jq, best_res, best_size, best_opts = jq, res, size, opts
        return best_jq, best_res, best_size, best_opts

    try:
        # Stage 1: Binary search JPEGQ at resolution=150
        lo, hi = 1, 100
        for _ in range(10):
            mid = (lo + hi) // 2
            result = _try(mid, 150)
            if result is None:
                for c in (mid - 5, mid + 5, lo, hi):
                    r = _try(c, 150)
                    if r is not None:
                        result = r
                        break
                if result is None:
                    break
            size, _ = result
            if abs(size - target_bytes) <= TARGET_TOLERANCE:
                break
            if size > target_bytes:
                hi = mid - 1
            else:
                lo = mid + 1
            if lo > hi:
                break

        # Stage 2: Fine-tune with resolution around best JPEGQ
        best_q = max(1, min(100, mid))
        fine_candidates = []
        for dq in range(-5, 6):
            for res in [72, 100, 150, 200, 300, 600]:
                jq = max(1, min(100, best_q + dq))
                fine_candidates.append((jq, res))

        jq, res, size, opts = _best_of(fine_candidates)
        return (opts, size if size > 0 else None)

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
    """Binary-search JPEG quality to hit a target file size."""
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

    opts = _build_standard_opts(
        preset=preset,
        resolution=resolution,
        jpeg_quality=None,
        color_image_resolution=color_image_resolution,
        gray_image_resolution=gray_image_resolution,
        mono_image_resolution=mono_image_resolution,
        color_image_filter=color_image_filter,
        gray_image_filter=gray_image_filter,
        mono_image_filter=mono_image_filter,
        auto_filter_color=auto_filter_color,
        auto_filter_gray=auto_filter_gray,
        auto_filter_mono=auto_filter_mono,
        embed_fonts=embed_fonts,
        subset_fonts=subset_fonts,
        compress_fonts=compress_fonts,
        compress_pages=compress_pages,
        linearize=linearize,
        detect_duplicates=detect_duplicates,
        preserve_metadata=preserve_metadata,
        preserve_annotations=preserve_annotations,
        preserve_forms=preserve_forms,
        color_conversion_strategy=color_conversion_strategy,
        compatibility_level=compatibility_level,
        grayscale=grayscale,
        lossless=lossless,
        downsample_images=downsample_images,
        extra_args=extra_args,
    )

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts)

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
