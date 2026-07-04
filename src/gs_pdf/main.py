"""gs-pdf CLI entry point and command registration."""

from __future__ import annotations

import typer

from gs_pdf.commands import (
    color,
    compress,
    config,
    convert,
    decrypt,
    encrypt,
    extract,
    fonts,
    inspect,
    merge,
    pages,
    pdfa,
    raw,
    split,
)

app = typer.Typer(
    name="gs-pdf",
    help="A user-friendly CLI wrapper around Ghostscript for PDF operations.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    gs_path: str = typer.Option(
        "gs", "--gs-path", help="Path to Ghostscript executable"
    ),
    timeout: int = typer.Option(
        300, "--timeout", help="Timeout in seconds for Ghostscript operations"
    ),
) -> None:
    """Global options shared by all commands."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["gs_path"] = gs_path
    ctx.obj["timeout"] = timeout


# Register all subcommands
app.add_typer(compress.app, name="compress", help="Reduce PDF file size")
app.add_typer(convert.app, name="convert", help="Convert PDF to/from other formats")
app.add_typer(merge.app, name="merge", help="Combine multiple PDFs into one")
app.add_typer(split.app, name="split", help="Split PDF into separate pages")
app.add_typer(encrypt.app, name="encrypt", help="Add password protection to PDF")
app.add_typer(decrypt.app, name="decrypt", help="Remove password protection from PDF")
app.add_typer(inspect.app, name="inspect", help="Show PDF metadata and information")
app.add_typer(extract.app, name="extract", help="Extract text, images, or fonts from PDF")
app.add_typer(pages.app, name="pages", help="Page operations: rotate, crop, resize, select")
app.add_typer(color.app, name="color", help="Convert PDF color space")
app.add_typer(pdfa.app, name="pdfa", help="Convert PDF to PDF/A archival format")
app.add_typer(fonts.app, name="fonts", help="List, embed, and subset fonts")
app.add_typer(config.app, name="config", help="Show Ghostscript configuration")
app.add_typer(raw.app, name="raw", help="Pass raw arguments to Ghostscript")


if __name__ == "__main__":
    app()
