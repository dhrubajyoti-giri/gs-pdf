# gs-pdf: Ghostscript PDF CLI Wrapper

**Date:** 2026-07-04
**Status:** Design Specification
**Language:** Python (uv-managed project)
**Stack:** Typer + Rich + Pydantic + subprocess

---

## 1. Purpose

Ghostscript (`gs`) is the most powerful open-source PDF processor, but its argument syntax is arcane, inconsistent across devices, and error-prone for everyday use. `gs-pdf` is a CLI wrapper that exposes **every Ghostscript PDF feature** through intuitive commands with sensible defaults, comprehensive `--help`, and a `raw` pass-through for zero feature gaps.

## 2. Project Structure

```
gs-pdf/
├── pyproject.toml           # uv-managed, PEP 621, typer[pip] dependencies
├── README.md                # Full user documentation
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-07-04-gs-pdf-cli-design.md   # This spec
└── src/
    └── gs_pdf/
        ├── __init__.py
        ├── __main__.py      # python -m gs_pdf entry
        ├── main.py          # Typer app root, command registration
        ├── engine.py        # Ghostscript subprocess builder + executor
        ├── config.py        # Pydantic models for ALL gs parameters
        ├── util.py          # Path resolution, format detection helpers
        └── commands/
            ├── __init__.py
            ├── compress.py
            ├── convert.py
            ├── merge.py
            ├── split.py
            ├── encrypt.py
            ├── decrypt.py
            ├── inspect.py
            ├── extract.py
            ├── pages.py
            ├── color.py
            ├── pdfa.py
            ├── fonts.py
            ├── config.py
            └── raw.py
```

## 3. Architecture

### 3.1 engine.py — Core Engine

The engine is the only module that calls `subprocess.run()` on Ghostscript.

```
GsEngine
├── gs_path: str                    # "gs" or custom path
├── version() -> str                # gs --version
├── available_devices() -> list[str] # gs --help output parse
├── build_args(device, inputs, output, options, extra) -> list[str]
│   └── Assembles: gs -q -dNOPAUSE -dBATCH -sDEVICE=<device>
│       -dSAFER <per-device-flags> -sOutputFile=<output> <inputs> -c quit
├── execute(args) -> GsResult       # subprocess.run with timeout
│   └── Returns: exit_code, stdout, stderr, output_path
└── execute_with_pipe(args) -> GsResult  # For bbox/inkcov special handling
```

**Key design choices:**
- Always uses `-dNOPAUSE -dBATCH -dSAFER` for safety and batch operation
- Catches `FileNotFoundError` → helpful error suggesting `apt install ghostscript`
- 5-minute timeout default, configurable
- Captures stderr for progress parsing (gs outputs to stderr)

### 3.2 config.py — Parameter Models

Pydantic models that type-validate every Ghostscript parameter:

```
GsQualityPreset       — screen | ebook | printer | prepress | default
GsImageFilter         — dct | flate | jpx | ccitt
GsColorModel          — rgb | cmyk | gray | unchanged
GsEncryptionKeyLength — 40 | 128 | 256
GsPermissions         — set of: print, edit, copy, annotate, forms, extract, assemble, accessibility
GsPdfALevel           — 1 | 2 | 3
GsRenderingIntent     — perceptual | saturation | relative | absolute
GsCompatibilityLevel  — 1.4 | 1.5 | 1.6 | 1.7 | 2.0
...
```

### 3.3 main.py — Typer App

```python
app = typer.Typer(rich_markup_mode="rich")

@app.callback()
def main(...):  # Global options: --verbose, --gs-path, --timeout

app.add_typer(compress.app, name="compress", ...)
app.add_typer(convert.app,  name="convert",  ...)
# ... 14 subcommands
```

### 3.4 Command Module Pattern

Each command module follows:

```python
# src/gs_pdf/commands/compress.py
app = typer.Typer(help="Reduce PDF file size")

@app.callback()
def compress(
    input: Path = typer.Argument(..., exists=True),
    output: Path = typer.Argument(...),
    preset: GsQualityPreset = typer.Option("default", "--preset"),
    resolution: int = typer.Option(150, "--resolution", min=72, max=2400),
    downsample_images: bool = typer.Option(True, "--downsample-images/--no-downsample"),
    # ... 20+ more options
):
    """Compress a PDF using Ghostscript's pdfwrite device."""
    opts = CompressOptions(preset=preset, resolution=resolution, ...)
    engine = GsEngine(gs_path=gs_path)
    args = engine.build_args("pdfwrite", [input], output, opts)
    result = engine.execute(args)
    # Print summary via Rich
```

## 4. Command Specifications

### 4.1 `gs-pdf compress`

Optimize/reduce PDF file size using pdfwrite device.

```
gs-pdf compress INPUT OUTPUT
  --preset TEXT                 Quality preset [default: default; choices: screen, ebook, printer, prepress, default]
  --resolution INTEGER          Output resolution in DPI [default: 150; range: 72-2400]
  --downsample-images / --no-downsample-images  [default: downsample-images]
  --color-image-resolution INTEGER  [default: 150]
  --gray-image-resolution INTEGER   [default: 150]
  --mono-image-resolution INTEGER   [default: 300]
  --color-image-filter [dct|flate|jpx]  [default: dct]
  --gray-image-filter [dct|flate]       [default: dct]
  --mono-image-filter [ccitt|flate]     [default: ccitt]
  --auto-filter-color / --no-auto-filter-color  [default: yes]
  --auto-filter-gray / --no-auto-filter-gray    [default: yes]
  --auto-filter-mono / --no-auto-filter-mono    [default: yes]
  --embed-fonts / --no-embed-fonts    [default: embed-fonts]
  --subset-fonts / --no-subset-fonts  [default: subset-fonts]
  --compress-fonts / --no-compress-fonts  [default: compress-fonts]
  --compress-pages / --no-compress-pages  [default: compress-pages]
  --linearize / --no-linearize     [default: no-linearize]
  --detect-duplicates / --no-detect-duplicates  [default: detect-duplicates]
  --preserve-metadata / --no-preserve-metadata  [default: preserve-metadata]
  --preserve-annotations / --flatten-annotations  [default: preserve-annotations]
  --preserve-forms / --flatten-forms  [default: preserve-forms]
  --color-conversion-strategy TEXT  [default: LeaveColorUnchanged]
  --compatibility-level TEXT    [default: 1.7; choices: 1.4, 1.5, 1.6, 1.7, 2.0]
  --grayscale / --no-grayscale  [default: no]
  --lossless / --no-lossless    [default: no]  # Forces flate everywhere, max quality
  --extra TEXT                  Raw extra Ghostscript arguments
  --verbose / --quiet           Output verbosity [default: quiet]
  --help                        Show this message
```

**Ghostscript mapping:** Uses `pdfwrite` device. Translates each flag to `-d` or `-s` parameters. `--preset` maps to `-dPDFSETTINGS=/preset`. `--lossless` mode disables all downsampling and forces flate compression.

### 4.2 `gs-pdf convert`

Convert PDF to/from images, PostScript, EPS, SVG, or text.

```
gs-pdf convert INPUT OUTPUT
  --format TEXT             Output format [auto-detect from extension; choices: png, jpeg, tiff, bmp, ps, eps, svg, text, pnm, pbm, pgm, ppm, pcx, jp2]
  --resolution INTEGER      DPI [default: 150]
  --pages TEXT              Page range e.g. "1-10" or "1,3,5-7" [default: all]
  --gray / --color          Color mode [default: color]
  --mono                    Monochrome (1-bit) output
  --alpha                   Include alpha channel (PNG only)
  --quality INTEGER         JPEG quality 1-100 [default: 90]
  --tiff-compression TEXT   TIFF compression [default: deflate; choices: none, packbits, deflate, lzw, g3, g4]
  --text-layout TEXT        Text layout for txtwrite [default: preserve; choices: physical, preserve, simple, table]
  --extra TEXT              Raw extra Ghostscript arguments
  --help
```

**Ghostscript mapping:** Selects device based on format. PNG→`png16m` (or `pnggray`/`pngmono`/`pngalpha`), JPEG→`jpeg` (or `jpeggray`), TIFF→`tiff24nc`/`tiffgray`/`tiffmono`, PS→`ps2write`, EPS→`epswrite`, SVG→`svg`, text→`txtwrite`.

### 4.3 `gs-pdf merge`

Combine multiple PDFs into a single document.

```
gs-pdf merge INPUTS... OUTPUT
  --first-page INTEGER       Start page [default: 1]
  --last-page INTEGER        End page [default: last]
  --extra TEXT               Raw extra Ghostscript arguments
  --help
```

**Ghostscript mapping:** Lists all input files, uses `pdfwrite` device, no page restrictions.

### 4.4 `gs-pdf split`

Extract pages from a PDF.

```
gs-pdf split INPUT OUTPUT_PATTERN
  --pages TEXT              Page range e.g. "1-10" or "1,3,5-7" [default: all]
  --one-per-page / --range  [default: one-per-page]
  --extra TEXT
  --help
```

**Ghostscript mapping:** Uses `-dFirstPage`/`-dLastPage` for range, `%d` in output pattern for multi-page. `--one-per-page` splits each page to a separate file by default.

### 4.5 `gs-pdf encrypt`

Add password protection and permissions.

```
gs-pdf encrypt INPUT OUTPUT
  --owner-password TEXT      Owner password (full access) [required]
  --user-password TEXT       User password (restricted access)
  --key-length [40|128|256]  Encryption key length [default: 256]
  --permissions TEXT         Comma-separated: print,edit,copy,annotate,forms,extract,assemble,accessibility [default: all]
  --no-encrypt-metadata      Don't encrypt document metadata [default: encrypt]
  --extra TEXT
  --help
```

**Ghostscript mapping:** Uses `pdfwrite` with `-sOwnerPassword`, `-sUserPassword`, `-sKeyLength`, `-dPermissions` bitmask, `-dEncryptMetadata`.

### 4.6 `gs-pdf decrypt`

Remove password protection.

```
gs-pdf decrypt INPUT OUTPUT
  --password TEXT            Password to decrypt [default: prompt if needed]
  --extra TEXT
  --help
```

### 4.7 `gs-pdf inspect`

Display PDF metadata, page info, fonts, images, ink coverage.

```
gs-pdf inspect INPUT
  --verbose          Full detailed dump
  --ink              Per-page ink coverage analysis (uses inkcov device)
  --bbox             Per-page bounding boxes (uses bbox device)
  --json             Machine-readable JSON output
  --extra TEXT
  --help
```

**Output includes:** Page count, PDF version, file size, compression ratio, fonts used (with types), color spaces, image count, metadata (author/title/subject/keywords).

### 4.8 `gs-pdf extract`

Extract text, images, or fonts from PDF. This is a command group with three subcommands.

**`gs-pdf extract text`** — Extract text content from PDF pages.
```
gs-pdf extract text INPUT OUTPUT.txt
  --encoding [Unicode|ASCII|UTF-8]  [default: UTF-8]
  --layout [physical|preserve|simple|table]  [default: preserve]
  --pages TEXT
```

**`gs-pdf extract images`** — Extract images embedded in the PDF.
```
gs-pdf extract images INPUT OUTPUT_DIR/
  --format [png|jpeg|tiff]  [default: png]
  --min-resolution INTEGER  [default: 72]
```

**`gs-pdf extract fonts`** — Dump font files embedded in the PDF.
```
gs-pdf extract fonts INPUT OUTPUT_DIR/
  --extra TEXT
  --help
```

### 4.9 `gs-pdf pages`

Page geometry operations. This is a command group with four subcommands.

**`gs-pdf pages rotate`** — Rotate pages by 90, 180, or 270 degrees.
```
gs-pdf pages rotate INPUT OUTPUT --angle [90|180|270]
  --use-trimbox / --use-cropbox / --use-artbox / --use-bleedbox  [default: use-trimbox]
  --extra TEXT
```

**`gs-pdf pages crop`** — Crop pages to a bounding box.
```
gs-pdf pages crop INPUT OUTPUT --bbox "x1 y1 x2 y2" [--units points|inches|mm]
  --extra TEXT
```

**`gs-pdf pages resize`** — Resize pages to a standard or custom size.
```
gs-pdf pages resize INPUT OUTPUT --fit [a3|a4|letter|legal|tabloid|custom WxH]
  --extra TEXT
```

**`gs-pdf pages select`** — Select specific pages from the PDF.
```
gs-pdf pages select INPUT OUTPUT --pages "1,3,5-7"
  --extra TEXT
  --help
```

### 4.10 `gs-pdf color`

Convert between color spaces.

```
gs-pdf color INPUT OUTPUT
  --to [rgb|cmyk|gray]      Target color space
  --color-conversion-strategy TEXT  [default: LeaveColorUnchanged]
  --icc-profile FILE        ICC profile for output intent
  --rendering-intent [perceptual|saturation|relative|absolute]  [default: relative]
  --preserve-overprint / --simulate-overprint  [default: preserve]
  --extra TEXT
  --help
```

### 4.11 `gs-pdf pdfa`

Convert to PDF/A archival format.

```
gs-pdf pdfa INPUT OUTPUT
  --level [1|2|3]           PDF/A level [default: 2]
  --output-intent TEXT      Output intent profile [default: sRGB; choices: sRGB, ISOcoated, eciRGB, or file.icc]
  --color-conversion-strategy TEXT  [default: UseDeviceIndependentColor]
  --policy [0|1|2]          PDFACompatibilityPolicy [default: 1]
  --extra TEXT
  --help
```

### 4.12 `gs-pdf fonts`

List, embed, subset, or substitute fonts.

```
gs-pdf fonts list INPUT

gs-pdf fonts embed INPUT OUTPUT
  --font-path PATH          Additional font directories
  --always-embed TEXT       Font names to always embed
  --never-embed TEXT        Font names to never embed

gs-pdf fonts subset INPUT OUTPUT
  --extra TEXT
  --help
```

### 4.13 `gs-pdf config`

Show detected system configuration.

```
gs-pdf config
  --json  Machine-readable output
  --help
```

**Output:** Ghostscript version, installed path, available output devices, supported file formats.

### 4.14 `gs-pdf raw`

Pass arbitrary arguments directly to Ghostscript.

```
gs-pdf raw [OPTIONS] ARGS...
  # Everything after "raw" is passed through verbatim
  # Example: gs-pdf raw -sDEVICE=pdfwrite -dPDFSETTINGS=/screen input.pdf -o out.pdf
  --help
```

## 5. Ghostscript Feature Coverage Matrix

| Ghostscript Feature | gs-pdf Command | Notes |
|---|---|---|
| PDFSETTINGS presets | `compress --preset` | Maps to -dPDFSETTINGS |
| Image downsampling | `compress --downsample-images --color-image-resolution ...` | All 3 color modes |
| Image filter selection | `compress --color-image-filter` | DCT, Flate, JPX, CCITT |
| Auto filter detection | `compress --auto-filter-*` | Per color mode |
| Font embedding/subsetting | `compress --embed-fonts --subset-fonts` / `fonts` | |
| Page compression | `compress --compress-pages` | |
| Image deduplication | `compress --detect-duplicates` | -dDetectDuplicateImages |
| Metadata preservation | `compress --preserve-metadata` | |
| Annotation handling | `compress --preserve-annotations / --flatten-annotations` | |
| Form preservation | `compress --preserve-forms / --flatten-forms` | |
| Color conversion | `color` / `compress --color-conversion-strategy` | |
| Color to grayscale | `compress --grayscale` / `color --to gray` | |
| PDF compatibility level | `compress --compatibility-level` | |
| Linearization (Fast Web View) | `compress --linearize` | -dOptimize |
| Image/PDF output devices | `convert --format` | png, jpeg, tiff, bmp, ps, eps, svg, pnm, pcx, jp2 |
| Resolution control | `convert --resolution` / `compress --resolution` | -r flag |
| Page range selection | `split --pages` / `convert --pages` | -dFirstPage/-dLastPage |
| PDF merging | `merge` | Multiple inputs |
| PDF splitting | `split` | One-per-page or range |
| Encryption (AES 256/128/40) | `encrypt --key-length` | -sKeyLength |
| Owner/user passwords | `encrypt --owner-password --user-password` | |
| Permission flags | `encrypt --permissions` | Bitmask generation |
| Metadata encryption control | `encrypt --no-encrypt-metadata` | |
| Decryption | `decrypt` | |
| Text extraction | `extract text` | txtwrite device |
| Image extraction | `extract images` | Device per format |
| Font listing/extraction | `fonts list` / `extract fonts` / `fonts` | |
| Ink coverage | `inspect --ink` | inkcov device |
| Bounding boxes | `inspect --bbox` | bbox device |
| PDF metadata | `inspect` | PDF parsing |
| Page rotation | `pages rotate` | |
| Page cropping | `pages crop` | -dUseCropBox, -dDEVICEWIDTH/HEIGHT |
| Page resizing | `pages resize` | -sPAPERSIZE, -gWxH |
| TrimBox/CropBox/ArtBox/BleedBox | `pages --use-*box` | |
| PDF/A-1b/2b/3b | `pdfa` | -dPDFA, -dPDFACompatibilityPolicy |
| Output intent profiles | `pdfa --output-intent` | -sOutputICCProfile |
| Rendering intent | `color --rendering-intent` | -dRenderIntent |
| ICC profile embedding | `color --icc-profile` | |
| Overprint control | `color --preserve-overprint / --simulate-overprint` | |
| PS/EPS/SVG output | `convert --format ps|eps|svg` | ps2write, epswrite, svg |
| Font path configuration | `fonts --font-path` | -sFONTPATH |
| Font substitution | `fonts ... --always-embed/--never-embed` | |
| Raw pass-through | `raw` | All unsupported features |

## 6. Implementation Plan

### Phase 1: Foundation
1. Scaffold `pyproject.toml`, main entry points, `engine.py`
2. Implement `config.py` with all Pydantic models
3. Create `main.py` with Typer app and router

### Phase 2: Core Commands
4. Implement `compress` command
5. Implement `convert` command
6. Implement `merge` + `split` commands
7. Implement `encrypt` + `decrypt` commands
8. Implement `inspect` command

### Phase 3: Extended Commands
9. Implement `pages` command
10. Implement `color` command
11. Implement `pdfa` command
12. Implement `extract` + `fonts` commands
13. Implement `config` + `raw` commands

### Phase 4: Documentation & Polish
14. Write comprehensive `README.md`
15. Test all commands against real PDFs
16. Handle edge cases (corrupt PDFs, no ghostscript, etc.)

## 7. Error Handling

- **No Ghostscript installed:** Catch `FileNotFoundError`, print: "Ghostscript not found. Install it: `apt install ghostscript` (Debian/Ubuntu) or `brew install ghostscript` (macOS)"
- **Corrupt PDF:** Capture gs stderr, surface the error message (gs is good at describing PDF problems)
- **Password wrong on decrypt:** gs returns non-zero with "Wrong password" message
- **Invalid option combination:** Validate with Pydantic before calling gs; raise clear Typer error
- **Timeout:** Default 5 min, configurable `--timeout`. On timeout, kill process, report

## 8. Testing Strategy

- **Unit tests:** Test `GsEngine.build_args()` produces correct `list[str]` for each command variant — no gs dependency
- **Integration tests:** Run `gs-pdf` commands against known PDF test fixtures, assert output file exists with expected properties
- **E2E tests:** Full pipeline tests — compress, then inspect, verify size reduction and validity

## 9. Non-Goals

- PDF content editing (add/remove text, images, signatures)
- PDF form filling
- PDF creation from scratch
- OCR

These are better served by dedicated tools (qpdf, pdftk, OCR tools). `gs-pdf` wraps what Ghostscript does best.
