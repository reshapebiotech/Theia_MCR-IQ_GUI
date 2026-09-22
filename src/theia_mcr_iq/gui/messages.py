"""Popup text for controller errors, worded for every desktop platform."""

from __future__ import annotations

import FreeSimpleGUI as sg

from theia_mcr_iq.controller import MCRError

_PORT_IN_USE = (
    "Serial port already in use",
    (
        "Serial port {port} is already in use.\n\n"
        "Another application is connected to this port.\n\n"
        "To resolve this:\n"
        "  - Close other instances of this application\n"
        "  - Close other programs using this serial port\n"
        "  - Check the serial devices present (Windows: Device Manager, macOS: ls /dev/tty.*, Linux: dmesg | tail)\n"
        "  - Unplug and reconnect the USB cable"
    ),
)
_PORT_UNRESPONSIVE = (
    "Wrong serial port",
    (
        "Serial port {port} is not responding.\n\n"
        "This usually means the selected port belongs to another device, such as:\n"
        "  - A Bluetooth adapter\n"
        "  - A GPS receiver\n"
        "  - Another virtual serial port\n\n"
        "Select the port that corresponds to the USB connection of the motor controller board."
    ),
)
_CONNECTION_FAILED = (
    "Connection failed",
    (
        "Motor controller initialization failed on {port}.\n\n"
        "Possible causes:\n"
        "  - Wrong serial port selected\n"
        "  - Board not connected or not powered\n"
        "  - USB cable disconnected\n"
        "  - Serial port in use by another application\n"
        "  - Board firmware issue"
    ),
)
_BOARD_READ = (
    "Board error",
    "Could not read the board identity on {port}.\n\n{message}",
)
_MOTOR = ("Motor error", "{message}")

POPUPS: dict[str, tuple[str, str]] = {
    "port_in_use": _PORT_IN_USE,
    "port_unresponsive": _PORT_UNRESPONSIVE,
    "port_error": ("Serial port unavailable", "{message}"),
    "timeout": _CONNECTION_FAILED,
    "board_init": _CONNECTION_FAILED,
    "no_board": _CONNECTION_FAILED,
    "fw_read": _BOARD_READ,
    "sn_read": _BOARD_READ,
    "motor_init": _MOTOR,
    "move": _MOTOR,
}


def show_error(error: MCRError, port: str = "") -> None:
    """Show the popup matching `error.kind`."""
    title, body = POPUPS.get(error.kind, ("Error", "{message}"))
    text = body.format(port=port, message=error.message)
    if error.detail:
        text += f"\n\nDetails: {error.detail}"
    sg.popup_ok(text, title=title)
