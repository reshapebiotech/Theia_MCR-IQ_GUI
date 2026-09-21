"""Locate the per-project data directory and the files kept inside it."""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

DIST_NAME = "theia-mcr-iq-gui"
ENV_DATA_DIR = "THEIA_MCR_DATA_DIR"
DATA_DIR_NAME = ".theia-mcr"
SETTINGS_FILE_NAME = "settings.json"
LENS_DATA_FILE_NAME = "limits.json"


def project_root(start: Path | None = None) -> Path | None:
    """Walk up from this package (or `start`) to the directory holding this distribution's pyproject.toml."""
    if getattr(sys, "frozen", False):  # PyInstaller bundle: no source tree to find
        return None
    here = (start or Path(__file__)).resolve()
    for candidate in (here, *here.parents):
        if _is_own_pyproject(candidate / "pyproject.toml"):
            return candidate
    return None


def _is_own_pyproject(pyproject: Path) -> bool:
    """Return True when `pyproject` exists and names this distribution."""
    if not pyproject.is_file():
        return False
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return data.get("project", {}).get("name") == DIST_NAME


def data_dir(create: bool = True) -> Path:
    """Resolve the data directory: env override, then the project-local folder, then the home fallback."""
    override = os.environ.get(ENV_DATA_DIR)
    if override:
        path = Path(override).expanduser()
    else:
        root = project_root()
        path = (root if root is not None else Path.home()) / DATA_DIR_NAME
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    """Path of the user settings file inside the data directory."""
    return data_dir() / SETTINGS_FILE_NAME


def lens_data_override_path() -> Path:
    """Path a user can drop a custom lens data file at; it may not exist."""
    return data_dir() / LENS_DATA_FILE_NAME
