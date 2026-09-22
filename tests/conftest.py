"""Shared fixtures: an isolated data directory and a fake TheiaMCR controller."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import pytest

from theia_mcr_iq import paths


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the data directory at a temp folder so tests never touch the real .theia-mcr/."""
    data = tmp_path / "data"
    monkeypatch.setenv(paths.ENV_DATA_DIR, str(data))
    monkeypatch.delenv("THEIA_MCR_PORT", raising=False)
    monkeypatch.delenv("THEIA_MCR_LENS", raising=False)
    return data


class FakeMotor:
    """Mimics a TheiaMCR motor object and records every call."""

    def __init__(self, name: str, pi: int = 0, fail_moves: bool = False) -> None:
        self.name = name
        self.pi_step = pi
        self.fail_moves = fail_moves
        self.currentStep = 0
        self.currentSpeed = 1000
        self.homingSpeed = 1000
        self.respectLimits = True
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _record(self, method: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append((method, args, kwargs))

    def setRespectLimits(self, state: bool) -> None:
        self._record("setRespectLimits", state)
        self.respectLimits = state

    def setMotorSpeed(self, speed: int) -> int:
        self._record("setMotorSpeed", speed)
        if not 10 <= speed <= 1500:
            return -69
        self.currentSpeed = speed
        return 0

    def setHomingSpeed(self, speed: int) -> int:
        self._record("setHomingSpeed", speed)
        if not 10 <= speed <= 1500:
            return -69
        self.homingSpeed = speed
        return 0

    def home(self) -> int:
        self._record("home")
        if self.fail_moves:
            return -62
        self.currentStep = self.pi_step
        return 0

    def moveRel(self, steps: int, correctForBL: bool = True) -> int:
        self._record("moveRel", steps, correctForBL=correctForBL)
        if self.fail_moves:
            return -62
        self.currentStep += steps
        return 0

    def moveAbs(self, step: int) -> int:
        self._record("moveAbs", step)
        if self.fail_moves:
            return -62
        self.currentStep = step
        return 0


class FakeIRC:
    """Mimics the TheiaMCR IRC object."""

    def __init__(self) -> None:
        self.states: list[int] = []

    def state(self, state: int) -> int:
        self.states.append(state)
        return state


class FakeBoard:
    """Mimics MCRControl.MCRBoard."""

    def __init__(self, fw: str = "6.1.2", sn: str = "B12345") -> None:
        self.fw = fw
        self.sn = sn
        self.paths: list[str] = []

    def readFWRevision(self) -> str:
        return self.fw

    def readBoardSN(self) -> str:
        return self.sn

    def setCommunicationPath(self, path: str) -> bool:
        self.paths.append(path)
        return path in {"UART", "I2C", "USB"}


class FakeMCR:
    """Mimics TheiaMCR.MCRControl closely enough for the controller and CLI."""

    instances: ClassVar[list[FakeMCR]] = []

    def __init__(
        self,
        port: str,
        moduleDebugLevel: bool = False,
        logFiles: bool = True,
        *,
        board_ok: bool = True,
        serial_exception: str = "",
        fail_moves: bool = False,
    ) -> None:
        self.port = port
        self.debug = moduleDebugLevel
        self.log_files = logFiles
        self.boardInitialized = board_ok
        self.MCRBoard = FakeBoard() if board_ok else None
        self.com = type("Com", (), {"serialPortException": serial_exception})()
        self.focus = FakeMotor("focus", pi=7959, fail_moves=fail_moves)
        self.zoom = FakeMotor("zoom", pi=3119, fail_moves=fail_moves)
        self.iris = FakeMotor("iris", fail_moves=fail_moves)
        self.IRC = FakeIRC()
        self.inits: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.closed = False
        FakeMCR.instances.append(self)

    def focusInit(
        self,
        steps: int,
        pi: int,
        move: bool = True,
        accel: int = 0,
        homingSpeed: int = -1,
    ) -> bool:
        self.inits.append(
            ("focus", (steps, pi), {"move": move, "homingSpeed": homingSpeed})
        )
        if move:
            self.focus.currentStep = pi
        return True

    def zoomInit(
        self,
        steps: int,
        pi: int,
        move: bool = True,
        accel: int = 0,
        homingSpeed: int = -1,
    ) -> bool:
        self.inits.append(
            ("zoom", (steps, pi), {"move": move, "homingSpeed": homingSpeed})
        )
        if move:
            self.zoom.currentStep = pi
        return True

    def irisInit(self, steps: int, move: bool = True, homingSpeed: int = -1) -> bool:
        self.inits.append(
            ("iris", (steps,), {"move": move, "homingSpeed": homingSpeed})
        )
        return True

    def IRCInit(self) -> bool:
        self.inits.append(("irc", (), {}))
        return True

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_mcr_factory() -> Callable[..., FakeMCR]:
    """A factory producing healthy FakeMCR instances; the list of created instances is on the class."""
    FakeMCR.instances.clear()
    return FakeMCR


@pytest.fixture
def make_factory() -> Callable[..., Callable[..., FakeMCR]]:
    """Build a factory that constructs FakeMCR with preset failure behaviour."""
    FakeMCR.instances.clear()

    def build(**preset: Any) -> Callable[..., FakeMCR]:
        def factory(
            port: str, moduleDebugLevel: bool = False, logFiles: bool = True
        ) -> FakeMCR:
            return FakeMCR(port, moduleDebugLevel, logFiles, **preset)

        return factory

    return build
