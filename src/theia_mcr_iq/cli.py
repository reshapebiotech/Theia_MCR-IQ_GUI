"""One-shot command-line interface: each invocation connects, acts, prints and disconnects."""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import sys
from collections.abc import Callable, Sequence
from typing import Any, Literal

from theia_mcr_iq import __version__, lens_data, ports, resources
from theia_mcr_iq.controller import ALL_MOTORS, MCRError, MCRSession, Motor, MotorSpeeds
from theia_mcr_iq.lens_data import LensNotFoundError, LensVariant
from theia_mcr_iq.settings import Settings

log = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_DEVICE = 1
EXIT_USAGE = 2
EXIT_PORT = 3
EXIT_LENS = 4
EXIT_MOVE = 5

ENV_LENS = "THEIA_MCR_LENS"

# Direction words per motor and the sign they apply to the step count.
DIRECTIONS: dict[Motor, dict[str, int]] = {
    "zoom": {"wide": 1, "tele": -1},
    "focus": {"far": 1, "near": -1},
    "iris": {"close": 1, "open": -1},
}

PortLister = Callable[[], list[ports.PortInfo]]
PortChecker = Callable[[str], tuple[ports.PortCheck, str]]


class CliError(Exception):
    """A failure with a specific exit code and a message for stderr."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclasses.dataclass
class Context:
    """Everything a command handler needs."""

    args: argparse.Namespace
    settings: Settings
    variants: dict[str, LensVariant]
    port_lister: PortLister
    mcr_factory: Callable[..., Any] | None
    port_checker: PortChecker | None

    def emit(self, payload: dict[str, Any], human: str) -> None:
        """Print `payload` as JSON when --json was given, else the human line."""
        if self.args.json:
            print(json.dumps(payload))
        else:
            print(human)

    def resolve_port(self) -> str:
        """Pick the serial port from flag, environment, settings or the single attached device."""
        try:
            return ports.resolve_port(self.args.port, self.settings, self.port_lister())
        except ports.PortResolutionError as exc:
            raise CliError(EXIT_PORT, str(exc)) from exc

    def resolve_lens(self) -> LensVariant:
        """Pick the lens from flag, environment or the saved selection."""
        query = self.args.lens or os.environ.get(ENV_LENS, "")
        if not query:
            saved = str(self.settings.get("last_lens_key", "") or "")
            query = lens_data.migrate_lens_key(saved, self.variants) if saved else ""
        if not query:
            raise CliError(
                EXIT_LENS, "No lens selected. Pass --lens KEY (see `theia-mcr lenses`)."
            )
        try:
            return lens_data.resolve_lens(query, self.variants)
        except LensNotFoundError as exc:
            keys = ", ".join(self.variants)
            raise CliError(
                EXIT_LENS, f"Unknown lens '{query}'. Known lenses: {keys}"
            ) from exc

    def connect(self) -> MCRSession:
        """Open a session on the resolved port."""
        port = self.resolve_port()
        kwargs: dict[str, Any] = {
            "timeout": self.args.timeout,
            "debug": self.args.debug,
        }
        if self.mcr_factory is not None:
            kwargs["mcr_factory"] = self.mcr_factory
        if self.port_checker is not None:
            kwargs["port_checker"] = self.port_checker
        return MCRSession.connect(port, **kwargs)

    def speeds(self, motor: Motor | None = None) -> MotorSpeeds:
        """Move speeds from settings, with --speed overriding the target motor."""
        speeds = MotorSpeeds.from_settings(self.settings)
        if motor is not None and self.args.speed is not None:
            speeds = dataclasses.replace(speeds, **{motor: int(self.args.speed)})
        return speeds


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser with the shared options accepted before or after the command."""
    parser = argparse.ArgumentParser(
        prog="theia-mcr",
        description="Control a Theia MCR lens motor board with one-shot commands.",
        epilog=(
            "Motor positions live only in this process, so every command starts from an unknown position. "
            "Add --home to home the motor first; absolute moves require it."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    _add_common(parser, suppress=False)

    sub = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)
    parents = [_common_parent()]

    sub.add_parser("ports", parents=parents, help="list serial ports")
    sub.add_parser("lenses", parents=parents, help="list known lens models")
    sub.add_parser(
        "info", parents=parents, help="show board firmware revision and serial number"
    )

    home = sub.add_parser(
        "home",
        parents=parents,
        help="home one motor or all motors to their PI position",
    )
    home.add_argument("motor", nargs="?", choices=[*ALL_MOTORS, "all"], default="all")

    for motor in ALL_MOTORS:
        words = list(DIRECTIONS[motor])
        move = sub.add_parser(
            motor,
            parents=parents,
            help=f"move the {motor} motor",
            epilog=f"'{words[0]}' moves +N steps, '{words[1]}' moves -N steps.",
        )
        move.add_argument(
            "mode",
            choices=["rel", "abs", *words],
            help="rel: signed steps, abs: target step",
        )
        move.add_argument("steps", type=int, metavar="N")
        move.add_argument(
            "--home",
            action="store_true",
            help="home the motor before moving (required for abs)",
        )

    irc = sub.add_parser("irc", parents=parents, help="switch the IRC filter")
    irc.add_argument("state", type=int, choices=[1, 2])

    path = sub.add_parser(
        "set-path",
        parents=parents,
        help="switch the board's host interface (ends USB control)",
    )
    path.add_argument("path", choices=["UART", "I2C"])
    path.add_argument(
        "--yes",
        action="store_true",
        help="confirm: USB communication stops working afterwards",
    )
    return parser


def _common_parent() -> argparse.ArgumentParser:
    """Parent parser for subcommands; suppressed defaults keep values given before the command."""
    parent = argparse.ArgumentParser(add_help=False)
    _add_common(parent, suppress=True)
    return parent


def _add_common(parser: argparse.ArgumentParser, *, suppress: bool) -> None:
    """Add the options shared by every command."""
    d = argparse.SUPPRESS if suppress else None
    group = parser.add_argument_group("connection")
    group.add_argument(
        "--port",
        default=d,
        help=f"serial port (default: ${ports.ENV_PORT}, saved port, or the only port)",
    )
    group.add_argument(
        "--lens",
        default=d,
        help=f"lens key or name (default: ${ENV_LENS} or the saved lens)",
    )
    group.add_argument(
        "--timeout",
        type=float,
        default=argparse.SUPPRESS if suppress else 5.0,
        help="connect timeout in seconds",
    )
    motion = parser.add_argument_group("motion")
    motion.add_argument(
        "--speed", type=int, default=d, help="motor speed in pps for this command"
    )
    motion.add_argument(
        "--no-limits",
        action="store_true",
        default=argparse.SUPPRESS if suppress else False,
        help="allow absolute moves past the PI limits",
    )
    motion.add_argument(
        "--no-backlash",
        action="store_true",
        default=argparse.SUPPRESS if suppress else False,
        help="skip backlash correction on relative moves",
    )
    output = parser.add_argument_group("output")
    output.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS if suppress else False,
        help="machine-readable output on stdout",
    )
    verbosity = output.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--quiet",
        action="store_true",
        default=argparse.SUPPRESS if suppress else False,
        help="only warnings and errors",
    )
    verbosity.add_argument(
        "--debug",
        action="store_true",
        default=argparse.SUPPRESS if suppress else False,
        help="debug logging, including TheiaMCR",
    )


def configure_logging(args: argparse.Namespace) -> None:
    """Route logs to stderr at the requested level."""
    level = (
        logging.DEBUG if args.debug else logging.WARNING if args.quiet else logging.INFO
    )
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(levelname)-7s %(module)-12s %(message)s",
    )


# -- commands ------------------------------------------------------------------------------


def cmd_ports(ctx: Context) -> int:
    found = ctx.port_lister()
    ctx.emit(
        {"ports": [dataclasses.asdict(p) for p in found]},
        "\n".join(f"{p.device}\t{p.description}\t[{p.hwid}]" for p in found)
        or "No serial ports found",
    )
    return EXIT_OK


def cmd_lenses(ctx: Context) -> int:
    rows = [dataclasses.asdict(v) for v in ctx.variants.values()]
    lines = [
        f"{'KEY':<16}{'NAME':<20}{'FAM':<6}{'ZOOM':>6}{'FOCUS':>7}{'IRIS':>5}  PI   IRC  FILTERS"
    ]
    for v in ctx.variants.values():
        flags = f"{'yes' if v.has_pi else 'no':<4} {'yes' if v.has_irc else 'no':<4}"
        lines.append(
            f"{v.key:<16}{v.name:<20}{v.fam:<6}{v.zoom_steps:>6}{v.focus_steps:>7}{v.iris_steps:>5}  {flags} {v.filter1}/{v.filter2}"
        )
    ctx.emit({"lenses": rows}, "\n".join(lines))
    return EXIT_OK


def cmd_info(ctx: Context) -> int:
    with ctx.connect() as session:
        info = session.info
    ctx.emit(
        {
            "port": info.port,
            "fw_revision": info.fw_revision,
            "serial_number": info.serial_number,
        },
        f"Port: {info.port}\nFirmware: {info.fw_revision or 'unknown'}\nSerial number: {info.serial_number or 'unknown'}",
    )
    return EXIT_OK


def cmd_home(ctx: Context) -> int:
    lens = ctx.resolve_lens()
    _require_pi(lens)
    motors: list[Motor] = (
        list(ALL_MOTORS) if ctx.args.motor == "all" else [ctx.args.motor]
    )
    with ctx.connect() as session:
        _init(ctx, session, lens, motors, respect_limits=True)
        positions = {m: session.home(m) for m in motors}
    ctx.emit(
        {"lens": lens.key, "homed": positions},
        "\n".join(f"{m} homed to step {p}" for m, p in positions.items()),
    )
    return EXIT_OK


def cmd_move(ctx: Context, motor: Motor) -> int:
    args = ctx.args
    lens = ctx.resolve_lens()
    if args.home:
        _require_pi(lens)
    absolute = args.mode == "abs"
    sign = DIRECTIONS[motor].get(args.mode, 1)
    with ctx.connect() as session:
        _init(
            ctx, session, lens, [motor], respect_limits=args.home and not args.no_limits
        )
        homed_from = session.home(motor) if args.home else None
        start = session.positions()[motor]
        if absolute:
            position = session.move_abs(motor, args.steps)
        else:
            position = session.move_rel(
                motor, sign * args.steps, backlash=not args.no_backlash
            )
    moved = position - start
    payload = {
        "lens": lens.key,
        "motor": motor,
        "mode": args.mode,
        "steps": args.steps,
        "homed": args.home,
        "moved": moved,
        "position": position,
        "position_absolute": args.home,
    }
    prefix = f"{motor} homed to {homed_from}, then " if args.home else f"{motor} "
    if absolute:
        human = f"{prefix}moved to step {position}"
    else:
        human = f"{prefix}moved {moved:+d} steps to {'step' if args.home else 'relative position'} {position}"
    if not absolute and moved != sign * args.steps:
        human += f" (requested {sign * args.steps:+d}, clamped by the step limits)"
    ctx.emit(payload, human)
    return EXIT_OK


def cmd_irc(ctx: Context) -> int:
    state: Literal[1, 2] = ctx.args.state
    with ctx.connect() as session:
        session.init_irc()
        session.irc_state(state)
    ctx.emit({"irc": state}, f"IRC filter set to position {state}")
    return EXIT_OK


def cmd_set_path(ctx: Context) -> int:
    path: Literal["UART", "I2C"] = ctx.args.path
    with ctx.connect() as session:
        session.set_communication_path(path)
    ctx.emit(
        {"communication_path": path},
        f"Communication path set to {path}. USB communication is no longer available; reconnect over {path}.",
    )
    return EXIT_OK


def _require_pi(lens: LensVariant) -> None:
    """Homing needs PI limit switches; refuse for lens variants without them."""
    if not lens.has_pi:
        raise CliError(
            EXIT_LENS,
            f"Lens {lens.key} has no PI limit switches, so it cannot be homed.",
        )


def _init(
    ctx: Context,
    session: MCRSession,
    lens: LensVariant,
    motors: Sequence[Motor],
    *,
    respect_limits: bool,
) -> None:
    """Initialize `motors` for `lens` without moving, then apply the resolved speeds."""
    target = motors[0] if len(motors) == 1 else None
    session.init_motors(
        lens,
        home=False,
        respect_limits=respect_limits,
        speeds=ctx.speeds(target),
        homing_speeds=MotorSpeeds.from_settings(ctx.settings, homing=True),
        motors=motors,
        init_irc=False,
    )


COMMANDS: dict[str, Callable[[Context], int]] = {
    "ports": cmd_ports,
    "lenses": cmd_lenses,
    "info": cmd_info,
    "home": cmd_home,
    "irc": cmd_irc,
    "set-path": cmd_set_path,
    **{motor: (lambda ctx, m=motor: cmd_move(ctx, m)) for motor in ALL_MOTORS},
}


def main(
    argv: Sequence[str] | None = None,
    *,
    mcr_factory: Callable[..., Any] | None = None,
    port_lister: PortLister | None = None,
    port_checker: PortChecker | None = None,
) -> int:
    """Entry point of `theia-mcr`; the keyword arguments are injection points for tests."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in ALL_MOTORS and args.mode == "abs" and not args.home:
        parser.error(
            "absolute moves need --home: the motor position is unknown until it is homed"
        )
    if args.command == "set-path" and not args.yes:
        parser.error(
            "set-path needs --yes: USB communication to the board stops working afterwards"
        )
    configure_logging(args)

    settings = Settings.load(autosave=False)  # the CLI never writes settings
    variants = lens_data.flatten(resources.load_lens_data())
    ctx = Context(
        args,
        settings,
        variants,
        port_lister or ports.list_ports,
        mcr_factory,
        port_checker,
    )
    try:
        return COMMANDS[args.command](ctx)
    except CliError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return exc.code
    except MCRError as exc:
        detail = f" ({exc.detail})" if exc.detail else ""
        print(f"error: {exc.message}{detail}", file=sys.stderr)
        return EXIT_MOVE if exc.kind == "move" else EXIT_DEVICE


if __name__ == "__main__":
    sys.exit(main())
