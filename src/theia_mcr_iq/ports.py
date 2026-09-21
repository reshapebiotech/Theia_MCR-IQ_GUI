"""Serial port discovery, availability probing and default-port resolution."""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

import serial
import serial.tools.list_ports

log = logging.getLogger(__name__)

ENV_PORT = "THEIA_MCR_PORT"

# Substrings pyserial puts in its exception text when another process holds the port.
_IN_USE_MARKERS = (
    "permissionerror",
    "access is denied",
    "in use",
    "cannot access",
    "resource busy",
)


@dataclass(frozen=True)
class PortInfo:
    """One serial device as reported by pyserial."""

    device: str
    description: str
    hwid: str


class PortCheck(Enum):
    """Outcome of probing a serial port."""

    OK = "ok"
    IN_USE = "in_use"
    UNRESPONSIVE = "unresponsive"
    ERROR = "error"


class PortResolutionError(Exception):
    """Raised when no serial port can be chosen automatically."""


def list_ports() -> list[PortInfo]:
    """Return the serial ports present on this machine, sorted by device name."""
    ports = [
        PortInfo(p.device, p.description, p.hwid)
        for p in serial.tools.list_ports.comports()
    ]
    return sorted(ports, key=lambda p: p.device)


def is_in_use_message(message: str) -> bool:
    """True when a serial exception text indicates the port is held by another process."""
    lowered = message.lower()
    return any(marker in lowered for marker in _IN_USE_MARKERS)


def check_port(port: str, timeout: float = 2.0) -> tuple[PortCheck, str]:
    """Briefly open `port` in a worker thread; classify failure and treat a hang as unresponsive."""
    outcome: dict[str, object] = {"check": PortCheck.ERROR, "message": ""}

    def worker() -> None:
        try:
            serial.Serial(port=port, baudrate=115200, timeout=0.1).close()
            outcome["check"] = PortCheck.OK
        except serial.SerialException as exc:
            if is_in_use_message(str(exc)):
                outcome["check"] = PortCheck.IN_USE
                outcome["message"] = (
                    f"Port {port} is already in use by another application"
                )
            else:
                outcome["message"] = f"Port {port} error: {exc}"
        except Exception as exc:  # noqa: BLE001 - any failure means the port is unusable
            outcome["message"] = f"Unexpected error checking port {port}: {exc}"

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    if (
        thread.is_alive()
    ):  # a hung open() usually means a non-MCR device such as a Bluetooth port
        log.warning(
            "Port availability check timed out for %s after %.1fs", port, timeout
        )
        return (
            PortCheck.UNRESPONSIVE,
            f"Port {port} is unresponsive (may be the wrong device type)",
        )
    check = outcome["check"]
    assert isinstance(check, PortCheck)
    return check, str(outcome["message"])


def resolve_port(
    explicit: str | None,
    settings: Mapping[str, object],
    available: Sequence[str],
    env: Mapping[str, str] | None = None,
) -> str:
    """Pick a port: explicit flag, then $THEIA_MCR_PORT, then a saved port that is present, then the only port."""
    env = os.environ if env is None else env
    if explicit:
        return explicit
    from_env = env.get(ENV_PORT, "")
    if from_env:
        return from_env
    saved = str(settings.get("com_port", "") or "")
    if saved and saved in available:
        return saved
    if len(available) == 1:
        return available[0]
    if not available:
        raise PortResolutionError(
            "No serial ports found. Connect the MCR board or pass --port."
        )
    listing = ", ".join(available)
    raise PortResolutionError(
        f"Several serial ports found, pass --port to choose one: {listing}"
    )
