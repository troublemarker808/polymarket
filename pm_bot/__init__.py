"""Local development shim for the src/ package layout."""

from __future__ import annotations

from pathlib import Path

__all__ = ["__version__"]

_PKG_DIR = Path(__file__).resolve().parent
_SRC_PACKAGE = _PKG_DIR.parent / "src" / "pm_bot"
if _SRC_PACKAGE.is_dir():
    __path__.append(str(_SRC_PACKAGE))  # type: ignore[name-defined]

__version__ = "0.1.0"
