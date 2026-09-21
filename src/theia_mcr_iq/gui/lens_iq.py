"""Optional Lens IQ expansion pack: present only for customers who received the private module."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def load_expansion_pack(window: Any, settings: Any) -> Any | None:
    """Return an IQExpansionPack bound to `window`, or None when the module is missing or fails to start."""
    try:
        import lensIQ_expansion  # type: ignore[import-not-found]  # ty: ignore[unresolved-import]
    except ImportError:
        log.info(
            "Lens IQ expansion pack (lensIQ_expansion) not installed; Lens IQ functions disabled"
        )
        return None
    try:
        return lensIQ_expansion.IQExpansionPack(window, settings)
    except Exception:
        log.exception(
            "Lens IQ expansion pack failed to initialize; Lens IQ functions disabled"
        )
        return None
