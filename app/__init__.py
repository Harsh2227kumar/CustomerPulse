"""Compatibility package for running the backend from the repo root."""

from __future__ import annotations

from pathlib import Path


_backend_app = Path(__file__).resolve().parent.parent / "backend" / "app"
if _backend_app.is_dir():
    __path__.append(str(_backend_app))

