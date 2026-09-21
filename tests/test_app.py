"""Drive the real main window against the fake controller; skipped when no display is available."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from typing import Any

import pytest

from theia_mcr_iq import lens_data, resources
from theia_mcr_iq.controller import MCRSession
from theia_mcr_iq.ports import PortCheck, PortInfo
from theia_mcr_iq.settings import Settings

from .conftest import FakeMCR

if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    pytest.skip("no display", allow_module_level=True)

sg = pytest.importorskip("FreeSimpleGUI")
from theia_mcr_iq.gui.app import App
from theia_mcr_iq.gui.keys import Key, SettingsKey

PORT = "/dev/tty.fake"


def fake_connect(port: str, **kwargs: Any) -> MCRSession:
    return MCRSession.connect(
        port, mcr_factory=FakeMCR, port_checker=lambda p: (PortCheck.OK, "")
    )


@pytest.fixture
def app() -> Iterator[App]:
    FakeMCR.instances.clear()
    sg.popup_ok = lambda *args, **kwargs: None  # popups would block the test
    settings = Settings.load()
    settings["com_port"] = PORT
    settings["last_lens_key"] = "TL1250_N6"
    variants = lens_data.flatten(resources.packaged_lens_data())
    instance = App(
        settings,
        variants,
        connect=fake_connect,
        list_ports=lambda: [PortInfo(PORT, "fake", "x")],
    )
    instance.create_window()
    yield instance
    if instance.session is not None:
        instance.session.close()
    instance.window.close()


def mcr() -> FakeMCR:
    return FakeMCR.instances[-1]


def test_initial_state(app: App) -> None:
    assert app.com_port == PORT
    assert app.lens.key == "TL1250_N6"
    assert app.iqep is None
    assert app.window[Key.LENS_IQ_CHECKBOX].Disabled
    assert app.window[Key.MOVE_WIDE].Disabled
    assert app.actions.status == "notInit"


def test_init_without_home_enables_relative_moves(app: App) -> None:
    assert app.handle_event(Key.INIT_NO_MOVE, {})
    assert app.session is not None
    assert app.actions.status == "ready"
    assert not app.window[Key.MOVE_WIDE].Disabled
    assert app.window[Key.MOVE_ZOOM_ABS].Disabled  # no homing, no absolute moves
    assert mcr().focus.respectLimits is False
    assert app.window[Key.FW_REV].get() == "FW: 6.1.2"


def test_relative_and_absolute_moves(app: App) -> None:
    app.handle_event(Key.INIT_HOME, {})
    assert app.actions.abs_move_initialized
    assert not app.window[Key.MOVE_ZOOM_ABS].Disabled
    app.handle_event(Key.MOVE_WIDE, {Key.ZOOM_STEP: "100"})
    assert mcr().zoom.currentStep == 3119 + 100
    app.handle_event(Key.MOVE_NEAR, {Key.FOCUS_STEP: "50"})
    assert mcr().focus.currentStep == 7959 - 50
    app.handle_event(Key.MOVE_ZOOM_ABS, {Key.ZOOM_CUR: "500"})
    assert mcr().zoom.currentStep == 500
    assert app.window[Key.ZOOM_CUR].get() == "500"
    app.handle_event(
        Key.MOVE_CLOSE, {Key.IRIS_STEP: "abc"}
    )  # rejected input leaves position alone
    assert mcr().iris.currentStep == 0
    assert app.actions.status == "ready"


def test_irc_buttons(app: App) -> None:
    app.handle_event(Key.INIT_NO_MOVE, {})
    app.handle_event(Key.IRC_2, {})
    assert mcr().IRC.states[-1] == 2


def test_lens_change_uninitializes(app: App) -> None:
    app.handle_event(Key.INIT_NO_MOVE, {})
    assert app.handle_event(Key.LENS_FAMILY, {Key.LENS_FAMILY: "TL410P R3"})
    assert app.lens.key == "TL410_R3"
    assert app.settings["last_lens_key"] == "TL410_R3"
    assert app.actions.status == "notInit"
    assert app.window[Key.INIT_HOME].Disabled  # R3 has no PI
    assert app.window[Key.IRC_1].get_text() == "Filter 1"


def test_port_change_closes_session(app: App) -> None:
    app.handle_event(Key.INIT_NO_MOVE, {})
    session_mcr = mcr()
    app.handle_event(Key.PORT, {Key.PORT: "/dev/tty.other"})
    assert session_mcr.closed
    assert app.session is None
    assert app.settings["com_port"] == "/dev/tty.other"


def test_settings_values_apply_speeds(app: App) -> None:
    app.handle_event(Key.INIT_NO_MOVE, {})
    app.apply_settings_values(
        {
            SettingsKey.FOCUS_SPEED: "700",
            SettingsKey.ZOOM_SPEED: "",
            SettingsKey.IRIS_SPEED: "9000",
            SettingsKey.LIMIT_CHECK: True,
            SettingsKey.BACKLASH: False,
        }
    )
    assert mcr().focus.currentSpeed == 700
    assert app.settings["focus_speed"] == 700
    assert app.settings["iris_speed"] == 100  # rejected by the board, not saved
    assert mcr().focus.respectLimits is True
    assert app.actions.regard_backlash is False


def test_exit_event_stops_loop(app: App) -> None:
    assert app.handle_event(Key.EXIT, {}) is False
    assert app.handle_event(sg.WIN_CLOSED, {}) is False
