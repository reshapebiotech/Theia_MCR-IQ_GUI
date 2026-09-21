"""Enable/disable groups of main-window controls and show the controller status."""

from __future__ import annotations

from typing import Any, Literal

from theia_mcr_iq.gui.keys import Key

Status = Literal["notInit", "init", "ready", "moving", "posUnknown", "error"]

STATUS_DISPLAY: dict[Status, tuple[str, str]] = {
    "notInit": ("Not initialized", "red"),
    "init": ("Initializing", "yellow"),
    "ready": ("Ready", "green"),
    "moving": ("Moving", "yellow"),
    "posUnknown": ("Position unknown", "lightgreen"),
    "error": ("ERROR", "red"),
}

_RELATIVE_CONTROLS = (
    Key.MOVE_TELE,
    Key.MOVE_WIDE,
    Key.MOVE_NEAR,
    Key.MOVE_FAR,
    Key.MOVE_OPEN,
    Key.MOVE_CLOSE,
    Key.ZOOM_CUR,
    Key.FOCUS_CUR,
    Key.IRIS_CUR,
    Key.ZOOM_STEP,
    Key.FOCUS_STEP,
    Key.IRIS_STEP,
)
_ABSOLUTE_CONTROLS = (Key.MOVE_ZOOM_ABS, Key.MOVE_FOCUS_ABS, Key.MOVE_IRIS_ABS)
_IRC_CONTROLS = (Key.IRC_1, Key.IRC_2)


class GuiActions:
    """UI-state helper for the main window; it never talks to the motor controller."""

    def __init__(self, window: Any, lens_iq_available: bool) -> None:
        """Bind to `window`; `lens_iq_available` gates whether the Lens IQ checkbox may ever be enabled."""
        self.window = window
        self.lens_iq_available = lens_iq_available
        self.abs_move_initialized = False
        self.regard_backlash = False
        self.regard_limits = False
        self.status: Status = "notInit"

    def enable_live_frame(
        self, enable: bool = True, absolute_init: bool = False
    ) -> None:
        """Enable the relative-move controls, and the absolute ones too when the motors were homed."""
        self.abs_move_initialized = absolute_init
        for key in _RELATIVE_CONTROLS:
            self.window[key].update(disabled=not enable)
        if absolute_init:
            self.enable_live_frame_abs(enable)

    def enable_live_frame_abs(self, enable: bool = True) -> None:
        """Enable the absolute-move buttons."""
        for key in _ABSOLUTE_CONTROLS:
            self.window[key].update(disabled=not enable)

    def enable_live_frame_irc(self, enable: bool = True) -> None:
        """Enable the IRC filter buttons."""
        for key in _IRC_CONTROLS:
            self.window[key].update(disabled=not enable)

    def enable_init_home_btn(self, enable: bool = True) -> None:
        """Enable the home-and-initialize button and the Lens IQ checkbox; both need a lens with PI."""
        self.window[Key.INIT_HOME].update(disabled=not enable)
        checkbox_enabled = enable and self.lens_iq_available
        self.window[Key.LENS_IQ_CHECKBOX].update(disabled=not checkbox_enabled)
        if not checkbox_enabled:
            self.window[Key.LENS_IQ_CHECKBOX].update(value=False)

    def set_regard_limits(self, state: bool = True) -> bool:
        """Record the limit-switch setting and mirror it on the absolute-move buttons."""
        self.regard_limits = state
        self.enable_live_frame_abs(state)
        return state

    def set_regard_backlash(self, state: bool = True) -> bool:
        """Record whether relative moves should apply backlash correction."""
        self.regard_backlash = state
        return state

    def set_status(self, status: Status = "notInit") -> None:
        """Show `status` in the status field with its color."""
        self.status = status
        text, color = STATUS_DISPLAY[status]
        self.window[Key.STATUS].update(text)
        self.window[Key.STATUS].update(background_color=color)
        self.window.refresh()
