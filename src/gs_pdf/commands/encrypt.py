"""PDF encryption via Ghostscript."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from gs_pdf.config import (
    GsEncryptionKeyLength,
    build_permissions_bitmask,
)
from gs_pdf.engine import GsEngine

app = typer.Typer(help="Add password protection to PDF")
console = Console()
err_console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def encrypt(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, help="Input PDF file"),
    output: Path = typer.Argument(..., help="Output encrypted PDF file"),
    owner_password: str = typer.Option(
        ..., "--owner-password", prompt=True, hide_input=True,
        help="Owner password (full access)",
    ),
    user_password: str | None = typer.Option(
        None, "--user-password", prompt=False, hide_input=True,
        help="User password (restricted access)",
    ),
    key_length: GsEncryptionKeyLength = typer.Option(
        GsEncryptionKeyLength.KEY_256, "--key-length",
        help="Encryption key length (40, 128, or 256 bits)",
    ),
    permissions: str = typer.Option(
        "print,edit,copy,annotate,forms,extract,assemble,accessibility",
        "--permissions",
        help="Comma-separated allowed permissions",
    ),
    no_encrypt_metadata: bool = typer.Option(
        False, "--no-encrypt-metadata",
        help="Don't encrypt document metadata",
    ),
    extra: str | None = typer.Option(
        None, "--extra", help="Raw extra Ghostscript arguments"
    ),
) -> None:
    """Add password protection and permission controls to a PDF.

    Supports AES-256 encryption (default), AES-128, and 40-bit RC4.
    """
    gs_path: str = ctx.obj.get("gs_path", "gs")
    timeout: int = ctx.obj.get("timeout", 300)

    extra_args: list[str] = []
    if extra:
        extra_args = extra.split()

    perms = [p.strip() for p in permissions.split(",")]
    bitmask = build_permissions_bitmask(perms)

    opts: list[str] = [
        f"-sOwnerPassword={owner_password}",
        f"-sKeyLength={key_length.value}",
        f"-dPermissions={bitmask}",
    ]

    if user_password:
        opts.append(f"-sUserPassword={user_password}")

    if key_length == GsEncryptionKeyLength.KEY_256:
        opts.append("-dEncryptionRites=/AES")
    elif key_length == GsEncryptionKeyLength.KEY_128:
        opts.append("-dEncryptionRites=/AES")
        opts.append("-dCompatibilityLevel=1.7")

    if no_encrypt_metadata:
        opts.append("-dEncryptMetadata=false")

    engine = GsEngine(gs_path=gs_path, timeout=timeout)
    args = engine.build_args("pdfwrite", [input], str(output), opts + extra_args)

    if ctx.obj.get("verbose"):
        console.print(f"[dim]Running: {' '.join(args)}[/dim]")

    result = engine.execute(args)

    if result.exit_code != 0:
        err_console.print("[red]Ghostscript error:[/red]")
        err_console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Encrypted [bold]{output}[/bold]")
    console.print(f"  Key length: {key_length.value}-bit")
    console.print(f"  Permissions: {', '.join(perms)}")
