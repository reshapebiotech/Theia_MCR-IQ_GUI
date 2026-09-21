"""Load files shipped inside the package: lens data, help links and icons."""

from __future__ import annotations

import atexit
import json
import logging
import sys
from contextlib import ExitStack
from importlib.resources import as_file, files
from typing import Any

from theia_mcr_iq import paths

log = logging.getLogger(__name__)

_DATA = files("theia_mcr_iq.data")
_ASSETS = files("theia_mcr_iq.assets")
_exit_stack = ExitStack()  # keeps as_file() extractions alive for the process lifetime
atexit.register(_exit_stack.close)


def packaged_lens_data() -> dict[str, Any]:
    """Return the lens limits table bundled with the package."""
    return json.loads((_DATA / paths.LENS_DATA_FILE_NAME).read_text(encoding="utf-8"))


def load_lens_data() -> dict[str, Any]:
    """Return the lens limits table, preferring a user override in the data directory."""
    override = paths.lens_data_override_path()
    if override.is_file():
        log.info("Loaded lens data override from %s", override)
        return json.loads(override.read_text(encoding="utf-8"))
    log.debug("Loaded packaged lens data")
    return packaged_lens_data()


def help_links() -> list[dict[str, str]]:
    """Return the list of help link records ({'desc': ..., 'URL': ...})."""
    data = json.loads((_DATA / "help_links.json").read_text(encoding="utf-8"))
    return list(data.get("links", []))


def asset_bytes(name: str) -> bytes:
    """Return the raw bytes of a packaged asset such as an icon PNG."""
    return (_ASSETS / name).read_bytes()


def window_icon() -> bytes | str:
    """Return the window icon: PNG bytes, or a .ico path on Windows where Tk renders it better."""
    if sys.platform == "win32":
        return str(_exit_stack.enter_context(as_file(_ASSETS / "tl1250p.ico")))
    return asset_bytes(
        "tl1250p.png"
    )  # Tk on macOS/Linux only applies PNG icons passed as data
