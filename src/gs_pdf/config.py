"""Pydantic models and enums for Ghostscript parameters."""

from __future__ import annotations

from enum import Enum


class GsQualityPreset(str, Enum):
    """PDFSETTINGS quality presets for pdfwrite device."""

    SCREEN = "screen"
    EBOOK = "ebook"
    PRINTER = "printer"
    PREPRESS = "prepress"
    DEFAULT = "default"


class GsImageFilter(str, Enum):
    """Image compression filter types."""

    DCT = "dct"
    FLATE = "flate"
    JPX = "jpx"
    CCITT = "ccitt"


class GsColorModel(str, Enum):
    """Target color space."""

    RGB = "rgb"
    CMYK = "cmyk"
    GRAY = "gray"
    UNCHANGED = "unchanged"


class GsEncryptionKeyLength(int, Enum):
    """Encryption key length in bits."""

    KEY_40 = 40
    KEY_128 = 128
    KEY_256 = 256


class GsPdfALevel(int, Enum):
    """PDF/A conformance level."""

    PDFA_1 = 1
    PDFA_2 = 2
    PDFA_3 = 3


class GsRenderingIntent(str, Enum):
    """Color rendering intent."""

    PERCEPTUAL = "perceptual"
    SATURATION = "saturation"
    RELATIVE_COLORIMETRIC = "relative"
    ABSOLUTE_COLORIMETRIC = "absolute"


class GsTextLayout(str, Enum):
    """Text extraction layout mode."""

    PHYSICAL = "physical"
    PRESERVE = "preserve"
    SIMPLE = "simple"
    TABLE = "table"


class GsCompatibilityLevel(str, Enum):
    """PDF version compatibility."""

    V1_4 = "1.4"
    V1_5 = "1.5"
    V1_6 = "1.6"
    V1_7 = "1.7"
    V2_0 = "2.0"


class GsTiffCompression(str, Enum):
    """TIFF compression type."""

    NONE = "none"
    PACKBITS = "packbits"
    DEFLATE = "deflate"
    LZW = "lzw"
    G3 = "g3"
    G4 = "g4"


class GsConvertFormat(str, Enum):
    """Output format for convert command."""

    PNG = "png"
    JPEG = "jpeg"
    TIFF = "tiff"
    BMP = "bmp"
    PS = "ps"
    EPS = "eps"
    SVG = "svg"
    TEXT = "text"
    PNM = "pnm"
    PBM = "pbm"
    PGM = "pgm"
    PPM = "ppm"
    PCX = "pcx"
    JP2 = "jp2"


# Permission bits for PDF encryption
GS_PERMISSION_BITS: dict[str, int] = {
    "print": 4,
    "edit": 8,
    "copy": 16,
    "annotate": 32,
    "forms": 64,
    "extract": 128,
    "assemble": 256,
    "accessibility": 512,
}


def build_permissions_bitmask(permissions: list[str]) -> int:
    """Build a Ghostscript permission bitmask from a list of permission names."""
    mask = 0
    for p in permissions:
        bit = GS_PERMISSION_BITS.get(p.lower())
        if bit is not None:
            mask |= bit
    return mask ^ ((1 << 13) - 1)  # Invert for gs (0 = forbidden)


# Device mapping for convert command
DEVICE_MAP: dict[GsConvertFormat, str] = {
    GsConvertFormat.PNG: "png16m",
    GsConvertFormat.JPEG: "jpeg",
    GsConvertFormat.TIFF: "tiff24nc",
    GsConvertFormat.BMP: "bmp16m",
    GsConvertFormat.PS: "ps2write",
    GsConvertFormat.EPS: "epswrite",
    GsConvertFormat.SVG: "svg",
    GsConvertFormat.TEXT: "txtwrite",
    GsConvertFormat.PNM: "pnm",
    GsConvertFormat.PBM: "pbm",
    GsConvertFormat.PGM: "pgm",
    GsConvertFormat.PPM: "ppm",
    GsConvertFormat.PCX: "pcx",
    GsConvertFormat.JP2: "jp2",
}


def device_for_format(
    fmt: GsConvertFormat,
    gray: bool = False,
    mono: bool = False,
    alpha: bool = False,
) -> str:
    """Get the appropriate gs device for a format with color/gray/mono variants."""
    if fmt == GsConvertFormat.PNG:
        if mono:
            return "pngmono"
        if gray:
            return "pnggray"
        if alpha:
            return "pngalpha"
        return "png16m"
    if fmt == GsConvertFormat.JPEG:
        return "jpeggray" if gray else "jpeg"
    if fmt == GsConvertFormat.TIFF:
        if mono:
            return "tiffg4"
        if gray:
            return "tiffgray"
        return "tiff24nc"
    if fmt == GsConvertFormat.BMP:
        if mono:
            return "bmpmono"
        if gray:
            return "bmpgray"
        return "bmp16m"
    if gray:
        return DEVICE_MAP.get(fmt, DEVICE_MAP[GsConvertFormat.PNG])
    return DEVICE_MAP.get(fmt, DEVICE_MAP[GsConvertFormat.PNG])
