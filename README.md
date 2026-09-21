# Theia MCR IQ lens control

Desktop GUI and command-line tool for Theia Technologies' MCR IQ motor control boards, which drive the focus, zoom, iris and IR-cut filter motors of Theia's motorized lenses. The code talks to the board over USB serial through Theia's [TheiaMCR](https://github.com/cliquot22/TheiaMCR) module and runs on macOS, Linux and Windows.

This repository is a reworked fork of Theia's [Theia_MCR-IQ_GUI](https://github.com/cliquot22/Theia_MCR-IQ_GUI) v3.2. See [CHANGELOG.md](CHANGELOG.md) for what changed.

## Requirements

- [uv](https://docs.astral.sh/uv/). It installs the pinned Python 3.13 (with Tk) on first use.
- An MCR IQ board connected by USB. It appears as `/dev/tty.usbserial-*` on macOS, `/dev/ttyUSB*` or `/dev/ttyACM*` on Linux, and `COMn` on Windows.

On Linux your user needs access to the serial device, usually by joining the `dialout` group.

## Install and run

```
git clone <this repository>
cd Theia_MCR-IQ_GUI
uv sync
uv run theia-mcr-gui      # the GUI
uv run theia-mcr ports    # the CLI
```

`uv sync` creates `.venv/` with the locked dependencies. Both commands are also available as console scripts inside that environment, and `uv run python -m theia_mcr_iq` starts the GUI too.

## GUI

1. Pick the lens model and the serial port. Click Refresh to rescan ports.
2. Click "Initialize program and home motors" to connect and drive every motor to its limit switch, or "Initialize without moving motors" to connect and leave the lens where it is. Homing needs a lens with PI limit switches and is required for absolute moves.
3. Move motors by a step count with the Tele/Wide, Near/Far and Open/Close buttons, or type a target step into a Current field and press Enter (or click the Zoom/Focus/Iris button) for an absolute move.
4. For lenses with an internal filter, the two filter buttons switch the IR-cut position.

The gear icon opens the settings window: moving and homing speeds per motor, limit switch enforcement, backlash correction, and the board's communication path. Switching the path to UART or I2C disables USB and closes the program.

### Lens IQ

Theia ships Lens IQ engineering-unit conversions as a separate module, `lensIQ_expansion`, to customers who bought a Lens IQ or calibrated lens. It is not published. When the module is importable the Lens IQ checkbox and calibration file picker work as in Theia's release; otherwise the checkbox is disabled and everything else runs normally.

## CLI

Every `theia-mcr` command connects to the board, does one thing, prints the result and disconnects. Nothing is remembered between commands, so a motor's position is unknown until it is homed in that same command.

```
theia-mcr ports                        # list serial ports
theia-mcr lenses                       # list known lens models and their extents
theia-mcr info                         # firmware revision and board serial number
theia-mcr home [focus|zoom|iris|all]   # drive motors to their limit switch
theia-mcr zoom wide 500                # relative move: wide/tele, near/far, open/close
theia-mcr focus rel -200               # relative move by signed steps
theia-mcr zoom abs 1500 --home         # home first, then move to an absolute step
theia-mcr irc 2                        # IR-cut filter position 1 or 2
theia-mcr set-path UART --yes          # switch the board off USB (irreversible from here)
```

Options work before or after the command:

| Option | Meaning |
|---|---|
| `--port PORT` | Serial port. Default: `$THEIA_MCR_PORT`, then the port saved by the GUI if present, then the only port found. |
| `--lens KEY` | Lens key or name from `theia-mcr lenses`. Default: `$THEIA_MCR_LENS`, then the lens saved by the GUI. |
| `--home` | On move commands: home the motor first. Required for `abs`. |
| `--speed PPS` | Motor speed for this command. Default: the speed saved by the GUI. |
| `--no-limits` | Allow absolute moves past the limit switch. |
| `--no-backlash` | Skip backlash correction on relative moves. |
| `--timeout S` | Connection timeout, default 5 seconds. |
| `--json` | Machine-readable result on stdout. Logs stay on stderr. |
| `--quiet`, `--debug` | Log level. Default is INFO. |

Exit codes: 0 success, 1 board or connection failure, 2 usage error, 3 no serial port could be chosen, 4 no lens could be chosen or the lens has no limit switches, 5 the board rejected a move.

The CLI reads the GUI's saved settings but never writes them.

## Files and configuration

Settings are stored in `.theia-mcr/settings.json` at the repository root (gitignored). Set `THEIA_MCR_DATA_DIR` to use another folder; when the package is installed outside a checkout the folder is `~/.theia-mcr`. Dropping a `limits.json` into that folder overrides the packaged lens table.

TheiaMCR writes its own communication logs under `~/.local/share/TheiaMCR/log` (macOS and Linux) or `%LOCALAPPDATA%\TheiaMCR\log` (Windows).

## Development

```
uv sync --all-groups
uv run ruff check && uv run ruff format --check
uv run ty check
uv run pytest
```

Tests run against a fake controller and need no hardware. The tests that build the real main window skip on a Linux machine without a display. CI runs the same four commands on Linux, macOS and Windows.

Layout: `src/theia_mcr_iq/controller.py` is the shared board session, `cli.py` the command-line tool, `gui/` the FreeSimpleGUI application, `lens_data.py` the lens table model, and `paths.py`, `resources.py`, `settings.py` handle files.

## License and contact

BSD 3-Clause, see [license](license). Copyright 2023-2026 Theia Technologies.

Theia's MCR controller page: <https://www.theiatech.com/lenses/accessories/mcr/>. Upstream author: Mark Peterson, <mpeterson@theiatech.com>. Security reports: see [SECURITY.md](SECURITY.md).
