"""Tests for the JSON-backed settings store."""

from __future__ import annotations

import json
from pathlib import Path

from theia_mcr_iq import paths
from theia_mcr_iq.settings import DEFAULTS, Settings


def test_load_creates_file_with_defaults(isolated_data_dir: Path) -> None:
    settings = Settings.load()
    assert settings.path == paths.settings_path()
    assert settings.path.is_file()
    assert dict(settings) == DEFAULTS


def test_setitem_autosaves_and_round_trips(isolated_data_dir: Path) -> None:
    settings = Settings.load()
    settings["com_port"] = "/dev/tty.usbserial-1"
    settings["focus_speed"] = 800
    on_disk = json.loads(settings.path.read_text())
    assert on_disk["com_port"] == "/dev/tty.usbserial-1"
    assert on_disk["focus_speed"] == 800
    assert Settings.load()["focus_speed"] == 800


def test_corrupt_file_falls_back_to_defaults(isolated_data_dir: Path) -> None:
    path = paths.settings_path()
    path.write_text("{not json")
    settings = Settings.load(path)
    assert settings["com_port"] == ""


def test_unknown_keys_are_kept(isolated_data_dir: Path) -> None:
    path = paths.settings_path()
    path.write_text(json.dumps({"custom": 1}))
    assert Settings.load(path)["custom"] == 1
