# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [3.3.0] - 2026-09-21

### Added

- `theia-mcr` command-line tool with one-shot commands: `ports`, `lenses`, `info`, `home`, `focus`, `zoom`, `iris`, `irc`, `set-path`.
- `uv` project management with `pyproject.toml`, `uv.lock` and a pinned Python 3.13.
- Shared `MCRSession` controller used by both the GUI and the CLI, with classified errors.
- Test suite with a fake controller, and a CI workflow for Linux, macOS and Windows.

### Changed

- Repackaged as the installable `theia_mcr_iq` package with `theia-mcr-gui` and `theia-mcr` entry points.
- Settings and the optional lens data override live in a project-local `.theia-mcr/` folder (or `$THEIA_MCR_DATA_DIR`, or `~/.theia-mcr`).
- Lens data, help links and icons ship inside the package.
- The GUI is an `App` class with typed element keys; module and function names follow PEP 8.
- Platform-neutral wording (serial port instead of COM port) and fonts; PNG window icon on macOS and Linux.
- The Lens IQ expansion pack is detected at start-up and the Lens IQ checkbox is disabled when it is not installed.

### Removed

- `requirements.txt`, the Windows `AppData` settings path, the unused `numpy` dependency and the tkinter file picker for a missing lens data file.

## [3.2.0] - 2026-05-19

- (limits.json) reorganized schema for simplification
- Added lens functionality check regarding available GUI buttons
- bug: motor home speed saving typo
- AI updated readme.md file for accuracy and readability

## [3.1.0]

- Changed from PySimpleGUI (no longer supported) to FreeSimpleGUI
- removed PySimpleGUI license requirement

## [3.0.4]

- added timeout for incorrectly connected com ports
- prevent multiple applications trying to connect to the same com port
- update TheiaMCR to v.3.4.2

## [3.0.3]

- removed pyproject.toml file, distributed necessary infomration

## [3.0.2]

- bug: BFLWindow set to modal instead of "keep_on_top"

## [3.0.1]

- bug: set initial FL in BFL calibration to preset[0] if the lens is ininitialization state.

## [3.0.0] - 2026-01-05

- Combined MCR IQ and lens IQ software into one version
- moved lens IQ functions to separate files
- Updated to TheiaMCR module v.3.3.4 and lensIQ module v.1.6.3
- Added clarifying text to lensIQ control section (initialized before use)
- moved some resources from data folder to config folder
- Created help file links
- Separated BFL calibration window and events into it's own section.
- Added motor control to BFL calibration window.
- Changed limits.json file to support new TL410 focus cam
- Added boardInitialization check into initMCR() function (new TheiaMCR v.3.3.4 should also check this)
- Created requirements.txt for modules

## [2.7.0] - 2025-08-25

- added slowHomeApproach to settings window
- moved backlash and regard limits to settings window

## [2.6.2] - 2025-08-25

- bug (read_settings_files): make sure the AppData/local/TheiaLensGUI/data folder exists before writing to it.

## [2.6.1] - 2025-08-12

- moved MCR out of GUI_actions

## [2.6.0] - 2025-08-11

- Separated main module into classes for easier maintenance
- Created GUI_actions, GUI_setup, PSG_license, read_settings_files, and utilities

## [2.5.7] - 2025-04-22

- updated TheiaMCR module to 3.1.5
- (lensIQ) Added new specific covered lens models to license
- Added pyproject.toml file
- (lensIQ) bug: check for loaded data before resetting sensor diagonal

## [2.5.6] - 2025-04-14

- removed depricated typing module.  Requires Python >3.10

## [2.5.5] - 2025-03-11

- (line 30) changed MCR debug log level parameter

## [2.5.4] - 2025-03-06

- updated TheiaMCR module to 2.5.0

## [2.5.3] - 2025-03-03

- bug: (lensIQ) added MCR initialization check (line 583) before IQEP functions
- (lensIQ) changed LensData.json to limits.json to avoid confusion.
- (lensIQ) added format check and popup for lens data file

## [2.5.2] - 2025-02-18

- bug: PySimpleGUI distribution license correction
- bug: (Theia_MCR) lens family selection field cleared

## [2.5.1] - 2025-02-12

- bug: changed lensData.json file location

## [2.5.0] - 2025-01-14

- moved lens data to a separate LensData.json file in the data folder
- (lensIQ) updated/corrected read me file.
- (lensIQ) lens family GUI selection will change automatically based on calibrated lens data file family

## [2.4.3] - 2025-01-07

- updated PySimpleGUI to licensed version (5.0.8) - bug prevents 'default' and some other themes, changed to LightGrey1 (different than LightGray1)

## [2.4.2] - 2024-10-11

- udpated for TheiaMCR 2.3.4 (logging reporting update)

## [2.4.1] - 2024-10-01

- added last COM port list number to selected comport field, required adjustment to cp_port and cp_refresh events

## [2.4.0] - 2024-10-01

- added COM port refresh

## [2.3.2] - 2024-09-19

- (lensIQ) fixed documentation bug: sensor w/h should be w/diag.

## [2.3.1]

- adjusted console logging structure

## [2.3.0] - 2024-08-12

- (lensIQ)Formatting adjustments to GUI for production release
- (lensIQ) removed default calibration data

## [2.2.3] - 2024-08-06

- (lensIQ) license update

## [2.2.2] - 2024-05-22

- Bug: changed from STRING_VALUE to ERR_NAN in lens IQ expansion

## [2.2.1] - 2024-03-05

- implemented signed exe

## [2.2.0] - 2024-02-07

- (lensIQ) added sensor diagonal and ratio input
- (lensIQ) Added BFLClass and BFL GUI
- Bug: added command to change communication path (previously missing)

## [2.1.4] - 2024-02-07

- bug: variable name 'prefix' in selectLens()
- bug: comport change status update error

## [2.1.3] - 2024-02-06

- bug: speed change in settings window was not an integer

## [2.1.2] - 2024-02-06

- added status indicator (moving, ready, etc)

## [2.1.1] - 2024-02-02

- added wait time spinner (Failed-couldn't get spinner class to work)

## [2.1.0] - 2024-02-01

- added return key bindings to absolute movements
- disabled buttons for init-only option (no absolute movements)
- Added IRC control

## [2.0.0] - 2024-01-25

- expanded motor control to include Lens IQ application

## [1.4.0] - 2024-01-24

- added settings popup window for motor speed and communication path selection

## [1.3.0] - 2024-01-16

- layout modification to move from development to distributable application

## [1.2.0] - 2023-12-04

- bug: fixed popup window error when comport is missing
- updated TheiaMCR control

## [1.1.0] - 2023-06-05

- added footer fields for revision, FW, and SN

## [1.0.1] - 2023-05-05

- fixed location of settings file

## [1.0.0] - 2023-05-04

- udpated GUI based on Master Control GUI v.3.2.3

## [0.3.0] - 2022-12-06

- updated due to MCRControl.py function changes for focus/zoom movements

## [0.2.2] - 2022-11-12

- fixed crash: modifications to autofocus

## [0.2.1] - 2022-11-02

- lowered trigger for mid focus step to 0.20

## [0.2.0] - 2022-10-24

- added autofocus
- dependency on commTCPIP (MTF machine)

## [0.1.4] - 2022-10-06

- added limit on/off switch

## [0.1.3] - 2022-10-04

- fixed initialization without movement to allow exceeding limits

## [0.1.2] - 2022-10-03

- added initialization without movement

## [0.1.1] - 2022-09-01

- added lens/com port selections

## [0.1.0] - 2022-08-30

- Release.
