"""Show Ghostscript configuration."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from gs_pdf.engine import GsEngine

console = Console()


def cmd(
    ctx: typer.Context,
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON"
    ),
) -> None:
    """Show detected Ghostscript version and available devices."""
    gs_path: str = ctx.obj.get("gs_path", "gs")

    try:
        engine = GsEngine(gs_path=gs_path)
        version = engine.version
        devices = engine.available_devices
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if json_output:
        data = {
            "version": version,
            "gs_path": gs_path,
            "device_count": len(devices),
            "devices": devices,
        }
        console.print(json.dumps(data, indent=2))
        return

    table = Table(title="Ghostscript Configuration")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Version", version)
    table.add_row("Path", engine._find_gs())
    table.add_row("Available Devices", str(len(devices)))
    console.print(table)

    # Show devices in categorized groups
    device_table = Table(title="Output Devices")
    device_table.add_column("Device Name", style="green")
    device_table.add_column("Type", style="cyan")
    for d in sorted(devices):
        if d.startswith("pdf"):
            dtype = "PDF"
        elif d.startswith("png"):
            dtype = "PNG"
        elif d.startswith("jpeg") or d.startswith("jpx") or d.startswith("jp2"):
            dtype = "JPEG"
        elif d.startswith("tiff"):
            dtype = "TIFF"
        elif d.startswith("bmp"):
            dtype = "BMP"
        elif d.startswith("ps"):
            dtype = "PostScript"
        elif d.startswith("eps"):
            dtype = "EPS"
        elif d.startswith("txt"):
            dtype = "Text"
        elif d.startswith("svg"):
            dtype = "SVG"
        else:
            dtype = "Other"
        device_table.add_row(d, dtype)
    console.print(device_table)
