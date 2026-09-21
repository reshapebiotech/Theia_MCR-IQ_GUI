"""Shared fixtures: every test gets an isolated data directory."""

from __future__ import annotations

from pathlib import Path

import pytest

from theia_mcr_iq import paths


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the data directory at a temp folder so tests never touch the real .theia-mcr/."""
    data = tmp_path / "data"
    monkeypatch.setenv(paths.ENV_DATA_DIR, str(data))
    return data
