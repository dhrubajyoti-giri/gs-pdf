"""Ghostscript subprocess engine — builds args, executes, returns results."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class GsResult:
    """Result of a Ghostscript execution."""

    exit_code: int
    stdout: str
    stderr: str
    command: list[str] = field(repr=False)


class GsEngine:
    """Builds and executes Ghostscript command lines."""

    def __init__(self, gs_path: str = "gs", timeout: int = 300) -> None:
        self.gs_path = gs_path
        self.timeout = timeout
        self._version: str | None = None
        self._devices: list[str] | None = None

    def _find_gs(self) -> str:
        """Find the gs binary, raising a clear error if missing."""
        path = shutil.which(self.gs_path)
        if path is None:
            msg = (
                f"Ghostscript not found at '{self.gs_path}'.\n"
                "Install it:\n"
                "  Debian/Ubuntu:  apt install ghostscript\n"
                "  macOS:          brew install ghostscript\n"
                "  Windows:        choco install ghostscript"
            )
            raise RuntimeError(msg)
        return path

    def build_args(
        self,
        device: str,
        inputs: list[Path],
        output: str,
        extra: list[str] | None = None,
    ) -> list[str]:
        """Build a Ghostscript command line."""
        gs = self._find_gs()
        args: list[str] = [
            gs,
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-dSAFER",
            "-sDEVICE=" + device,
            "-sOutputFile=" + output,
        ]
        if extra:
            args.extend(extra)
        args.extend(str(p) for p in inputs)
        args.extend(["-c", "quit"])
        return args

    def execute(self, args: list[str]) -> GsResult:
        """Run Ghostscript and return the result."""
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return GsResult(
                exit_code=-1,
                stdout="",
                stderr=f"Process timed out after {self.timeout}s",
                command=args,
            )
        except FileNotFoundError:
            return GsResult(
                exit_code=-1,
                stdout="",
                stderr=f"Ghostscript binary not found: {args[0]}",
                command=args,
            )
        return GsResult(
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            command=args,
        )

    @property
    def version(self) -> str:
        """Return the installed Ghostscript version string."""
        if self._version is not None:
            return self._version
        gs = self._find_gs()
        result = subprocess.run(
            [gs, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self._version = result.stdout.strip()
        return self._version

    @property
    def available_devices(self) -> list[str]:
        """Return list of available output devices."""
        if self._devices is not None:
            return self._devices
        gs = self._find_gs()
        result = subprocess.run(
            [gs, "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        devices: list[str] = []
        in_devices = False
        for line in result.stdout.split("\n"):
            if "Available devices:" in line:
                in_devices = True
                continue
            if in_devices:
                line = line.strip()
                if not line or line.startswith("Search"):
                    break
                devices.extend(line.split())
        self._devices = devices
        return self._devices
