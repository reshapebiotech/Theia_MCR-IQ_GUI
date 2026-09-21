"""Tests for port resolution and error classification."""

from __future__ import annotations

import pytest

from theia_mcr_iq import ports


def test_explicit_port_wins() -> None:
    assert (
        ports.resolve_port(
            "COM9", {"com_port": "COM1"}, ["COM1"], env={"THEIA_MCR_PORT": "COM5"}
        )
        == "COM9"
    )


def test_env_port_beats_settings() -> None:
    assert (
        ports.resolve_port(
            None, {"com_port": "COM1"}, ["COM1"], env={"THEIA_MCR_PORT": "COM5"}
        )
        == "COM5"
    )


def test_saved_port_used_only_when_present() -> None:
    assert (
        ports.resolve_port(None, {"com_port": "COM1"}, ["COM1", "COM2"], env={})
        == "COM1"
    )
    assert ports.resolve_port(None, {"com_port": "COM7"}, ["COM3"], env={}) == "COM3"


def test_sole_port_is_picked() -> None:
    assert (
        ports.resolve_port(None, {}, ["/dev/tty.usbserial-1"], env={})
        == "/dev/tty.usbserial-1"
    )


def test_ambiguous_and_missing_ports_raise() -> None:
    with pytest.raises(ports.PortResolutionError, match="Several"):
        ports.resolve_port(None, {}, ["COM3", "COM4"], env={})
    with pytest.raises(ports.PortResolutionError, match="No serial ports"):
        ports.resolve_port(None, {}, [], env={})


def test_in_use_message_detection() -> None:
    assert ports.is_in_use_message("[Errno 16] could not open port: Resource busy")
    assert ports.is_in_use_message("PermissionError(13, 'Access is denied.')")
    assert not ports.is_in_use_message("could not open port COM9: FileNotFoundError")


def test_check_port_classifies_missing_device() -> None:
    check, message = ports.check_port("/nonexistent/port", timeout=2.0)
    assert check is ports.PortCheck.ERROR
    assert "/nonexistent/port" in message
