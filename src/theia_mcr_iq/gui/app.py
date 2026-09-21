"""Main GUI application: window creation, event loop and controller wiring."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from os import path
from typing import Any, Literal

import FreeSimpleGUI as sg

from theia_mcr_iq import __version__, lens_data, ports, resources
from theia_mcr_iq.controller import ALL_MOTORS, MCRError, MCRSession, Motor, MotorSpeeds
from theia_mcr_iq.gui import layout, lens_iq, messages
from theia_mcr_iq.gui.actions import GuiActions
from theia_mcr_iq.gui.keys import RETURN_BINDING_SUFFIX, Key, SettingsKey
from theia_mcr_iq.lens_data import LensVariant
from theia_mcr_iq.settings import Settings

log = logging.getLogger(__name__)

MCR_DEBUG = False  # TheiaMCR module debug logging

WINDOW_TITLE = "Theia MCR IQ™ control"

# Relative-move buttons: motor and direction sign applied to the step field value.
_RELATIVE_MOVES: dict[str, tuple[Motor, int]] = {
    Key.MOVE_WIDE: ("zoom", 1),
    Key.MOVE_TELE: ("zoom", -1),
    Key.MOVE_NEAR: ("focus", -1),
    Key.MOVE_FAR: ("focus", 1),
    Key.MOVE_OPEN: ("iris", -1),
    Key.MOVE_CLOSE: ("iris", 1),
}
_ABSOLUTE_MOVES: dict[str, Motor] = {
    Key.MOVE_ZOOM_ABS: "zoom",
    Key.ZOOM_CUR_UPDATE: "zoom",
    Key.MOVE_FOCUS_ABS: "focus",
    Key.FOCUS_CUR_UPDATE: "focus",
    Key.MOVE_IRIS_ABS: "iris",
    Key.IRIS_CUR_UPDATE: "iris",
}
_STEP_FIELDS: dict[Motor, Key] = {
    "zoom": Key.ZOOM_STEP,
    "focus": Key.FOCUS_STEP,
    "iris": Key.IRIS_STEP,
}
_CURRENT_FIELDS: dict[Motor, Key] = {
    "zoom": Key.ZOOM_CUR,
    "focus": Key.FOCUS_CUR,
    "iris": Key.IRIS_CUR,
}
_CAL_FILE_KEYS = (Key.CAL_FILE_TEXT, Key.CAL_FILE, Key.CAL_FILE_BROWSE)


class App:
    """The main window and everything it owns: settings, lens table, controller session, Lens IQ pack."""

    def __init__(
        self,
        settings: Settings,
        variants: dict[str, LensVariant],
        *,
        connect: Callable[..., MCRSession] = MCRSession.connect,
        list_ports: Callable[[], list[ports.PortInfo]] = ports.list_ports,
    ) -> None:
        """Prepare state from `settings` and the lens `variants`; the window is created in `run()`."""
        self.settings = settings
        self.variants = variants
        self._connect = connect  # injection points for tests without hardware
        self._list_ports = list_ports
        self.window: Any = None
        self._actions: GuiActions | None = None
        self.session: MCRSession | None = None
        self.iqep: Any | None = None
        self.lens_iq_active = False  # a compatible calibration file is loaded
        self.calibration_file = ""
        self.port_list = [p.device for p in self._list_ports()]
        self.com_port = str(settings["com_port"])
        if self.com_port not in self.port_list:
            self.com_port = ""
        saved_key = str(settings["last_lens_key"])
        self.lens_key = lens_data.migrate_lens_key(saved_key, variants)
        if self.lens_key != saved_key:
            log.info('Migrated saved lens "%s" to "%s"', saved_key, self.lens_key)
            settings["last_lens_key"] = self.lens_key

    @property
    def lens(self) -> LensVariant:
        """The currently selected lens variant."""
        return self.variants[self.lens_key]

    @property
    def actions(self) -> GuiActions:
        """The UI-state helper; only valid after `create_window()`."""
        if self._actions is None:
            raise RuntimeError("window not created")
        return self._actions

    def _require_session(self) -> MCRSession:
        """The open controller session; callers guard on `self.session` first."""
        if self.session is None:
            raise RuntimeError("controller not connected")
        return self.session

    def create_window(self) -> None:
        """Build the main window, load the optional Lens IQ pack and set the initial control state."""
        sg.set_global_icon(resources.window_icon())
        layout.apply_theme()
        self.window = sg.Window(WINDOW_TITLE, layout.main_layout(), finalize=True)
        self.window[Key.REVISION].update(f"v. {__version__}")
        for key in _CURRENT_FIELDS.values():
            self.window[key].bind("<Return>", RETURN_BINDING_SUFFIX)
        names = [v.name for v in self.variants.values()]
        self.window[Key.LENS_FAMILY].update(
            value=self.lens.name, values=names, size=(18, 10)
        )
        self.window[Key.PORT].update(
            value=self.com_port, values=sorted(self.port_list), size=(18, 10)
        )

        self.iqep = lens_iq.load_expansion_pack(self.window, self.settings)
        if self.iqep is None:
            self.window[Key.LENS_IQ_CHECKBOX].update(
                text="Lens IQ expansion pack not installed", disabled=True
            )

        self._actions = GuiActions(self.window, lens_iq_available=self.iqep is not None)
        self.actions.set_status("notInit")
        self.actions.enable_live_frame(False)
        self.actions.enable_live_frame_irc(False)
        self.configure_irc_buttons()
        self.actions.enable_init_home_btn(self.lens.has_pi)

    def run(self) -> int:
        """Create the window and process events until the user quits."""
        self.create_window()
        try:
            while True:
                event, values = self.window.read()
                if not self.handle_event(event, values or {}):
                    break
        finally:
            if self.session is not None:
                self.session.close()
            self.window.close()
        return 0

    def handle_event(self, event: Any, values: dict[str, Any]) -> bool:
        """Dispatch one window event; return False when the application should exit."""
        if event in (sg.WIN_CLOSED, Key.EXIT):
            return False
        if event == Key.LENS_FAMILY:
            self.on_lens_selected(values)
        elif event == Key.PORT:
            self.on_port_selected(values)
        elif event == Key.PORT_REFRESH:
            self.on_port_refresh()
        elif event == Key.INIT_NO_MOVE:
            self.on_init(home=False)
        elif event == Key.INIT_HOME:
            self.on_init(home=True)
        elif event == Key.SETTINGS_POPUP:
            if not self.on_settings():
                return False
        elif event == Key.HELP_POPUP:
            layout.help_popup(layout.window_position(self.window))
        elif event in (Key.IRC_1, Key.IRC_2):
            self.on_irc(1 if event == Key.IRC_1 else 2)
        elif event == Key.LENS_IQ_CHECKBOX:
            self.on_lens_iq_checkbox(bool(values.get(Key.LENS_IQ_CHECKBOX)))
        elif event == Key.CAL_FILE_FULL:
            self.on_calibration_file(str(values.get(Key.CAL_FILE_FULL, "")))

        if self.lens_iq_active and self.iqep is not None:
            self.iqep.IQActions.readGUIValues = values
            self.iqep.checkEvents(event, values)

        if self.session is not None and (
            event in _RELATIVE_MOVES or event in _ABSOLUTE_MOVES
        ):
            self.on_move(event, values)
        return True

    # -- selection events -------------------------------------------------------------------

    def on_lens_selected(self, values: dict[str, Any]) -> None:
        """Switch lens variant, drop the motor state and re-validate any calibration file."""
        name = values.get(Key.LENS_FAMILY, "")
        key = next((v.key for v in self.variants.values() if v.name == name), "")
        if not key or key == self.lens_key:
            return
        self.actions.enable_live_frame(False)
        self.actions.enable_live_frame_abs(False)
        self.actions.enable_live_frame_irc(False)
        self.actions.enable_init_home_btn(self.variants[key].has_pi)
        if self.lens_iq_active and self.iqep is not None:
            self.iqep.IQActions.clearFields()
            self.iqep.IQActions.enableLiveFrame(False)
        self.actions.set_status("notInit")
        self.lens_key = key
        self.settings["last_lens_key"] = key
        self.configure_irc_buttons()

        if (
            not self.lens.has_pi
        ):  # no PI means no calibration tracking: hide the file picker
            self.uninitialize(motor_reset=True, cal_file_reset=True)
            self._set_cal_file_fields_visible(False)
        else:
            self.uninitialize(motor_reset=True, cal_file_reset=False)
            if values.get(Key.LENS_IQ_CHECKBOX):
                self._set_cal_file_fields_visible(True)
            if self.calibration_file and self.iqep is not None:
                cal_family = self.iqep.validateCalibrationFile(self.calibration_file)
                if cal_family and self.lens.fam in lens_data.compatible_families(
                    cal_family
                ):
                    self.load_calibration_file_data()
                else:
                    self._clear_calibration_file()
        self.window.visibility_changed()
        self.window.refresh()

    def on_port_selected(self, values: dict[str, Any]) -> None:
        """Remember the newly chosen serial port and drop any open session."""
        new_port = str(values.get(Key.PORT, ""))
        if new_port == self.com_port:
            return
        self.com_port = new_port
        self.settings["com_port"] = new_port
        self.uninitialize(motor_reset=True, cal_file_reset=False)
        self._close_session()

    def on_port_refresh(self) -> None:
        """Rescan serial ports; if the selected one vanished, pick the last one found."""
        self.port_list = [p.device for p in self._list_ports()]
        if self.com_port not in self.port_list:
            self.com_port = self.port_list[-1] if self.port_list else ""
            if self.com_port:
                self.settings["com_port"] = self.com_port
            self.uninitialize(motor_reset=True, cal_file_reset=False)
            self._close_session()
        self.window[Key.PORT].update(
            value=self.com_port, values=sorted(self.port_list), size=(18, 10)
        )

    # -- controller -------------------------------------------------------------------------

    def on_init(self, *, home: bool) -> None:
        """Handle the two initialize buttons; homing needs a lens with PI switches."""
        if not self.com_port:
            log.error("Serial port is blank")
            sg.popup_ok("Serial port is blank", title="Error")
            return
        if home and self.lens.has_pi:
            if self.init_mcr(home=True, regard_limits=True):
                self.load_calibration_file_data()
        else:
            self.uninitialize(motor_reset=False, cal_file_reset=True)
            self.init_mcr(home=False, regard_limits=False)

    def init_mcr(self, *, home: bool, regard_limits: bool) -> bool:
        """Connect (if needed) and initialize the motors for the selected lens; True on success."""
        self.actions.set_status("init")
        if self.session is None:
            try:
                self.session = self._connect(self.com_port, debug=MCR_DEBUG)
            except MCRError as error:
                log.error("%s: %s", error.message, error.detail)
                messages.show_error(error, self.com_port)
                self.actions.set_status("error")
                return False
        info = self.session.info
        self.window[Key.FW_REV].update(f"FW: {info.fw_revision or 'Unknown'}")
        self.window[Key.BOARD_SN].update(f"SN: {info.serial_number or 'Unknown'}")

        log.info("Initializing motors for %s", self.lens.name)
        try:
            self.session.init_motors(
                self.lens,
                home=home,
                respect_limits=regard_limits,
                speeds=MotorSpeeds.from_settings(self.settings),
                homing_speeds=MotorSpeeds.from_settings(self.settings, homing=True),
            )
        except MCRError as error:
            log.error("%s: %s", error.message, error.detail)
            messages.show_error(error, self.com_port)
            self.actions.set_status("error")
            return False

        self.configure_irc_buttons()
        self.window[Key.IRC_1].update(button_color=layout.IRC_SELECTED_COLOR)
        self.actions.set_regard_limits(regard_limits)
        self.actions.set_regard_backlash(True)
        self.actions.enable_live_frame(True, absolute_init=home)
        self.actions.enable_live_frame_irc(self.lens.has_irc)
        self.actions.enable_init_home_btn(self.lens.has_pi)
        if self.lens_iq_active and self.iqep is not None:
            self.iqep.initMotors(self.session.mcr, enableFields=regard_limits)
        self.update_position_fields()
        self.actions.set_status("ready")
        log.info("Lens initialized")
        return True

    def on_move(self, event: str, values: dict[str, Any]) -> None:
        """Run a relative or absolute move for the button or field that fired."""
        session = self._require_session()
        self.actions.set_status("moving")
        try:
            if event in _RELATIVE_MOVES:
                motor, sign = _RELATIVE_MOVES[event]
                steps = self._read_int(values, _STEP_FIELDS[motor])
                if steps is not None:
                    backlash = self.actions.regard_backlash
                    session.move_rel(motor, sign * steps, backlash=backlash)
                    self._after_move(motor)
            else:
                motor = _ABSOLUTE_MOVES[event]
                target = self._read_int(values, _CURRENT_FIELDS[motor])
                if target is not None and self.actions.abs_move_initialized:
                    session.move_abs(motor, target)
                    self._after_move(motor)
        except MCRError as error:
            log.error("%s", error.message)
            messages.show_error(error, self.com_port)
            self.actions.set_status("error")
            return
        self.actions.set_status("ready")

    def _after_move(self, motor: Motor) -> None:
        """Refresh the position field and notify the Lens IQ pack after `motor` moved."""
        self.window[_CURRENT_FIELDS[motor]].update(
            self._require_session().motor(motor).currentStep
        )
        if not (self.lens_iq_active and self.iqep is not None):
            return
        if motor == "zoom":
            self.iqep.updateAfterZoom()
        elif motor == "focus":
            self.iqep.updateAfterFocus(changeOD=False)
        else:
            self.iqep.updateAfterIris()

    def on_irc(self, state: Literal[1, 2]) -> None:
        """Switch the IRC filter and highlight the active button."""
        if self.session is None:
            return
        try:
            self.session.irc_state(state)
        except MCRError as error:
            messages.show_error(error, self.com_port)
            return
        self.window[Key.IRC_1].update(
            button_color=layout.IRC_SELECTED_COLOR if state == 1 else layout.DARK_BLUE
        )
        self.window[Key.IRC_2].update(
            button_color=layout.IRC_SELECTED_COLOR if state == 2 else layout.DARK_BLUE
        )

    def update_position_fields(self) -> None:
        """Copy the controller's tracked motor positions into the current-position fields."""
        for motor in ALL_MOTORS:
            self.window[_CURRENT_FIELDS[motor]].update(
                self._require_session().motor(motor).currentStep
            )

    def configure_irc_buttons(self) -> None:
        """Label the IRC buttons for the selected lens and reset their colors."""
        for key, label in zip(
            (Key.IRC_1, Key.IRC_2), self.lens.irc_labels(), strict=True
        ):
            self.window[key].update(label, button_color=layout.DARK_BLUE)

    # -- settings window --------------------------------------------------------------------

    def on_settings(self) -> bool:
        """Open the settings window and apply its result; False when a path change ends the app."""
        mcr = self.session.mcr if self.session is not None else None
        values = layout.settings_window(
            "USB", mcr, self.actions, layout.window_position(self.window)
        )
        if values is None:
            return True
        self.apply_settings_values(values)
        if not (values.get(SettingsKey.COM_UART) or values.get(SettingsKey.COM_I2C)):
            return True
        # the board leaves USB, so this program can no longer talk to it
        if not self.com_port:
            sg.popup_ok("Com path not changed: serial port is blank", title="Error")
            return True
        if self.session is None:
            try:
                self.session = self._connect(self.com_port, debug=MCR_DEBUG)
            except MCRError as error:
                messages.show_error(error, self.com_port)
                return True
        new_path: Literal["UART", "I2C"] = (
            "UART" if values.get(SettingsKey.COM_UART) else "I2C"
        )
        try:
            self.session.set_communication_path(new_path)
        except MCRError as error:
            messages.show_error(error, self.com_port)
            return True
        sg.popup_ok(
            f"New communication path was set to {new_path}. USB communication is no longer available and this application will end.",
            title="New com path",
        )
        return False

    def apply_settings_values(self, values: dict[str, Any]) -> None:
        """Push speeds to the board (saving accepted ones) and update the limit and backlash flags."""
        if self.session is not None:
            for homing, keys in (
                (
                    False,
                    (
                        SettingsKey.FOCUS_SPEED,
                        SettingsKey.ZOOM_SPEED,
                        SettingsKey.IRIS_SPEED,
                    ),
                ),
                (
                    True,
                    (
                        SettingsKey.FOCUS_HOME_SPEED,
                        SettingsKey.ZOOM_HOME_SPEED,
                        SettingsKey.IRIS_HOME_SPEED,
                    ),
                ),
            ):
                speeds = self._speeds_from_values(values, keys, homing=homing)
                if speeds is None:
                    continue
                accepted = self.session.set_speeds(speeds, homing=homing)
                suffix = "_home_speed" if homing else "_speed"
                for motor, ok in accepted.items():
                    if ok:
                        self.settings[f"{motor}{suffix}"] = speeds.get(motor)
        if values.get(SettingsKey.LIMIT_CHECK) is not None:
            state = bool(values[SettingsKey.LIMIT_CHECK])
            self.actions.set_regard_limits(state)
            if self.session is not None:
                self.session.set_respect_limits(state)
        if values.get(SettingsKey.BACKLASH) is not None:
            self.actions.set_regard_backlash(bool(values[SettingsKey.BACKLASH]))

    def _speeds_from_values(
        self, values: dict[str, Any], keys: tuple[str, str, str], *, homing: bool
    ) -> MotorSpeeds | None:
        """Parse the three speed fields; None when all are blank, current settings fill in blanks."""
        current = MotorSpeeds.from_settings(self.settings, homing=homing)
        raw = [str(values.get(k, "")).strip() for k in keys]
        if not any(raw):
            return None
        try:
            focus, zoom, iris = (
                int(r) if r else fallback
                for r, fallback in zip(
                    raw, (current.focus, current.zoom, current.iris), strict=True
                )
            )
        except ValueError:
            sg.popup_ok("Motor speeds must be whole numbers", title="Error")
            return None
        return MotorSpeeds(focus=focus, zoom=zoom, iris=iris)

    # -- Lens IQ ----------------------------------------------------------------------------

    def on_lens_iq_checkbox(self, checked: bool) -> None:
        """Show or hide the calibration file picker."""
        self._set_cal_file_fields_visible(checked)
        self.window.visibility_changed()
        self.window.refresh()
        if not checked:
            self.uninitialize(motor_reset=False, cal_file_reset=True)

    def on_calibration_file(self, filename: str) -> None:
        """Take the calibration file chosen in the browser and validate it."""
        if self.iqep is None:
            return
        self.window[Key.CAL_FILE].update(path.basename(filename))
        self.calibration_file = filename
        self.load_calibration_file_data()

    def load_calibration_file_data(self) -> None:
        """Validate the calibration file against the selected lens and enable the Lens IQ panel."""
        if not self.calibration_file or self.iqep is None:
            return
        cal_family = self.iqep.validateCalibrationFile(self.calibration_file)
        if cal_family is None:
            self.window[Key.CAL_FILE].update("")
            self.window[Key.CAL_FILE_FULL].update("")
            return
        lens = self.lens
        if lens.fam not in lens_data.compatible_families(cal_family):
            self.uninitialize(motor_reset=False, cal_file_reset=False)
            log.error(
                "Calibration file family %s is not compatible with lens family %s",
                cal_family,
                lens.fam,
            )
            sg.popup_ok(
                f"The calibration data file (lens family {cal_family}) is not compatible with the selected lens. Please select a compatible lens or a different calibration file.",
                title="Error",
            )
            return
        if not lens.has_pi:
            self.uninitialize(motor_reset=False, cal_file_reset=False)
            log.error(
                "Lens %s has no PI support required for calibration tracking", lens.name
            )
            sg.popup_ok(
                f"The selected lens ({lens.name}) does not support PI initialization and cannot use this calibration file.\nPlease select a lens with PI limit switches available.",
                title="Error",
            )
            return
        log.debug("Calibration file loaded for lens %s (fam %s)", lens.name, lens.fam)
        self.lens_iq_active = True
        self.window[Key.LENS_IQ_FRAME].update(visible=True)
        if (
            self.actions.status == "ready"
            and self.actions.regard_limits
            and self.session is not None
        ):
            self.iqep.initMotors(
                self.session.mcr, enableFields=self.actions.regard_limits
            )
        self.iqep.updateCalibrationFile()

    def uninitialize(
        self, *, motor_reset: bool = True, cal_file_reset: bool = True
    ) -> None:
        """Return the controls to the not-initialized state and optionally forget the calibration file."""
        if motor_reset:
            self.actions.set_status("notInit")
            self.actions.enable_live_frame(False)
            self.actions.enable_live_frame_abs(False)
            self.configure_irc_buttons()
            self.actions.enable_init_home_btn(self.lens.has_pi)
        if cal_file_reset:
            self._clear_calibration_file()
        if self.lens_iq_active and self.iqep is not None:
            self.lens_iq_active = False
            self.window[Key.LENS_IQ_FRAME].update(visible=False)
            self.iqep.resetControlInfo()
            self.iqep.IQActions.clearFields()
            self.iqep.IQActions.enableLiveFrame(False)
            if motor_reset and self.session is not None:
                self.iqep.motorsEnabled = False

    # -- helpers ----------------------------------------------------------------------------

    def _set_cal_file_fields_visible(self, visible: bool) -> None:
        for key in _CAL_FILE_KEYS:
            self.window[key].update(visible=visible)

    def _clear_calibration_file(self) -> None:
        self.calibration_file = ""
        self.window[Key.CAL_FILE].update("")
        self.window[Key.CAL_FILE_FULL].update("")

    def _close_session(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None

    @staticmethod
    def _read_int(values: dict[str, Any], key: str) -> int | None:
        """Parse a whole number from a field, showing a popup and returning None when invalid."""
        try:
            return int(str(values.get(key, "")).strip())
        except ValueError:
            sg.popup_ok("Enter a whole number of steps", title="Error")
            return None


def main(argv: list[str] | None = None) -> int:
    """Entry point of `theia-mcr-gui`."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s",
    )
    settings = Settings.load()
    variants = lens_data.flatten(resources.load_lens_data())
    if not variants:
        sg.popup_ok("Lens data file has no entries", title="Error")
        return 1
    return App(settings, variants).run()


if __name__ == "__main__":
    sys.exit(main())
