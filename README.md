# Theia MCR IQ lens control

Desktop GUI and command-line tool for Theia Technologies' MCR IQ motor control boards, which drive the focus, zoom, iris and IR-cut filter motors of Theia's motorized lenses. The code talks to the board over USB serial through Theia's [TheiaMCR](https://github.com/cliquot22/TheiaMCR) module and runs on macOS, Linux and Windows.

This repository is a reworked fork of Theia's [Theia_MCR-IQ_GUI](https://github.com/cliquot22/Theia_MCR-IQ_GUI) v3.2. See [CHANGELOG.md](CHANGELOG.md) for what changed.

## Requirements

- [uv](https://docs.astral.sh/uv/). It installs the pinned Python 3.13 (with Tk) on first use. For the CLI alone, Docker is enough, see [Run with Docker](#run-with-docker).
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

## Run with Docker

For Linux hosts that have Docker but no Python 3.11 or uv. Every GitHub release publishes the CLI as the image `ghcr.io/reshapebiotech/theia-mcr-iq` for amd64 and arm64, plus a wrapper script that runs it. The GUI is not in the image. Nothing is installed on the host: the wrapper is a single `sh` script that runs from any folder.

```
mkdir -p ~/theia-mcr && cd ~/theia-mcr
curl -fsSLO https://github.com/reshapebiotech/Theia_MCR-IQ_GUI/releases/latest/download/theia-mcr
chmod +x theia-mcr
./theia-mcr ports
```

The first run pulls the image. From then on `./theia-mcr` takes the same commands and options as the native install, for example `./theia-mcr --lens TL410_R6 focus rel 100`. Removing the folder and the image (`docker image rm ghcr.io/reshapebiotech/theia-mcr-iq:4.0.0`) removes everything.

The wrapper runs `docker run --rm` with the host's `/dev` mounted and device cgroup rules for USB serial (major 188) and CDC-ACM (major 166) devices. A board plugged in after the image was pulled is visible at once, and the container does not need `--privileged`. It runs as root, so it needs no `dialout` membership, and it has no network. `~/.theia-mcr` is mounted as the data directory, so a `limits.json` override and a lens or port saved by the GUI are read. `THEIA_MCR_PORT` and `THEIA_MCR_LENS` pass through.

| Variable | Meaning |
|---|---|
| `THEIA_MCR_IMAGE` | Image to run. Default: the release's tag on ghcr.io. Point it at a locally built image such as `theia-mcr-iq:dev`. |
| `THEIA_MCR_DATA_DIR` | Host folder mounted for settings and `limits.json`. Default `~/.theia-mcr`. |
| `THEIA_MCR_PRIVILEGED` | Set to `1` to run with `--privileged` instead of the cgroup rules, for rootless Docker where the rules do not apply. |

Offline hosts: copy `theia-mcr-iq-<version>-linux-<arch>.tar.gz` from the release page to the host next to the wrapper and run `docker load < theia-mcr-iq-4.0.0-linux-amd64.tar.gz`. It restores the tag the wrapper expects, so nothing else needs configuring. The wheel on the same page is for hosts with Python 3.11 or newer that do not want Docker.

Serial passthrough only works when Docker runs on the Linux kernel that owns the USB device. Docker Desktop on macOS and Windows runs a virtual machine without USB serial access, so there only `ports`, `lenses` and `--help` are useful.

`just docker-build` builds the image locally as `theia-mcr-iq:dev` and `just docker-run lenses` runs the wrapper against it.

## GUI

1. Pick the lens model and the serial port. Click Refresh to rescan ports.
2. Click "Initialize program and home motors" to connect and drive every motor to its limit switch, or "Initialize without moving motors" to connect and leave the lens where it is. Homing needs a lens with PI limit switches and is required for absolute moves.
3. Move motors by a step count with the Tele/Wide, Near/Far and Open/Close buttons, or type a target step into a Current field and press Enter (or click the Zoom/Focus/Iris button) for an absolute move.
4. For lenses with an internal filter, the two filter buttons switch the IR-cut position.

After "Initialize without moving motors" the iris Open button does nothing until the iris has been closed, because TheiaMCR assumes the iris starts fully open at step 0.

The gear icon opens the settings window: moving and homing speeds per motor, limit switch enforcement, backlash correction, and the board's communication path. Switching the path to UART or I2C disables USB and closes the program.

### Lens IQ

Theia ships Lens IQ engineering-unit conversions as a separate module, `lensIQ_expansion`, to customers who bought a Lens IQ or calibrated lens. It is not published. When the module is importable the Lens IQ checkbox and calibration file picker work as in Theia's release; otherwise the checkbox is disabled and everything else runs normally.

This is untested.

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
| `--port PORT` | Serial port. Default: `$THEIA_MCR_PORT`, then the port saved by the GUI if present, then the only USB serial device, then the only port found. |
| `--lens KEY` | Lens key or name from `theia-mcr lenses`. Default: `$THEIA_MCR_LENS`, then the lens saved by the GUI. |
| `--home` | On move commands: home the motor first. Required for `abs`. |
| `--speed PPS` | Motor speed for this command. Default: the speed saved by the GUI. |
| `--no-limits` | Allow absolute moves past the limit switch. |
| `--no-backlash` | Skip backlash correction on relative moves. |
| `--timeout S` | Connection timeout, default 5 seconds. |
| `--json` | Machine-readable result on stdout. Logs stay on stderr. |
| `--quiet`, `--debug` | Log level. Default is INFO. |

The iris has no limit switch. TheiaMCR treats step 0 as its fully open home and clamps every move to 0..75, so from a fresh start `iris open N` does nothing; use `iris abs N --home` or `iris close N`.

Exit codes: 0 success, 1 board or connection failure, 2 usage error, 3 no serial port could be chosen, 4 no lens could be chosen or the lens has no limit switches, 5 the board rejected a move.

The CLI reads the GUI's saved settings but never writes them.

While the GUI or a CLI command holds the board, a second process gets a "port already in use" error instead of sharing the serial line. On macOS and Linux this relies on the exclusive-access flag the program sets on its own open port.

## Files and configuration

Settings are stored in `.theia-mcr/settings.json` at the repository root (gitignored). Set `THEIA_MCR_DATA_DIR` to use another folder; when the package is installed outside a checkout the folder is `~/.theia-mcr`. Dropping a `limits.json` into that folder overrides the packaged lens table.

TheiaMCR writes its own communication logs under `~/.local/share/TheiaMCR/log` (macOS and Linux) or `%LOCALAPPDATA%\TheiaMCR\log` (Windows).

## Development

```
just sync      # uv sync --all-groups
just check     # ruff check, ruff format --check, ty check, pytest
just hooks     # install the pre-commit and pre-push git hooks
just           # list every task
```

The recipes in `justfile` wrap `uv run`; without [just](https://github.com/casey/just) run the same commands by hand, for example `uv run pytest`. The git hooks (`.pre-commit-config.yaml`) use the official ruff and ty hooks on commit, pinned to the same versions as `uv.lock`, and run the tests on push.

Tests run against a fake controller and need no hardware. The tests that build the real main window skip on a Linux machine without a display. CI runs the same four commands on Linux, macOS and Windows.

Pushing a `v*` tag runs the release workflow: it checks that the tag matches the version in `pyproject.toml` and the image tag pinned in `docker/theia-mcr`, pushes the image to ghcr.io, and attaches the wheel, sdist, image tarballs and wrapper to a GitHub release. Bump all three together.

Layout: `src/theia_mcr_iq/controller.py` is the shared board session, `cli.py` the command-line tool, `gui/` the FreeSimpleGUI application, `lens_data.py` the lens table model, and `paths.py`, `resources.py`, `settings.py` handle files.

## License and contact

BSD 3-Clause, see [license](license). Copyright 2023-2026 Theia Technologies.

Theia's MCR controller page: <https://www.theiatech.com/lenses/accessories/mcr/>. Upstream author: Mark Peterson, <mpeterson@theiatech.com>. Security reports: see [SECURITY.md](SECURITY.md).
