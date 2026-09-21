"""Element keys and event names of the main window and the settings window."""

from __future__ import annotations

from enum import StrEnum


class Key(StrEnum):
    """Main window element keys; bound events reuse the field key with a suffix."""

    REVISION = "fldRevision"
    FW_REV = "fldFWRev"
    BOARD_SN = "fldSNBoard"
    HELP_POPUP = "helpPopup"
    SETTINGS_POPUP = "settingsPopup"
    EXIT = "exitBtn"
    LENS_FAMILY = "cp_lensFam"
    PORT = "cp_port"
    PORT_REFRESH = "cp_refresh"
    INIT_HOME = "motorInitHomeBtn"
    INIT_NO_MOVE = "motorInitBtn"
    STATUS = "fldStatus"
    MOVE_TELE = "moveTeleBtn"
    MOVE_WIDE = "moveWideBtn"
    MOVE_NEAR = "moveNearBtn"
    MOVE_FAR = "moveFarBtn"
    MOVE_OPEN = "moveOpenBtn"
    MOVE_CLOSE = "moveCloseBtn"
    ZOOM_STEP = "zoomStepFld"
    FOCUS_STEP = "focusStepFld"
    IRIS_STEP = "irisStepFld"
    ZOOM_CUR = "zoomCurFld"
    FOCUS_CUR = "focusCurFld"
    IRIS_CUR = "irisCurFld"
    ZOOM_CUR_UPDATE = "zoomCurFldUpdate"  # <Return> binding on ZOOM_CUR
    FOCUS_CUR_UPDATE = "focusCurFldUpdate"
    IRIS_CUR_UPDATE = "irisCurFldUpdate"
    MOVE_ZOOM_ABS = "moveZoomAbsBtn"
    MOVE_FOCUS_ABS = "moveFocusAbsBtn"
    MOVE_IRIS_ABS = "moveIrisAbsBtn"
    IRC_1 = "IRCBtn1"
    IRC_2 = "IRCBtn2"
    LENS_IQ_CHECKBOX = "lensIQCheckbox"
    CAL_FILE_TEXT = "calFileText"
    CAL_FILE = "calFile"
    CAL_FILE_FULL = "calFileFull"
    CAL_FILE_BROWSE = "calFileBrowse"
    LENS_IQ_FRAME = "lensIQControlFrame"


RETURN_BINDING_SUFFIX = "Update"


class SettingsKey(StrEnum):
    """Settings window element keys."""

    FOCUS_SPEED = "focusSpeed"
    ZOOM_SPEED = "zoomSpeed"
    IRIS_SPEED = "irisSpeed"
    FOCUS_HOME_SPEED = "focusHomeSpeed"
    ZOOM_HOME_SPEED = "zoomHomeSpeed"
    IRIS_HOME_SPEED = "irisHomeSpeed"
    CHANGE_PATH = "changePath"
    COM_USB = "comUSB"
    COM_UART = "comUART"
    COM_I2C = "comI2C"
    BACKLASH = "cp_backlash"
    LIMIT_CHECK = "cp_limitCheck"
    SAVE = "save"
    DISCARD = "discard"
