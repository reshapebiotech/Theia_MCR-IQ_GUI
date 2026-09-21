"""Shared MCR board session used by both the GUI and the CLI; no GUI imports here."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Self

from theia_mcr_iq import ports
from theia_mcr_iq.lens_data import LensVariant

log = logging.getLogger(__name__)

Motor = Literal["focus", "zoom", "iris"]
ALL_MOTORS: tuple[Motor, ...] = ("focus", "zoom", "iris")
ErrorKind = Literal[
    "port_in_use",
    "port_unresponsive",
    "port_error",
    "timeout",
    "board_init",
    "no_board",
    "fw_read",
    "sn_read",
    "motor_init",
    "move",
]
CommunicationPath = Literal["UART", "I2C", "USB"]

DEFAULT_CONNECT_TIMEOUT = 5.0


class MCRError(Exception):
    """A classified failure talking to the MCR board."""

    def __init__(self, kind: ErrorKind, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.detail = detail


@dataclass(frozen=True)
class BoardInfo:
    """Identity of a connected board."""

    port: str
    fw_revision: str | None
    serial_number: str | None


@dataclass(frozen=True)
class MotorSpeeds:
    """Speeds in pulses per second for the three stepper motors."""

    focus: int = 1000
    zoom: int = 1000
    iris: int = 100

    @classmethod
    def from_settings(
        cls, settings: Mapping[str, Any], homing: bool = False
    ) -> MotorSpeeds:
        """Build from the settings keys `<motor>_speed` or `<motor>_home_speed`."""
        suffix = "_home_speed" if homing else "_speed"
        defaults = cls()
        return cls(
            focus=int(settings.get(f"focus{suffix}", defaults.focus)),
            zoom=int(settings.get(f"zoom{suffix}", defaults.zoom)),
            iris=int(settings.get(f"iris{suffix}", defaults.iris)),
        )

    def get(self, motor: Motor) -> int:
        """Speed for one motor."""
        return int(getattr(self, motor))


def _default_factory() -> Callable[..., Any]:
    """Import TheiaMCR lazily so tests and offline CLI commands never need the serial stack."""
    import TheiaMCR

    return TheiaMCR.MCRControl


class MCRSession:
    """An open connection to one MCR board with typed, error-raising motor operations."""

    def __init__(self, mcr: Any, info: BoardInfo) -> None:
        """Wrap an initialized TheiaMCR controller; use `connect()` to create one."""
        self._mcr = mcr
        self.info = info

    @classmethod
    def connect(
        cls,
        port: str,
        *,
        timeout: float = DEFAULT_CONNECT_TIMEOUT,
        precheck: bool = True,
        debug: bool = False,
        log_files: bool = True,
        mcr_factory: Callable[..., Any] | None = None,
        port_checker: Callable[[str], tuple[ports.PortCheck, str]] = ports.check_port,
    ) -> MCRSession:
        """Probe the port, construct the controller under a timeout, verify the board and read its identity."""
        if precheck:
            check, message = port_checker(port)
            if check is not ports.PortCheck.OK:
                kind: ErrorKind = {
                    ports.PortCheck.IN_USE: "port_in_use",
                    ports.PortCheck.UNRESPONSIVE: "port_unresponsive",
                }.get(check, "port_error")
                raise MCRError(kind, message)

        factory = mcr_factory or _default_factory()
        mcr = _construct_with_timeout(
            factory, port, timeout, debug=debug, log_files=log_files
        )

        if not getattr(mcr, "boardInitialized", False):
            detail = str(
                getattr(getattr(mcr, "com", None), "serialPortException", "") or ""
            )
            _close_quietly(mcr)
            if detail and ports.is_in_use_message(detail):
                raise MCRError(
                    "port_in_use", f"Serial port {port} is already in use", detail
                )
            raise MCRError(
                "board_init", f"Board initialization failed on {port}", detail
            )

        board = getattr(mcr, "MCRBoard", None)
        if board is None:
            _close_quietly(mcr)
            raise MCRError(
                "no_board", "Board object not available after initialization"
            )

        fw_revision = _read_identity(
            mcr, board.readFWRevision, "fw_read", "firmware revision"
        )
        serial_number = _read_identity(
            mcr, board.readBoardSN, "sn_read", "board serial number"
        )
        log.info(
            "Connected to MCR board on %s (FW %s, SN %s)",
            port,
            fw_revision,
            serial_number,
        )
        return cls(mcr, BoardInfo(port, fw_revision, serial_number))

    @property
    def mcr(self) -> Any:
        """The underlying TheiaMCR controller, for code that still needs the raw object."""
        return self._mcr

    def motor(self, motor: Motor) -> Any:
        """The TheiaMCR motor object for `motor`."""
        return getattr(self._mcr, motor)

    def init_motors(
        self,
        lens: LensVariant,
        *,
        home: bool,
        respect_limits: bool,
        speeds: MotorSpeeds | None = None,
        homing_speeds: MotorSpeeds | None = None,
        motors: Iterable[Motor] = ALL_MOTORS,
        init_irc: bool = True,
    ) -> None:
        """Send the lens extents to the board, optionally homing, then apply limit and speed settings."""
        homing_speeds = homing_speeds or MotorSpeeds()
        motors = tuple(motors)
        for motor in motors:
            if motor == "focus":
                ok = self._mcr.focusInit(
                    lens.focus_steps,
                    lens.focus_pi,
                    move=home,
                    homingSpeed=homing_speeds.focus,
                )
            elif motor == "zoom":
                ok = self._mcr.zoomInit(
                    lens.zoom_steps,
                    lens.zoom_pi,
                    move=home,
                    homingSpeed=homing_speeds.zoom,
                )
            else:
                ok = self._mcr.irisInit(
                    lens.iris_steps, move=home, homingSpeed=homing_speeds.iris
                )
            if ok is False:
                raise MCRError("motor_init", f"{motor} motor initialization failed")
        if init_irc:
            self._mcr.IRCInit()
            self._mcr.IRC.state(1)
        self.set_respect_limits(
            respect_limits, motors=[m for m in motors if m != "iris"]
        )
        if speeds is not None:
            self.set_speeds(speeds, motors=motors)

    def set_speeds(
        self,
        speeds: MotorSpeeds,
        *,
        homing: bool = False,
        motors: Iterable[Motor] = ALL_MOTORS,
    ) -> dict[Motor, bool]:
        """Set moving (or homing) speeds; a False entry means the board rejected that value as out of range."""
        method = "setHomingSpeed" if homing else "setMotorSpeed"
        accepted: dict[Motor, bool] = {}
        for motor in motors:
            result = getattr(self.motor(motor), method)(speeds.get(motor))
            accepted[motor] = result == 0
            if result != 0:
                log.warning(
                    "%s %s speed %d out of range, not changed",
                    motor,
                    "homing" if homing else "move",
                    speeds.get(motor),
                )
        return accepted

    def set_respect_limits(
        self, state: bool, motors: Iterable[Motor] = ("focus", "zoom")
    ) -> None:
        """Tell the board whether moves may pass the PI limit switches (iris has none)."""
        for motor in motors:
            self.motor(motor).setRespectLimits(state)

    def home(self, motor: Motor) -> int:
        """Drive `motor` to its PI position and return the resulting step."""
        self._check_move(motor, self.motor(motor).home(), "home")
        return int(self.motor(motor).currentStep)

    def move_rel(self, motor: Motor, steps: int, *, backlash: bool = True) -> int:
        """Move `motor` by `steps` (sign gives direction) and return the new step."""
        if motor == "iris":
            backlash = False  # the GUI never backlash-corrects the iris
        self._check_move(
            motor,
            self.motor(motor).moveRel(int(steps), correctForBL=backlash),
            f"move {steps:+d}",
        )
        return int(self.motor(motor).currentStep)

    def move_abs(self, motor: Motor, step: int) -> int:
        """Move `motor` to an absolute step, meaningful only after `home()` in this process."""
        self._check_move(motor, self.motor(motor).moveAbs(int(step)), f"move to {step}")
        return int(self.motor(motor).currentStep)

    def irc_state(self, state: Literal[1, 2]) -> None:
        """Switch the IRC filter to position 1 or 2."""
        result = self._mcr.IRC.state(state)
        if isinstance(result, int) and result < 0:
            raise MCRError(
                "move", f"IRC filter switch to {state} failed (code {result})"
            )

    def set_communication_path(self, path: CommunicationPath) -> None:
        """Reconfigure the board's host interface; after UART or I2C the USB link stops working."""
        if not self._mcr.MCRBoard.setCommunicationPath(path):
            raise MCRError("move", f"Setting communication path to {path} failed")

    def positions(self) -> dict[Motor, int]:
        """Current step of every motor as tracked by TheiaMCR."""
        return {m: int(self.motor(m).currentStep) for m in ALL_MOTORS}

    def close(self) -> None:
        """Close the serial port and release the TheiaMCR instance."""
        _close_quietly(self._mcr)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @staticmethod
    def _check_move(motor: Motor, result: Any, action: str) -> None:
        """Raise MCRError when a TheiaMCR move call returned a negative error code."""
        if isinstance(result, int) and result < 0:
            raise MCRError("move", f"{motor} {action} failed (code {result})")


def _construct_with_timeout(
    factory: Callable[..., Any],
    port: str,
    timeout: float,
    *,
    debug: bool,
    log_files: bool,
) -> Any:
    """Construct the controller in a worker thread so a wrong port cannot freeze the caller."""
    outcome: dict[str, Any] = {}

    def worker() -> None:
        try:
            outcome["mcr"] = factory(port, moduleDebugLevel=debug, logFiles=log_files)
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller as MCRError
            outcome["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    if thread.is_alive():
        log.error("MCR initialization timed out after %.1fs on %s", timeout, port)
        raise MCRError(
            "timeout", f"Connection to {port} timed out after {timeout:.0f} s"
        )
    if "error" in outcome:
        raise MCRError(
            "board_init", f"Connection to {port} failed", str(outcome["error"])
        )
    return outcome["mcr"]


def _read_identity(
    mcr: Any, reader: Callable[[], Any], kind: ErrorKind, what: str
) -> str | None:
    """Read one identity string from the board; close and raise on exception, None when empty."""
    try:
        value = reader()
    except Exception as exc:  # reported to the caller as MCRError
        _close_quietly(mcr)
        raise MCRError(kind, f"Failed to read {what}", str(exc)) from exc
    if not value:
        log.warning("Could not read %s", what)
        return None
    return str(value)


def _close_quietly(mcr: Any) -> None:
    """Close a TheiaMCR instance, ignoring errors, so its per-port singleton is released."""
    try:
        mcr.close()
    except Exception:  # nothing useful to do if close itself fails
        log.debug("Ignoring error while closing MCR", exc_info=True)
