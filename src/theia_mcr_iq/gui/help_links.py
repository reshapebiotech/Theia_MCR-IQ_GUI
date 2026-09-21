"""Help popup support: the packaged link list and hyperlink styling."""

from __future__ import annotations

from typing import Any

from theia_mcr_iq import resources


def help_init() -> list[dict[str, str]]:
    """Return the packaged help links."""
    return resources.help_links()


def hyperlink(window: Any, field_key: str) -> None:
    """Style a Text element as a clickable link; the caller handles its event with webbrowser."""
    window[field_key].update(text_color="blue", font=("Helvetica", 10, "underline"))
