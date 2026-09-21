"""Window layouts and the small modal windows (settings, help)."""

from __future__ import annotations

import logging
import webbrowser
from typing import Any

import FreeSimpleGUI as sg

from theia_mcr_iq import resources
from theia_mcr_iq.gui import help_links
from theia_mcr_iq.gui.keys import Key, SettingsKey

log = logging.getLogger(__name__)

THEME = "LightGrey1"
WHITE = "#FFFFFF"
GREEN = "#006633"
DARK_BLUE = "#333399"
LIGHT_YELLOW = "#FFFFEC"
DARK_GRAY = "#666666"
IRC_SELECTED_COLOR = GREEN

# Helvetica is the one family Tk maps to a platform sans-serif everywhere.
FONT_SMALL = ("Helvetica", 8)
FONT_HEADER = ("Helvetica", 12, "underline")

Layout = list[list[Any]]


def apply_theme() -> None:
    """Set the global FreeSimpleGUI theme and button colors; call once before creating windows."""
    sg.theme(THEME)
    sg.set_options(
        button_color=[WHITE, DARK_BLUE], input_elements_background_color=LIGHT_YELLOW
    )


def _readonly_input(default: str, key: str, **kwargs: Any) -> sg.Input:
    """Input field styled the same way for every numeric field in the main window."""
    return sg.Input(
        default,
        size=(12, 1),
        justification="center",
        disabled_readonly_background_color=DARK_GRAY,
        key=key,
        **kwargs,
    )


def main_layout() -> Layout:
    """Main window: lens and port selection, motor moves, IRC filter, Lens IQ section, footer."""
    footer = [
        [
            sg.Text("v. rev.", size=(12, 1), font=FONT_SMALL, key=Key.REVISION),
            sg.Text("", size=(20, 1), font=FONT_SMALL, key=Key.FW_REV),
            sg.Text("", size=(20, 1), font=FONT_SMALL, key=Key.BOARD_SN),
            sg.Push(),
            sg.Image(
                data=resources.asset_bytes("help.png"),
                key=Key.HELP_POPUP,
                enable_events=True,
            ),
            sg.Image(
                data=resources.asset_bytes("cog.png"),
                key=Key.SETTINGS_POPUP,
                enable_events=True,
            ),
            sg.Button("Quit", size=(12, 1), key=Key.EXIT),
        ]
    ]
    header = [
        [
            sg.Column(
                [
                    [
                        sg.Text("Lens family", size=(10, 1)),
                        sg.Combo(
                            [], size=(18, 10), enable_events=True, key=Key.LENS_FAMILY
                        ),
                    ]
                ]
            )
        ],
        [
            sg.Column(
                [
                    [
                        sg.Text("Serial port", size=(10, 1)),
                        sg.Combo([], size=(18, 10), enable_events=True, key=Key.PORT),
                        sg.Button("Refresh", size=(6, 1), key=Key.PORT_REFRESH),
                    ]
                ]
            )
        ],
        [
            sg.Column(
                [
                    [
                        sg.Button(
                            "Initialize program\nand home motors",
                            size=(14, 2),
                            key=Key.INIT_HOME,
                        ),
                        sg.Button(
                            "Initialize without\nmoving motors",
                            size=(14, 2),
                            key=Key.INIT_NO_MOVE,
                        ),
                        sg.Frame(
                            "Status",
                            [
                                [
                                    sg.Text(
                                        "",
                                        key=Key.STATUS,
                                        size=(12, 1),
                                        justification="center",
                                    )
                                ]
                            ],
                        ),
                    ]
                ],
                element_justification="center",
                expand_x=True,
            )
        ],
    ]
    relative_moves = [
        [
            sg.Button("Tele", size=(12, 1), key=Key.MOVE_TELE),
            _readonly_input("1000", Key.ZOOM_STEP),
            sg.Button("Wide", size=(12, 1), key=Key.MOVE_WIDE),
        ],
        [
            sg.Button("Near", size=(12, 1), key=Key.MOVE_NEAR),
            _readonly_input("1000", Key.FOCUS_STEP),
            sg.Button("Far", size=(12, 1), key=Key.MOVE_FAR),
        ],
        [
            sg.Button("Open", size=(12, 1), key=Key.MOVE_OPEN),
            _readonly_input("10", Key.IRIS_STEP),
            sg.Button("Close", size=(12, 1), key=Key.MOVE_CLOSE),
        ],
    ]
    current_positions = [
        [_readonly_input("0", Key.ZOOM_CUR, pad=(6, 6))],
        [_readonly_input("0", Key.FOCUS_CUR, pad=(6, 6))],
        [_readonly_input("0", Key.IRIS_CUR, pad=(6, 6))],
    ]
    absolute_moves = [
        [sg.Button("Zoom", size=(12, 1), key=Key.MOVE_ZOOM_ABS, disabled=True)],
        [sg.Button("Focus", size=(12, 1), key=Key.MOVE_FOCUS_ABS, disabled=True)],
        [sg.Button("Iris", size=(12, 1), key=Key.MOVE_IRIS_ABS, disabled=True)],
    ]
    irc = [
        [
            sg.Text("Internal filter:", size=(12, 1)),
            sg.Button("Filter 1\n(Visible)", size=(11, 2), key=Key.IRC_1),
            sg.Button("Filter 2\n(Visible + IR)", size=(11, 2), key=Key.IRC_2),
        ]
    ]
    lens_iq_file = [
        [
            sg.Checkbox(
                "Lens IQ or calibrated lens was purchased from Theia and data file was downloaded.",
                key=Key.LENS_IQ_CHECKBOX,
                default=False,
                enable_events=True,
            )
        ],
        [
            sg.pin(sg.Text("Data file:", key=Key.CAL_FILE_TEXT, visible=False)),
            sg.pin(
                sg.Input(
                    "Select...",
                    key=Key.CAL_FILE,
                    disabled=True,
                    size=(30, 1),
                    visible=False,
                )
            ),
            sg.pin(
                sg.Input("", key=Key.CAL_FILE_FULL, visible=False, enable_events=True)
            ),
            sg.pin(
                sg.FileBrowse(
                    "Browse",
                    file_types=([("*.json", "*.json")]),
                    key=Key.CAL_FILE_BROWSE,
                    target=Key.CAL_FILE_FULL,
                    visible=False,
                )
            ),
        ],
    ]
    lens_iq = [
        [sg.Column(lens_iq_file, expand_x=True)],
        [
            sg.pin(
                sg.Column(
                    lens_iq_layout(),
                    expand_x=True,
                    visible=False,
                    key=Key.LENS_IQ_FRAME,
                )
            )
        ],
    ]
    return [
        [
            sg.Column(
                [
                    [
                        sg.Image(data=resources.asset_bytes("theia_logo.png")),
                        sg.Column(header),
                    ]
                ],
                expand_x=True,
            )
        ],
        [sg.Frame("Lens IQ™", lens_iq, expand_x=True)],
        [
            sg.Frame("Relative move", relative_moves),
            sg.Frame("Current", current_positions),
            sg.Frame("Absolute move", absolute_moves),
        ],
        [sg.Column(irc)],
        [sg.Frame("", footer, expand_x=True)],
    ]


def lens_iq_layout() -> Layout:
    """Lens IQ engineering-unit panel; its string keys are the contract of the expansion pack."""

    def sensor_field(label: str, key: str) -> sg.Column:
        return sg.Column(
            [
                [sg.Text(label, justification="center")],
                [
                    sg.Input(
                        "",
                        key=key,
                        size=(7, 1),
                        enable_events=True,
                        disabled=True,
                        disabled_readonly_background_color=DARK_GRAY,
                    )
                ],
            ]
        )

    sensor = [
        [
            sensor_field("Width [mm]", "sensorWd"),
            sensor_field("Diagonal [mm]", "sensorDiag"),
            sensor_field("W/Diag ratio", "sensorRatio"),
            sg.Button("Reset", key="resetBtn"),
        ]
    ]
    top = [
        [
            sg.Column(
                [
                    [sg.Frame("Image sensor", sensor)],
                    [
                        sg.Text(
                            "",
                            expand_x=True,
                            text_color="red",
                            font=FONT_SMALL,
                            visible=False,
                            key="sensorWarning",
                        )
                    ],
                ]
            ),
            sg.Column(
                [
                    [
                        sg.Text("Units"),
                        sg.Combo([], enable_events=True, key="unitList", size=(10, 1)),
                    ],
                    [
                        sg.Button(
                            "BFL calibration", size=(15, 1), key="btnBFL", disabled=True
                        )
                    ],
                    [sg.Text("", font=("Helvetica", 9), key="fldCurBFL")],
                ]
            ),
        ]
    ]
    parameters = [
        "Object distance",
        "Angle of view",
        "Field of view",
        "Focal length",
        "F/#",
        "Numeric aperture",
        "Depth of field",
    ]
    prefixes = ["OD", "AOV", "FOV", "FL", "FNum", "NA", "DOF"]
    units = ["m", "deg", "m", "mm", "", "", "m"]
    col_param = [
        [sg.Text("Parameter", size=(15, 1), justification="right", font=FONT_HEADER)]
    ]
    col_param += [
        [sg.Text(name, size=(15, 1), justification="right")] for name in parameters
    ]
    col_value: Layout = [
        [sg.Text("Value", size=(10, 1), justification="center", font=FONT_HEADER)]
    ]
    col_value += [
        [sg.Input("", size=(10, 1), key=f"{p}Value", disabled=(p == "DOF"))]
        for p in prefixes
    ]
    col_unit: Layout = [[sg.Text("")]] + [
        [sg.Text(u, size=(3, 1), key=f"{p}Units")]
        for p, u in zip(prefixes, units, strict=True)
    ]
    col_min: Layout = [
        [sg.Text("Minimum", size=(10, 1), justification="center", font=FONT_HEADER)]
    ]
    col_min += [
        [sg.Input("", size=(10, 1), key=f"{p}Min", disabled=True)] for p in prefixes
    ]
    col_max: Layout = [
        [sg.Text("Maximum", size=(10, 1), justification="center", font=FONT_HEADER)]
    ]
    col_max += [
        [sg.Input("", size=(10, 1), key=f"{p}Max", disabled=True)] for p in prefixes
    ]
    bottom = [
        [sg.Column([[sg.Text("", key="controlTextFld")]])],
        [
            sg.Column(col_param),
            sg.Column(col_value),
            sg.Column(col_unit),
            sg.Column(col_min),
            sg.Column(col_max),
        ],
    ]
    return [
        [sg.Column(top, expand_x=True)],
        [sg.Frame("Control", layout=bottom, expand_x=True)],
    ]


def bfl_layout() -> Layout:
    """BFL calibration window; its string keys are the contract of the expansion pack."""
    od_row = [
        [
            sg.Text("BFL calibration at OD"),
            sg.Input("", size=(10, 1), key="fldODCal"),
            sg.Text("", size=(4, 1), key="fldODSymbol"),
            sg.Button("Set OD", key="setODBtn", size=(16, 1)),
        ]
    ]
    fl_row = [
        [
            sg.Text("1. Select FL"),
            *[sg.Button("", key=f"preset{i}", size=(6, 1)) for i in range(5)],
            sg.Text("Other"),
            sg.Input("", size=(6, 1), key="fl_other"),
            sg.Text("mm"),
        ]
    ]
    focus_row = [
        [
            sg.Text("2. Find best focus"),
            sg.Button("near", key="focusNear", size=(10, 1)),
            sg.Input("100", size=(10, 1), key="focusSteps"),
            sg.Text("steps"),
            sg.Button("far", key="focusFar", size=(10, 1)),
        ]
    ]
    save_row = [
        [
            sg.Text("3. Save BFL data point"),
            sg.Button("Save", key="saveBtn", size=(16, 1)),
        ]
    ]
    graph = [
        [
            sg.Graph(
                canvas_size=(400, 200),
                graph_bottom_left=(0, 0),
                graph_top_right=(10, 10),
                background_color="white",
                key="BFLGraph",
                float_values=True,
                enable_events=True,
            )
        ]
    ]
    color_key = [
        [
            sg.Graph(
                canvas_size=(400, 50),
                graph_bottom_left=(0, 0),
                graph_top_right=(400, 50),
                background_color="white",
                key="BFLKey",
                border_width=2,
            )
        ]
    ]
    controls = [
        [
            sg.Button(
                "Copy BFL curve\ncoefficients (P0,P1,P2)", key="BFLCopy", size=(20, 2)
            ),
            sg.Button(
                "Delete selected\ndata point",
                key="btnDelBFL",
                disabled=True,
                size=(16, 2),
            ),
            sg.Button(
                "Clear all\ndata points", key="btnResetBFL", disabled=True, size=(16, 2)
            ),
        ]
    ]
    return [
        [sg.Column(od_row, expand_x=True)],
        [sg.Column(fl_row, expand_x=True)],
        [sg.Column(focus_row, expand_x=True)],
        [sg.Column(save_row, expand_x=True)],
        [sg.Column(graph, element_justification="center")],
        [sg.Column(color_key, expand_x=True)],
        [sg.Column(controls, expand_x=True, element_justification="center")],
        [
            sg.Column(
                [[sg.Button("BFL complete", key="exitBtn", size=(12, 1))]],
                expand_x=True,
                element_justification="center",
            )
        ],
    ]


def settings_window(
    initial_protocol: str, mcr: Any | None, actions: Any, position: tuple[int, int]
) -> dict[str, Any] | None:
    """Modal settings window; returns the entered values on Save, None on cancel or when not connected."""
    if mcr is None:
        sg.popup_ok("Motor control must be initialized first", title="Error")
        return None

    def speed_row(label: str, move_key: str, home_key: str) -> list[Any]:
        return [
            sg.Text(label, size=(16, 1)),
            sg.Input("", size=(7, 1), key=move_key, disabled=True),
            sg.Input("", size=(7, 1), key=home_key, disabled=True),
        ]

    speeds = [
        [
            sg.Text("", size=(16, 1)),
            sg.Text("Moving", size=(7, 1)),
            sg.Text("Homing", size=(7, 1)),
        ],
        speed_row(
            "Focus motor speed", SettingsKey.FOCUS_SPEED, SettingsKey.FOCUS_HOME_SPEED
        ),
        speed_row(
            "Zoom motor speed", SettingsKey.ZOOM_SPEED, SettingsKey.ZOOM_HOME_SPEED
        ),
        speed_row(
            "Iris motor speed", SettingsKey.IRIS_SPEED, SettingsKey.IRIS_HOME_SPEED
        ),
    ]
    communication = [
        [
            sg.Text(
                "Warning: Changing the communication path will reboot the controller board and the original communication path will no longer be active",
                size=(30, 4),
                text_color="red",
            )
        ],
        [sg.Button("Change com path", key=SettingsKey.CHANGE_PATH)],
        [
            sg.Radio(
                "USB",
                group_id="comGroup",
                default=(initial_protocol == "USB"),
                key=SettingsKey.COM_USB,
                visible=False,
            ),
            sg.Radio(
                "UART",
                group_id="comGroup",
                default=(initial_protocol == "UART"),
                key=SettingsKey.COM_UART,
                visible=False,
            ),
            sg.Radio(
                "I2C",
                group_id="comGroup",
                default=(initial_protocol == "I2C"),
                key=SettingsKey.COM_I2C,
                visible=False,
            ),
        ],
    ]
    extra = [
        [sg.Checkbox("Backlash", default=True, key=SettingsKey.BACKLASH)],
        [sg.Checkbox("Regard limits", default=True, key=SettingsKey.LIMIT_CHECK)],
    ]
    layout = [
        [sg.Frame("Motor speeds", speeds, expand_x=True)],
        [sg.Frame("Additional settings", extra)],
        [sg.Frame("Communication", communication)],
        [
            sg.Button("Save settings", key=SettingsKey.SAVE),
            sg.Button("Cancel", key=SettingsKey.DISCARD),
        ],
    ]
    window = sg.Window("Set values", layout, modal=True, finalize=True)
    center_window(window, position, 50)

    for motor, move_key, home_key in (
        ("focus", SettingsKey.FOCUS_SPEED, SettingsKey.FOCUS_HOME_SPEED),
        ("zoom", SettingsKey.ZOOM_SPEED, SettingsKey.ZOOM_HOME_SPEED),
        ("iris", SettingsKey.IRIS_SPEED, SettingsKey.IRIS_HOME_SPEED),
    ):
        motor_obj = getattr(mcr, motor)
        window[move_key].update(motor_obj.currentSpeed, disabled=False)
        window[home_key].update(motor_obj.homingSpeed, disabled=False)
    window[SettingsKey.BACKLASH].update(actions.regard_backlash)
    window[SettingsKey.LIMIT_CHECK].update(actions.regard_limits)

    while True:
        event, values = window.read()
        if event in {sg.WIN_CLOSED, SettingsKey.SAVE, SettingsKey.DISCARD}:
            break
        if event == SettingsKey.CHANGE_PATH:
            window[SettingsKey.CHANGE_PATH].update(visible=False)
            for key in (SettingsKey.COM_USB, SettingsKey.COM_UART, SettingsKey.COM_I2C):
                window[key].update(visible=True)
    window.close()
    return values if event == SettingsKey.SAVE else None


def help_popup(position: tuple[int, int]) -> None:
    """Modal window listing the help links; clicking one opens it in the browser."""
    links = help_links.help_init()
    if not links:
        sg.popup_ok("No help links available", title="Error")
        return
    layout: Layout = [
        [sg.Text(link["desc"], key=f"LINK{n}", enable_events=True)]
        for n, link in enumerate(links)
    ]
    layout.append([sg.Button("Close", size=(10, 1))])
    window = sg.Window("Help resources and links", layout, finalize=True, modal=True)
    center_window(window, position, 50)
    for n in range(len(links)):
        help_links.hyperlink(window, f"LINK{n}")
    while True:
        event, _ = window.read()
        if event in {sg.WIN_CLOSED, "Close"}:
            break
        if isinstance(event, str) and event.startswith("LINK"):
            url = links[int(event.removeprefix("LINK"))]["URL"]
            if url:
                webbrowser.open(url)
    window.close()


def window_position(window: Any) -> tuple[int, int]:
    """(x center, y top) of `window`, or (0, 0) when Tk cannot report it."""
    try:
        x, y = window.CurrentLocation()
        width, _ = window.Size
    except Exception:
        log.exception("Error getting main window position and size")
        return (0, 0)
    return (x + width // 2, y)


def center_window(window: Any, parent_position: tuple[int, int], y_shift: int) -> None:
    """Move `window` so it is centered under the parent's top edge, `y_shift` pixels down."""
    width, _ = window.size
    x, y = parent_position
    window.move((x or 400) - width // 2, (y or 200) + y_shift)
