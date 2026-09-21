"""Tests for the one-shot CLI driven against the fake controller."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from theia_mcr_iq import cli, paths
from theia_mcr_iq.ports import PortCheck, PortInfo
from theia_mcr_iq.settings import Settings

from .conftest import FakeMCR

PORT = "/dev/tty.fake"
ONE_PORT = [PortInfo(PORT, "MCR board", "USB VID:PID=0403:6001")]


def run(
    argv: list[str],
    *,
    ports: list[PortInfo] | None = None,
    factory: Callable[..., Any] = FakeMCR,
) -> int:
    FakeMCR.instances.clear()
    return cli.main(
        argv,
        mcr_factory=factory,
        port_lister=lambda: ONE_PORT if ports is None else ports,
        port_checker=lambda p: (PortCheck.OK, ""),
    )


def mcr() -> FakeMCR:
    return FakeMCR.instances[-1]


@pytest.fixture
def saved_lens() -> None:
    settings = Settings.load()
    settings["last_lens_key"] = "TL1250_N6"


def test_ports_offline(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["ports"]) == 0
    assert PORT in capsys.readouterr().out
    assert run(["ports", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ports"][0]["device"] == PORT
    assert run(["ports"], ports=[]) == 0
    assert "No serial ports" in capsys.readouterr().out


def test_lenses_offline(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["lenses"]) == 0
    assert "TL1250_N6" in capsys.readouterr().out
    assert run(["--json", "lenses"]) == 0
    assert len(json.loads(capsys.readouterr().out)["lenses"]) == 12


def test_info_reports_board(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["info", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "port": PORT,
        "fw_revision": "6.1.2",
        "serial_number": "B12345",
    }
    assert mcr().closed


def test_port_resolution_failures(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["info"], ports=[]) == cli.EXIT_PORT
    assert "No serial ports" in capsys.readouterr().err
    two = [PortInfo("COM3", "", ""), PortInfo("COM4", "", "")]
    assert run(["info"], ports=two) == cli.EXIT_PORT
    assert "--port" in capsys.readouterr().err
    assert run(["--port", "COM4", "info"], ports=two) == 0
    mixed = [
        PortInfo("/dev/ttyS0", "", ""),
        PortInfo("/dev/ttyUSB0", "", "USB VID:PID=0403:6015"),
    ]
    assert run(["info"], ports=mixed) == 0
    assert mcr().port == "/dev/ttyUSB0"


def test_lens_required_for_moves(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["zoom", "rel", "10"]) == cli.EXIT_LENS
    assert "No lens selected" in capsys.readouterr().err
    assert run(["--lens", "nope", "zoom", "rel", "10"]) == cli.EXIT_LENS
    assert "Unknown lens" in capsys.readouterr().err


def test_relative_move_disables_limits(
    saved_lens: None, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(["focus", "rel", "-500", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["position"] == -500 and out["position_absolute"] is False
    assert out["moved"] == -500
    m = mcr()
    assert m.focus.calls[-1] == ("moveRel", (-500,), {"correctForBL": True})
    assert m.focus.respectLimits is False
    assert [i[0] for i in m.inits] == ["focus"]  # only the moved motor is initialized
    assert m.closed


def test_direction_words_and_backlash(saved_lens: None) -> None:
    assert run(["zoom", "tele", "100", "--no-backlash"]) == 0
    assert mcr().zoom.calls[-1] == ("moveRel", (-100,), {"correctForBL": False})
    assert run(["iris", "close", "5"]) == 0
    assert mcr().iris.calls[-1] == ("moveRel", (5,), {"correctForBL": False})
    assert run(["focus", "far", "7"]) == 0
    assert mcr().focus.calls[-1] == ("moveRel", (7,), {"correctForBL": True})


def test_abs_requires_home(
    saved_lens: None, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as info:
        run(["zoom", "abs", "500"])
    assert info.value.code == cli.EXIT_USAGE
    assert "--home" in capsys.readouterr().err


def test_abs_with_home(saved_lens: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["zoom", "abs", "500", "--home", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert (
        out["position"] == 500
        and out["position_absolute"] is True
        and out["homed"] is True
    )
    m = mcr()
    assert [c[0] for c in m.zoom.calls if c[0] in {"home", "moveAbs"}] == [
        "home",
        "moveAbs",
    ]
    assert m.zoom.respectLimits is True


def test_home_refused_without_pi(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["--lens", "TL1250_N3", "zoom", "rel", "10", "--home"]) == cli.EXIT_LENS
    assert "PI" in capsys.readouterr().err
    assert run(["--lens", "TL1250_N3", "home"]) == cli.EXIT_LENS


def test_home_all(saved_lens: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["home", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["homed"] == {
        "focus": 7959,
        "zoom": 3119,
        "iris": 0,
    }
    assert run(["home", "zoom"]) == 0
    assert [c[0] for c in mcr().zoom.calls] == [
        "setRespectLimits",
        "setMotorSpeed",
        "home",
    ]


def test_speed_override_and_settings_speed(saved_lens: None) -> None:
    Settings.load()["iris_speed"] = 60
    assert run(["iris", "open", "3", "--speed", "80"]) == 0
    assert mcr().iris.currentSpeed == 80
    assert run(["iris", "open", "3"]) == 0
    assert mcr().iris.currentSpeed == 60


def test_cli_never_writes_settings(saved_lens: None) -> None:
    before = paths.settings_path().read_text()
    assert run(["--lens", "TL410_R6", "--port", PORT, "zoom", "rel", "1"]) == 0
    assert paths.settings_path().read_text() == before


def test_irc_and_set_path(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["irc", "2"]) == 0
    assert mcr().IRC.states == [2]
    assert mcr().inits == [("irc", (), {})]
    with pytest.raises(SystemExit) as info:
        run(["set-path", "UART"])
    assert info.value.code == cli.EXIT_USAGE
    assert run(["set-path", "UART", "--yes"]) == 0
    board = mcr().MCRBoard
    assert board is not None
    assert board.paths == ["UART"]


def test_move_failure_exit_code(
    saved_lens: None, capsys: pytest.CaptureFixture[str]
) -> None:
    def factory(
        port: str, moduleDebugLevel: bool = False, logFiles: bool = True
    ) -> FakeMCR:
        return FakeMCR(port, moduleDebugLevel, logFiles, fail_moves=True)

    assert run(["zoom", "rel", "10"], factory=factory) == cli.EXIT_MOVE
    assert "failed" in capsys.readouterr().err


def test_device_failure_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    def factory(
        port: str, moduleDebugLevel: bool = False, logFiles: bool = True
    ) -> FakeMCR:
        return FakeMCR(port, moduleDebugLevel, logFiles, board_ok=False)

    assert run(["info"], factory=factory) == cli.EXIT_DEVICE
    assert "initialization failed" in capsys.readouterr().err


def test_env_lens_and_port(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(cli.ENV_LENS, "TL936P R6")
    monkeypatch.setenv("THEIA_MCR_PORT", "COM9")
    assert run(["zoom", "wide", "2", "--json"], ports=[]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["lens"] == "TL936_R6"
    assert mcr().port == "COM9"


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        cli.main(["--version"])
    assert info.value.code == 0
    assert "theia-mcr" in capsys.readouterr().out
