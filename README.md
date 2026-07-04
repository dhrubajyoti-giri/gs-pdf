# gs-pdf — Ghostscript PDF CLI Wrapper

A user-friendly command-line tool that wraps Ghostscript's PDF capabilities through intuitive commands.

## Requirements

- Python 3.12+
- [Ghostscript](https://ghostscript.com/) (`gs` on PATH)

```bash
# Debian/Ubuntu
apt install ghostscript

# macOS
brew install ghostscript

# Windows
choco install ghostscript
```

## Installation

```bash
uv tool install .
# or
pip install .
```

## Usage

```
Usage: gs-pdf [OPTIONS] COMMAND [ARGS]...

  A user-friendly CLI wrapper around Ghostscript for PDF operations.

Options:
  --verbose, -v    Enable verbose output
  --gs-path TEXT   Path to Ghostscript executable [default: gs]
  --timeout INT    Timeout in seconds [default: 300]
  --help           Show this message and exit

Commands:
  compress   Reduce PDF file size
  convert    Convert PDF to/from other formats
  merge      Combine multiple PDFs into one
  split      Split PDF into separate pages
  encrypt    Add password protection to PDF
  decrypt    Remove password protection from PDF
  inspect    Show PDF metadata and information
  extract    Extract text, images, or fonts from PDF
  pages      Page operations: rotate, crop, resize, select
  color      Convert PDF color space
  pdfa       Convert PDF to PDF/A archival format
  fonts      List, embed, and subset fonts
  config     Show Ghostscript configuration
  raw        Pass raw arguments to Ghostscript
```

### Compression

```bash
gs-pdf compress input.pdf output.pdf
gs-pdf compress input.pdf output.pdf --preset screen
gs-pdf compress input.pdf output.pdf --preset ebook --resolution 300
gs-pdf compress input.pdf output.pdf --lossless
gs-pdf compress input.pdf output.pdf --grayscale
gs-pdf compress input.pdf output.pdf --linearize --compatibility-level 1.7
```

### Conversion

```bash
# PDF to PNG images
gs-pdf convert document.pdf pages/page_%d.png

# PDF to JPEG at 300 DPI
gs-pdf convert document.pdf preview.jpg --resolution 300

# PDF to text
gs-pdf convert document.pdf output.txt

# PDF to PostScript
gs-pdf convert document.pdf output.ps

# Grayscale PNG
gs-pdf convert document.pdf output.png --gray

# With specific pages
gs-pdf convert document.pdf output.png --pages 1-10
```

### Merge & Split

```bash
# Merge PDFs
gs-pdf merge chapter1.pdf chapter2.pdf chapter3.pdf combined.pdf

# Split into separate pages
gs-pdf split input.pdf page_%d.pdf

# Split specific pages
gs-pdf split input.pdf selected.pdf --pages 1,3,5-7
```

### Security

```bash
# Encrypt with AES-256
gs-pdf encrypt confidential.pdf encrypted.pdf --owner-password mypass

# Encrypt with user/owner passwords
gs-pdf encrypt doc.pdf doc-enc.pdf --owner-password admin --user-password read --key-length 128

# Decrypt
gs-pdf decrypt encrypted.pdf decrypted.pdf
```

### Inspection

```bash
# Basic info
gs-pdf inspect document.pdf

# Detailed analysis
gs-pdf inspect document.pdf --verbose --ink --bbox

# JSON output
gs-pdf inspect document.pdf --json
```

### Page Operations

```bash
# Rotate
gs-pdf pages rotate input.pdf output.pdf --angle 90

# Crop
gs-pdf pages crop input.pdf output.pdf --bbox "50 50 500 700"

# Resize to A4
gs-pdf pages resize input.pdf output.pdf --fit a4

# Select pages
gs-pdf pages select input.pdf output.pdf --pages 1,3,5-7
```

### Color & Archival

```bash
# Convert to grayscale
gs-pdf color input.pdf output.pdf --to gray

# Convert to CMYK
gs-pdf color input.pdf output.pdf --to cmyk

# PDF/A-2b
gs-pdf pdfa input.pdf output.pdf --level 2

# PDF/A-3b
gs-pdf pdfa input.pdf output.pdf --level 3 --output-intent ISOcoated
```

### Font Management

```bash
# List fonts
gs-pdf fonts list document.pdf

# Embed missing fonts
gs-pdf fonts embed input.pdf output.pdf --font-path /usr/share/fonts

# Subset embedded fonts
gs-pdf fonts subset input.pdf output.pdf
```

### Raw Passthrough

```bash
# Any Ghostscript command
gs-pdf raw -sDEVICE=pdfwrite -dPDFSETTINGS=/screen input.pdf -o out.pdf
```

## All Options Reference

### `gs-pdf compress`

| Option | Default | Description |
|--------|---------|-------------|
| `--preset` | `default` | Quality preset: screen, ebook, printer, prepress, default |
| `--resolution` | `150` | Output resolution in DPI (72-2400) |
| `--downsample-images/--no-downsample-images` | `downsample-images` | Downsample images above threshold |
| `--color-image-resolution` | `150` | Downsampling resolution for color images |
| `--gray-image-resolution` | `150` | Downsampling resolution for gray images |
| `--mono-image-resolution` | `300` | Downsampling resolution for monochrome images |
| `--color-image-filter` | `dct` | Compression filter for color images (dct, flate, jpx) |
| `--gray-image-filter` | `dct` | Compression filter for gray images (dct, flate) |
| `--mono-image-filter` | `ccitt` | Compression filter for monochrome images (ccitt, flate) |
| `--auto-filter-color/--no-auto-filter-color` | `yes` | Auto-select color image filter |
| `--auto-filter-gray/--no-auto-filter-gray` | `yes` | Auto-select gray image filter |
| `--auto-filter-mono/--no-auto-filter-mono` | `yes` | Auto-select monochrome image filter |
| `--embed-fonts/--no-embed-fonts` | `embed-fonts` | Embed all fonts |
| `--subset-fonts/--no-subset-fonts` | `subset-fonts` | Subset embedded fonts |
| `--compress-fonts/--no-compress-fonts` | `compress-fonts` | Compress font streams |
| `--compress-pages/--no-compress-pages` | `compress-pages` | Compress page content streams |
| `--linearize/--no-linearize` | `no-linearize` | Optimize for fast web viewing |
| `--detect-duplicates/--no-detect-duplicates` | `detect-duplicates` | Detect and merge duplicate images |
| `--preserve-metadata/--no-preserve-metadata` | `preserve-metadata` | Preserve document metadata |
| `--preserve-annotations/--flatten-annotations` | `preserve-annotations` | Preserve or flatten annotations |
| `--preserve-forms/--flatten-forms` | `preserve-forms` | Preserve or flatten form fields |
| `--color-conversion-strategy` | `LeaveColorUnchanged` | Color conversion strategy |
| `--compatibility-level` | `1.7` | PDF version (1.4, 1.5, 1.6, 1.7, 2.0) |
| `--grayscale/--no-grayscale` | `no` | Convert to grayscale |
| `--lossless/--no-lossless` | `no` | Maximum quality, no downsampling |
| `--extra` | — | Raw extra Ghostscript arguments |

### `gs-pdf convert`

| Option | Default | Description |
|--------|---------|-------------|
| `--format` | auto | Output format (png, jpeg, tiff, bmp, ps, eps, svg, text, pnm, pbm, pgm, ppm, pcx, jp2) |
| `--resolution` | `150` | DPI (9-2400) |
| `--pages` | all | Page range e.g. '1-10' or '1,3,5-7' |
| `--gray` | `false` | Grayscale output |
| `--mono` | `false` | Monochrome (1-bit) output |
| `--alpha` | `false` | Include alpha channel (PNG only) |
| `--quality` | `90` | JPEG/JPEG2000 quality (1-100) |
| `--tiff-compression` | `deflate` | TIFF compression (none, packbits, deflate, lzw, g3, g4) |
| `--text-layout` | `preserve` | Text layout (physical, preserve, simple, table) |
| `--extra` | — | Raw extra Ghostscript arguments |

### `gs-pdf encrypt`

| Option | Default | Description |
|--------|---------|-------------|
| `--owner-password` | (prompted) | Owner password (full access) |
| `--user-password` | — | User password (restricted access) |
| `--key-length` | `256` | Encryption key length (40, 128, 256) |
| `--permissions` | all | Comma-separated: print, edit, copy, annotate, forms, extract, assemble, accessibility |
| `--no-encrypt-metadata` | `false` | Don't encrypt document metadata |
| `--extra` | — | Raw extra Ghostscript arguments |

### `gs-pdf pdfa`

| Option | Default | Description |
|--------|---------|-------------|
| `--level` | `2` | PDF/A level (1, 2, 3) |
| `--output-intent` | `sRGB` | Output intent profile |
| `--color-conversion-strategy` | `UseDeviceIndependentColor` | Color conversion strategy |
| `--policy` | `1` | PDFACompatibilityPolicy (0=warn, 1=error, 2=auto-fix) |
| `--extra` | — | Raw extra Ghostscript arguments |

### `gs-pdf pages`

| Subcommand | Option | Default | Description |
|-----------|--------|---------|-------------|
| rotate | `--angle` | `90` | Rotation angle (90, 180, 270) |
| crop | `--bbox` | (required) | Bounding box: 'llx lly urx ury' |
| resize | `--fit` | (required) | Page size (a3, a4, letter, legal, tabloid, or WxH) |
| select | `--pages` | (required) | Page range e.g. '1,3,5-7' |

## Architecture Notes

gs-pdf is a pure wrapper around Ghostscript. It does NOT:

- Parse or modify PDF structure directly
- Render pages without Ghostscript
- Handle PDF forms, signatures, or content editing
- Process PDFs without Ghostscript installed

For every command, gs-pdf builds a Ghostscript command line from your high-level options and executes it as a subprocess. The `raw` command gives you unrestricted access to any feature not explicitly wrapped.
