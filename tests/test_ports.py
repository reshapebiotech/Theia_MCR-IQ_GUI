"""Tests for port resolution and error classification."""

from __future__ import annotations

import pytest

from theia_mcr_iq import ports

USB_HWID = "USB VID:PID=0403:6015 SER=DC96F7HT"


def _port(device: str, hwid: str = "") -> ports.PortInfo:
    return ports.PortInfo(device, "", hwid)


def _ports(*devices: str) -> list[ports.PortInfo]:
    return [_port(d) for d in devices]


def test_explicit_port_wins() -> None:
    assert (
        ports.resolve_port(
            "COM9", {"com_port": "COM1"}, _ports("COM1"), env={"THEIA_MCR_PORT": "COM5"}
        )
        == "COM9"
    )


def test_env_port_beats_settings() -> None:
    assert (
        ports.resolve_port(
            None, {"com_port": "COM1"}, _ports("COM1"), env={"THEIA_MCR_PORT": "COM5"}
        )
        == "COM5"
    )


def test_saved_port_used_only_when_present() -> None:
    assert (
        ports.resolve_port(None, {"com_port": "COM1"}, _ports("COM1", "COM2"), env={})
        == "COM1"
    )
    assert (
        ports.resolve_port(None, {"com_port": "COM7"}, _ports("COM3"), env={}) == "COM3"
    )


def test_saved_port_beats_usb_preference() -> None:
    found = [_port("/dev/ttyS0"), _port("/dev/ttyUSB0", USB_HWID)]
    assert (
        ports.resolve_port(None, {"com_port": "/dev/ttyS0"}, found, env={})
        == "/dev/ttyS0"
    )


def test_sole_port_is_picked() -> None:
    assert (
        ports.resolve_port(None, {}, _ports("/dev/tty.usbserial-1"), env={})
        == "/dev/tty.usbserial-1"
    )


def test_sole_usb_port_is_picked_among_others() -> None:
    found = [
        *_ports("/dev/ttyS0", "/dev/ttyS1", "/dev/ttyS2", "/dev/ttyS3"),
        _port("/dev/ttyUSB0", USB_HWID),
    ]
    assert ports.resolve_port(None, {}, found, env={}) == "/dev/ttyUSB0"


def test_several_usb_ports_raise_and_list_all_devices() -> None:
    found = [
        _port("/dev/ttyS0"),
        _port("/dev/ttyUSB0", USB_HWID),
        _port("/dev/ttyUSB1", "USB VID:PID=10C4:EA60"),
    ]
    with pytest.raises(ports.PortResolutionError, match="Several") as excinfo:
        ports.resolve_port(None, {}, found, env={})
    for device in ("/dev/ttyS0", "/dev/ttyUSB0", "/dev/ttyUSB1"):
        assert device in str(excinfo.value)


def test_ambiguous_and_missing_ports_raise() -> None:
    with pytest.raises(ports.PortResolutionError, match="Several"):
        ports.resolve_port(None, {}, _ports("COM3", "COM4"), env={})
    with pytest.raises(ports.PortResolutionError, match="No serial ports"):
        ports.resolve_port(None, {}, [], env={})


def test_is_usb_reads_hwid() -> None:
    assert ports.is_usb(_port("/dev/ttyUSB0", USB_HWID))
    assert not ports.is_usb(_port("/dev/ttyS0", "PNP0501"))
    assert not ports.is_usb(_port("/dev/cu.Bluetooth-Incoming-Port", "n/a"))


def test_in_use_message_detection() -> None:
    assert ports.is_in_use_message("[Errno 16] could not open port: Resource busy")
    assert ports.is_in_use_message("PermissionError(13, 'Access is denied.')")
    assert not ports.is_in_use_message("could not open port COM9: FileNotFoundError")


def test_check_port_classifies_missing_device() -> None:
    check, message = ports.check_port("/nonexistent/port", timeout=2.0)
    assert check is ports.PortCheck.ERROR
    assert "/nonexistent/port" in message
