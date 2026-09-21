"""Persistent user settings stored as a JSON file in the data directory."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator, MutableMapping
from pathlib import Path
from typing import Any

from theia_mcr_iq import paths

log = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    "com_port": "",
    "last_lens_key": "",
    "focus_speed": 1000,
    "zoom_speed": 1000,
    "iris_speed": 100,
    "focus_home_speed": 1000,
    "zoom_home_speed": 1000,
    "iris_home_speed": 100,
}


class Settings(MutableMapping[str, Any]):
    """Dict-like settings that write themselves back to disk on every change."""

    def __init__(
        self, path: Path, data: dict[str, Any] | None = None, autosave: bool = True
    ) -> None:
        """Wrap `data` (or the defaults) and persist to `path` when autosave is on."""
        self.path = path
        self.autosave = autosave
        self._data: dict[str, Any] = dict(DEFAULTS)
        if data:
            self._data.update(data)

    @classmethod
    def load(cls, path: Path | None = None, autosave: bool = True) -> Settings:
        """Read settings from `path` (default: the data directory), tolerating a missing or corrupt file."""
        path = path or paths.settings_path()
        data: dict[str, Any] = {}
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data = loaded
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("Ignoring unreadable settings file %s: %s", path, exc)
        settings = cls(path, data, autosave=autosave)
        if not path.is_file() and autosave:
            settings.save()
        return settings

    def save(self) -> None:
        """Write the settings to disk as indented JSON."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2) + "\n", encoding="utf-8")

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value
        if self.autosave:
            self.save()

    def __delitem__(self, key: str) -> None:
        del self._data[key]
        if self.autosave:
            self.save()

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"Settings({self.path!s}, {self._data!r})"
