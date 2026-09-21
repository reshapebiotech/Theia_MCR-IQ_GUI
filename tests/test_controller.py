"""Tests for MCRSession against the fake controller."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

import pytest

from theia_mcr_iq import lens_data, resources
from theia_mcr_iq.controller import MCRError, MCRSession, MotorSpeeds
from theia_mcr_iq.ports import PortCheck

from .conftest import FakeMCR

OK_CHECK = staticmethod(lambda port: (PortCheck.OK, ""))


def lens(key: str = "TL1250_N6") -> lens_data.LensVariant:
    return lens_data.flatten(resources.packaged_lens_data())[key]


def connect(factory: Callable[..., Any], **kwargs: Any) -> MCRSession:
    return MCRSession.connect(
        "COM1", mcr_factory=factory, port_checker=lambda p: (PortCheck.OK, ""), **kwargs
    )


def test_connect_reads_identity(fake_mcr_factory: Callable[..., FakeMCR]) -> None:
    session = connect(fake_mcr_factory)
    assert session.info.port == "COM1"
    assert session.info.fw_revision == "6.1.2"
    assert session.info.serial_number == "B12345"


def test_connect_passes_debug_and_log_flags(
    fake_mcr_factory: Callable[..., FakeMCR],
) -> None:
    connect(fake_mcr_factory, debug=True, log_files=False)
    mcr = FakeMCR.instances[-1]
    assert mcr.debug is True and mcr.log_files is False


def test_precheck_failures_map_to_kinds(
    fake_mcr_factory: Callable[..., FakeMCR],
) -> None:
    for check, kind in [
        (PortCheck.IN_USE, "port_in_use"),
        (PortCheck.UNRESPONSIVE, "port_unresponsive"),
        (PortCheck.ERROR, "port_error"),
    ]:
        with pytest.raises(MCRError) as info:
            MCRSession.connect(
                "COM1",
                mcr_factory=fake_mcr_factory,
                port_checker=lambda p, c=check: (c, "msg"),
            )
        assert info.value.kind == kind
    assert FakeMCR.instances == []


def test_board_init_failure_closes_and_classifies(
    make_factory: Callable[..., Callable[..., FakeMCR]],
) -> None:
    with pytest.raises(MCRError) as info:
        connect(make_factory(board_ok=False, serial_exception="Access is denied"))
    assert info.value.kind == "port_in_use"
    assert FakeMCR.instances[-1].closed

    with pytest.raises(MCRError) as info:
        connect(make_factory(board_ok=False))
    assert info.value.kind == "board_init"
    assert FakeMCR.instances[-1].closed


def test_constructor_exception_is_board_init() -> None:
    def factory(port: str, **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    with pytest.raises(MCRError) as info:
        connect(factory)
    assert info.value.kind == "board_init"
    assert "boom" in info.value.detail


def test_constructor_timeout() -> None:
    import threading

    release = threading.Event()

    def factory(port: str, **kwargs: Any) -> Any:
        release.wait(5)
        return FakeMCR(port)

    with pytest.raises(MCRError) as info:
        connect(factory, timeout=0.2)
    assert info.value.kind == "timeout"
    release.set()


def test_init_motors_without_home_disables_limits(
    fake_mcr_factory: Callable[..., FakeMCR],
) -> None:
    session = connect(fake_mcr_factory)
    session.init_motors(
        lens(),
        home=False,
        respect_limits=False,
        homing_speeds=MotorSpeeds(900, 800, 90),
    )
    mcr = FakeMCR.instances[-1]
    assert [i[0] for i in mcr.inits] == ["focus", "zoom", "iris", "irc"]
    assert mcr.inits[0] == ("focus", (8390, 7959), {"move": False, "homingSpeed": 900})
    assert mcr.focus.respectLimits is False and mcr.zoom.respectLimits is False
    assert mcr.IRC.states == [1]


def test_init_motors_subset_and_home(fake_mcr_factory: Callable[..., FakeMCR]) -> None:
    session = connect(fake_mcr_factory)
    session.init_motors(
        lens(),
        home=True,
        respect_limits=True,
        motors=["zoom"],
        init_irc=False,
        speeds=MotorSpeeds(zoom=500),
    )
    mcr = FakeMCR.instances[-1]
    assert [i[0] for i in mcr.inits] == ["zoom"]
    assert mcr.zoom.currentStep == 3119
    assert mcr.zoom.currentSpeed == 500
    assert mcr.IRC.states == []


def test_moves_and_positions(fake_mcr_factory: Callable[..., FakeMCR]) -> None:
    session = connect(fake_mcr_factory)
    session.init_motors(lens(), home=False, respect_limits=False)
    assert session.move_rel("focus", -500) == -500
    assert session.move_rel("iris", 5, backlash=True) == 5
    mcr = FakeMCR.instances[-1]
    assert mcr.iris.calls[-1] == ("moveRel", (5,), {"correctForBL": False})
    assert session.home("zoom") == 3119
    assert session.move_abs("zoom", 100) == 100
    assert session.positions() == {"focus": -500, "zoom": 100, "iris": 5}


def test_move_failure_raises(
    make_factory: Callable[..., Callable[..., FakeMCR]],
) -> None:
    session = connect(make_factory(fail_moves=True))
    with pytest.raises(MCRError) as info:
        session.move_rel("zoom", 10)
    assert info.value.kind == "move"
    with pytest.raises(MCRError):
        session.home("focus")


def test_speeds_report_rejections(fake_mcr_factory: Callable[..., FakeMCR]) -> None:
    session = connect(fake_mcr_factory)
    accepted = session.set_speeds(
        MotorSpeeds(focus=5000, zoom=700, iris=50), homing=True
    )
    assert accepted == {"focus": False, "zoom": True, "iris": True}
    assert FakeMCR.instances[-1].zoom.homingSpeed == 700


def test_speeds_from_settings() -> None:
    settings = {
        "focus_speed": 1,
        "zoom_speed": 2,
        "iris_speed": 3,
        "focus_home_speed": 4,
        "zoom_home_speed": 5,
        "iris_home_speed": 6,
    }
    assert MotorSpeeds.from_settings(settings) == MotorSpeeds(1, 2, 3)
    assert MotorSpeeds.from_settings(settings, homing=True) == MotorSpeeds(4, 5, 6)


def test_irc_and_comm_path(fake_mcr_factory: Callable[..., FakeMCR]) -> None:
    with connect(fake_mcr_factory) as session:
        session.irc_state(2)
        session.set_communication_path("UART")
        mcr = FakeMCR.instances[-1]
        assert mcr.IRC.states == [2]
        assert mcr.MCRBoard is not None and mcr.MCRBoard.paths == ["UART"]
    assert mcr.closed


def test_constructor_exception_discards_cached_instance() -> None:
    closed: list[str] = []

    class HalfBuilt:
        def __init__(self, port: str) -> None:
            self.serialPort = type(
                "Port", (), {"close": lambda self: closed.append(port)}
            )()

    class Factory:
        _instances: ClassVar[dict[str, HalfBuilt]] = {}

        def __new__(cls, port: str, **kwargs: Any) -> Any:
            cls._instances[port] = HalfBuilt(port)
            raise ValueError("invalid literal for int()")

    with pytest.raises(MCRError) as info:
        connect(Factory)
    assert info.value.kind == "board_init"
    assert "No MCR board answered" in info.value.message
    assert Factory._instances == {}
    assert closed == ["COM1"]
