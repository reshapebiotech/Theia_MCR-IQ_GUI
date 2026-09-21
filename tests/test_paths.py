"""Tests for data directory resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from theia_mcr_iq import paths


def test_env_override_wins(isolated_data_dir: Path) -> None:
    assert paths.data_dir() == isolated_data_dir
    assert isolated_data_dir.is_dir()


def test_project_root_finds_own_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "theia-mcr-iq-gui"\n')
    nested = tmp_path / "src" / "pkg" / "module.py"
    nested.parent.mkdir(parents=True)
    nested.touch()
    assert paths.project_root(nested) == tmp_path


def test_project_root_ignores_other_projects(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "someone-else"\n')
    nested = tmp_path / "src" / "module.py"
    nested.parent.mkdir(parents=True)
    nested.touch()
    assert paths.project_root(nested) is None


def test_real_package_resolves_to_repo_root() -> None:
    root = paths.project_root()
    assert root is not None
    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "theia_mcr_iq").is_dir()


def test_home_fallback_when_no_project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(paths.ENV_DATA_DIR)
    monkeypatch.setattr(paths, "project_root", lambda start=None: None)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert paths.data_dir(create=False) == tmp_path / paths.DATA_DIR_NAME


def test_file_paths_live_in_data_dir(isolated_data_dir: Path) -> None:
    assert paths.settings_path() == isolated_data_dir / "settings.json"
    assert paths.lens_data_override_path() == isolated_data_dir / "limits.json"
