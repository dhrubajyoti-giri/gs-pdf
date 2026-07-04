"""gs-pdf CLI entry point and command registration."""

from __future__ import annotations

import typer
from rich.console import Console

from gs_pdf.commands import color, compress, config_, convert, decrypt, encrypt
from gs_pdf.commands import extract, fonts, inspect, merge, pages, pdfa, raw, split

console = Console()

_version_flag: bool = False


def _version_callback(value: bool) -> None:
    global _version_flag
    if value:
        console.print("gs-pdf 0.1.0")
        raise typer.Exit()


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
    version: bool = typer.Option(
        False, "--version", is_eager=True, callback=_version_callback,
        help="Show version and exit",
    ),
) -> None:
    """Global options shared by all commands."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["gs_path"] = gs_path
    ctx.obj["timeout"] = timeout


# Single-action commands — registered directly on the main app
app.command(name="compress", help="Reduce PDF file size")(compress.cmd)
app.command(name="convert", help="Convert PDF to/from other formats")(convert.cmd)
app.command(name="color", help="Convert PDF color space")(color.cmd)
app.command(name="encrypt", help="Add password protection to PDF")(encrypt.cmd)
app.command(name="decrypt", help="Remove password protection from PDF")(decrypt.cmd)
app.command(name="pdfa", help="Convert PDF to PDF/A archival format")(pdfa.cmd)
app.command(name="inspect", help="Show PDF metadata and information")(inspect.cmd)
app.command(name="config", help="Show Ghostscript configuration")(config_.cmd)
app.command(name="merge", help="Combine multiple PDFs into one")(merge.cmd)
app.command(name="split", help="Split PDF into separate pages")(split.cmd)

# Raw pass-through — handles arbitrary gs arguments
app.command(
    name="raw",
    help="Pass raw arguments directly to Ghostscript",
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)(raw.cmd)

# Group commands — use sub-typers for nested sub-commands
app.add_typer(pages.app, name="pages", help="Page operations: rotate, crop, resize, select")
app.add_typer(extract.app, name="extract", help="Extract text, images, or fonts from PDF")
app.add_typer(fonts.app, name="fonts", help="List, embed, and subset fonts")


if __name__ == "__main__":
    app()
