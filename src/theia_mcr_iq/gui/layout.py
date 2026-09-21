# GUI window creation for Theia_lensIQ_GUI
#
# v.1.0.0 250811 initial creation extracted from v.2.5.7 Theia_lensIQ_GUI.py
# v.2.0.0 250903 moved LensIQ GUI setup into this file

# pyright: reportOptionalMemberAccess=false

import FreeSimpleGUI as sg
from theia_mcr_iq import resources
from theia_mcr_iq.gui import help_links as help
import webbrowser as web

import logging
log = logging.getLogger(__name__)

TheiaColorTheme = 'LightGrey1'
TheiaWhiteColor = '#FFFFFF'
TheiaGreenColor = '#006633'
TheiaDarkBlueColor = '#333399'
TheiaLightYellowColor = "#FFFFEC"
TheiaDarkGrayColor = '#666666'  
TheiaRedColor = '#FF0000'
IRCSelectedColor = TheiaGreenColor                  # color for selected IRC filter

# mainGUILayout
def mainGUILayout():
    '''
    Main GUI layout. 
    Create the GUI window for the main window.  
    There is a live motor control section, measurement section, settings section, and optional monitor 
    section when the test is running.  
    The section for converting from engineering units to motor steps is supported by Lens IQ module functions.  
    ### input:  
    - settingsIconPath: the path to the settings gear icon
    ### return: 
    [handle to the window]
    '''
    sg.theme(TheiaColorTheme) 
    sg.set_options(button_color=[TheiaWhiteColor, TheiaDarkBlueColor], input_elements_background_color=TheiaLightYellowColor)
    # footer frame
    footerFrame = [
        [sg.Text(f'v. rev.', size=(12,1), font='Helvetica 8', key='fldRevision'),
            sg.Text('', size=(20,1), font='Helvetica 8', key='fldFWRev'),
            sg.Text('', size=(20,1), font='Helvetica 8', key='fldSNBoard'),
            sg.Push(),
            sg.Image(data=resources.asset_bytes('help.png'), key='helpPopup', enable_events=True),
            sg.Image(data=resources.asset_bytes('cog.png'), key='settingsPopup', enable_events=True),
            sg.Button('Quit', size=(12,1), key="exitBtn")]
    ]

    # Live lens motor control section
    # lens family sub-frame
    lensFamFrame = [
        [sg.Text('Lens family', size=(10,1)), sg.Combo([], size=(18,10), enable_events=True, key='cp_lensFam')]
        ]
    # comPort selection sub-frame
    comPortFrame = [
        [sg.Text('Com port', size=(10,1)), sg.Combo([], size=(18,10), enable_events=True, key="cp_port"), 
            sg.Button('Refresh', size=(6,1), key='cp_refresh')],
        ]
    # initialize motor control sub-frame
    initMotorsFrame = [
        [sg.Button('Initialize program\nand home motors', size=(14,2), key='motorInitHomeBtn'),
            sg.Button('Initialize without\nmoving motors', size=(14,2), key='motorInitBtn'),
            sg.Frame('Status', [[sg.Text('', key='fldStatus', size=(12,1), justification='center')]]) ]
        ]
    # lens header including picture and setup functions
    headerFrame = [
        [sg.Column(lensFamFrame)],
        [sg.Column(comPortFrame)],
        [sg.Column(initMotorsFrame, element_justification='center', expand_x=True)]
        ]

    # motor control sub-frames
    defaultSteps = '1000'
    relMoveFrame = [
        [sg.Button('Tele', size=(12,1), key='moveTeleBtn'), sg.Input(defaultSteps, size=(12,1), justification='center', disabled_readonly_background_color=TheiaDarkGrayColor, key='zoomStepFld'), 
            sg.Button('Wide', size=(12,1), key='moveWideBtn')],
        [sg.Button('Near', size=(12,1), key='moveNearBtn'), sg.Input(defaultSteps, size=(12,1), justification='center', disabled_readonly_background_color=TheiaDarkGrayColor, key='focusStepFld'), 
            sg.Button('Far', size=(12,1), key='moveFarBtn')],
        [sg.Button('Open', size=(12,1), key='moveOpenBtn'), sg.Input('10', size=(12,1), justification='center', disabled_readonly_background_color=TheiaDarkGrayColor, key='irisStepFld'), 
            sg.Button('Close', size=(12,1), key='moveCloseBtn')],
        ]
    curPosFrame = [
        [sg.Input('0', size=(12,1), pad=(6,6), justification='center', disabled_readonly_background_color=TheiaDarkGrayColor, key='zoomCurFld')],
        [sg.Input('0', size=(12,1), pad=(6,6), justification='center', disabled_readonly_background_color=TheiaDarkGrayColor, key='focusCurFld')],
        [sg.Input('0', size=(12,1), pad=(6,6), justification='center', disabled_readonly_background_color=TheiaDarkGrayColor, key='irisCurFld')],
        ]
    absMoveFrame = [
        [sg.Button('Zoom', size=(12,1), key='moveZoomAbsBtn', disabled=True)],
        [sg.Button('Focus', size=(12,1), key='moveFocusAbsBtn', disabled=True)],
        [sg.Button('Iris', size=(12,1), key='moveIrisAbsBtn', disabled=True)],
        ]
    IRCFrame = [
        [sg.Text('Internal filter:', size=(12,1)), sg.Button('Filter 1\n(Visible)', size=(11,2), key='IRCBtn1'), sg.Button('Filter 2\n(Visible + IR)', size=(11,2), key='IRCBtn2')]
        ]
    
    # lens IQ frames
    lensIQFileFrame = [
        [sg.Checkbox('Lens IQ or calibrated lens was purchased from Theia and data file was downloaded.', key='lensIQCheckbox', default=False, enable_events=True)],
        [sg.pin(sg.Text('Data file:', key='calFileText', visible=False)),
            sg.pin(sg.Input('Select...', key='calFile', disabled=True, size=(30,1), visible=False)),
            sg.pin(sg.Input('', key='calFileFull', visible=False, enable_events=True)),
            sg.pin(sg.FileBrowse('Browse', file_types=([('*.json', '*.json')]), key='calFileBrowse', target='calFileFull', visible=False))]
        ]
    lensIQLayoutFrame = lensIQGUILayout()
    lensIQFrame = [
        [sg.Column(lensIQFileFrame, expand_x=True)],
        [sg.pin(sg.Column(lensIQLayoutFrame, expand_x=True, visible=False, key='lensIQControlFrame'))]
    ]
                
    # overall layout
    layout = [
        [sg.Column([[sg.Image(data=resources.asset_bytes('theia_logo.png')), sg.Column(headerFrame)]], expand_x=True)],
        [sg.Frame('Lens IQ™', lensIQFrame, expand_x=True)],
        [sg.Frame('Relative move', relMoveFrame), sg.Frame('Current', curPosFrame), sg.Frame('Absolute move', absMoveFrame)],
        [sg.Column(IRCFrame)],
        [sg.Frame('', footerFrame, expand_x=True)]
    ]
    return layout

# display revision
def setRevisionField(window, rev:str=''):
    if not window:
        return
    window['fldRevision'].update(f'v. {rev}')

# Lens IQ GUI layout
def lensIQGUILayout():
    '''
    Layout for Lens IQ fields.  
    ### return: 
    [lensIQ Frame layout]
    '''
    # top layout for setup functions
    sensorLayout = [
        [sg.Column([
            [sg.Text('Width [mm]', justification='center')], 
            [sg.Input('', key='sensorWd', size=(7,1), enable_events=True, disabled=True, disabled_readonly_background_color=TheiaDarkGrayColor)]
            ]),
        sg.Column([
            [sg.Text('Diagonal [mm]', justification='center')],
            [sg.Input('', size=(7,1), key='sensorDiag', enable_events=True, disabled=True, disabled_readonly_background_color=TheiaDarkGrayColor)]
            ]),
        sg.Column([
            [sg.Text('W/Diag ratio', justification='center')],
            [sg.Input('', size=(7,1), key='sensorRatio', enable_events=True, disabled=True, disabled_readonly_background_color=TheiaDarkGrayColor)]
            ]),
        sg.Button('Reset', key='resetBtn'),
        ]
    ]
    topLayout = [
        [sg.Column([
            [sg.Frame('Image sensor', sensorLayout)],
            [sg.Text('', expand_x=True, text_color='red', font=('Calibri', 8), visible=False, key='sensorWarning')]
            ]),
        sg.Column([
            [sg.Text('Units'), sg.Combo([], enable_events=True, key='unitList', size=(10,1))],
            [sg.Button('BFL calibration', size=(15,1), key='btnBFL', disabled=True)],
            [sg.Text('', font=('Calibri 9'), key='fldCurBFL')]
            ])
        ]
    ]
    # bottom layout for interaction
    col1Wd = 15
    colParam = [
        [sg.Text('Parameter', size=(col1Wd,1), justification='right', font=('Calibri 12 underline'))],
        [sg.Text('Object distance', size=(col1Wd,1), justification="right")],
        [sg.Text('Angle of view', size=(col1Wd,1), justification="right")],
        [sg.Text('Field of view', size=(col1Wd,1), justification="right")],
        [sg.Text('Focal length', size=(col1Wd,1), justification="right")],
        [sg.Text('F/#', size=(col1Wd,1), justification="right")],
        [sg.Text('Numeric aperture', size=(col1Wd,1), justification="right")],
        [sg.Text('Depth of field', size=(col1Wd,1), justification="right")],
    ]
    col2Wd = 10
    colValue = [
        [sg.Text('Value', size=(col2Wd,1), justification='center', font=('Calibri 12 underline'))],
        [sg.Input('', size=(col2Wd,1), key='ODValue')],
        [sg.Input('', size=(col2Wd,1), key='AOVValue')],
        [sg.Input('', size=(col2Wd,1), key='FOVValue')],
        [sg.Input('', size=(col2Wd,1), key='FLValue')],
        [sg.Input('', size=(col2Wd,1), key='FNumValue')],
        [sg.Input('', size=(col2Wd,1), key='NAValue')],
        [sg.Input('', size=(col2Wd,1), key='DOFValue', disabled=True)],
    ]
    col3Wd = 3
    colUnit = [
        [sg.Text('')],
        [sg.Text('m', size=(col3Wd,1), key='ODUnits')],
        [sg.Text('deg', size=(col3Wd,1), key='AOVUnits')],
        [sg.Text('m', size=(col3Wd,1), key='FOVUnits')],
        [sg.Text('mm', size=(col3Wd,1), key='FLUnits')],
        [sg.Text('', size=(col3Wd,1), key='FNumUnits')],
        [sg.Text('', size=(col3Wd,1), key='NAUnits')],
        [sg.Text('m', size=(col3Wd,1), key='DOFUnits')],
    ]
    col4Wd = 10
    colMin = [
        [sg.Text('Minimum', size=(col4Wd,1), justification='center', font=('Calibri 12 underline'))],
        [sg.Input('', size=(col4Wd,1), key='ODMin', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='AOVMin', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='FOVMin', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='FLMin', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='FNumMin', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='NAMin', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='DOFMin', disabled=True)],
    ]
    colMax = [
        [sg.Text('Maximum', size=(col4Wd,1), justification='center', font=('Calibri 12 underline'))],
        [sg.Input('', size=(col4Wd,1), key='ODMax', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='AOVMax', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='FOVMax', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='FLMax', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='FNumMax', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='NAMax', disabled=True)],
        [sg.Input('', size=(col4Wd,1), key='DOFMax', disabled=True)],
    ]
    topLineLayout = [
        [sg.Text('', key='controlTextFld')]
    ]
    bottomLayout = [
        [sg.Column(topLineLayout)],
        [sg.Column(colParam), sg.Column(colValue), sg.Column(colUnit), sg.Column(colMin), sg.Column(colMax)]
    ]
    layout = [
        #[sg.Frame('Setup', layout=topLayout, expand_x=True)],
        [sg.Column(topLayout, expand_x=True)],
        [sg.Frame('Control', layout=bottomLayout, expand_x=True)]
    ]

    return layout

# BFL calibration window layout
def bflLayout():
    '''
    Create the BFL calibration window layout (experimental design).
    ### return:  
    [BFL window layout]
    '''
    # OD calibration row
    odLayout = [
        [sg.Text("BFL calibration at OD"), 
         sg.Input('', size=(10,1), key='fldODCal'), 
         sg.Text('', size=(4,1), key='fldODSymbol'),
         sg.Button("Set OD", key='setODBtn', size=(16,1))]
    ]
    
    # FL selection row
    flLayout = [
        [sg.Text("1. Select FL"), 
         sg.Button('', key='preset0', size=(6,1)), 
         sg.Button('', key='preset1', size=(6,1)), 
         sg.Button('', key='preset2', size=(6,1)), 
         sg.Button('', key='preset3', size=(6,1)), 
         sg.Button('', key='preset4', size=(6,1)), 
         sg.Text('Other'), 
         sg.Input('', size=(6,1), key='fl_other'), 
         sg.Text('mm')]
    ]
    
    # Focus control row
    focusLayout = [
        [sg.Text('2. Find best focus'), 
         sg.Button('near', key='focusNear', size=(10,1)), 
         sg.Input('100', size=(10,1), key='focusSteps'), 
         sg.Text('steps'),
         sg.Button('far', key='focusFar', size=(10,1))]
    ]

    # save row
    saveLayout = [
         [sg.Text('3. Save BFL data point'), sg.Button('Save', key='saveBtn', size=(16,1))]
    ]
    
    # Graph
    graphLayout = [
        [sg.Graph(canvas_size=(400, 200), 
                  graph_bottom_left=(0,0), 
                  graph_top_right=(10,10),
                  background_color='white', 
                  key='BFLGraph', 
                  float_values=True, 
                  enable_events=True)]
    ]

    # color key
    keyLayout = [
        [sg.Graph(canvas_size=(400, 50), graph_bottom_left=(0,0), graph_top_right=(400,50),
            background_color='white', key='BFLKey', border_width=2)]
    ]
    # Control buttons
    controlLayout = [
        [sg.Button('Copy BFL curve\ncoefficients (P0,P1,P2)', key='BFLCopy', size=(20,2)),
         sg.Button('Delete selected\ndata point', key='btnDelBFL', disabled=True, size=(16,2)), 
         sg.Button('Clear all\ndata points', key='btnResetBFL', disabled=True, size=(16,2))
        ]
    ]
    
    # Close button
    bottomLayout = [
        [sg.Button('BFL complete', key='exitBtn', size=(12,1))]
    ]

    # Overall layout
    layout = [
        [sg.Column(odLayout, expand_x=True)],
        [sg.Column(flLayout, expand_x=True)],
        [sg.Column(focusLayout, expand_x=True)],
        [sg.Column(saveLayout, expand_x=True)],
        [sg.Column(graphLayout, element_justification='center')],
        [sg.Column(keyLayout, expand_x=True)],
        [sg.Column(controlLayout, expand_x=True, element_justification='center')],
        [sg.Column(bottomLayout, expand_x=True, element_justification='center')]
    ]

    return layout

# setting window 
def settingsGUI(initialProtocol:str, MCR, GUIActions, position:tuple[int, int]) -> dict | None:
    '''
    Create a window for additional settings.  This function handles the window and returns the values once it is closed.  
    This window includes communication path and motor speeds.  
    Once set by the user, the motor speeds are written to the board and the communication path is updated.  
    If the user cancels, nothing is changed and the return value is 'None'.  
    ### input:
    - initialProtocol: current communication path string ('USB', 'UART', 'I2C')
    - MCR: the handle to the MCR module
    - GUIActions: the handle to the GUI actions module
    - position: the (x (center), y (top)) position to place the window
    ### return: 
    [settings values | None]
    '''
    # check if MCR is initialized
    if not MCR:
        sg.popup_ok('Motor control must be initialized first', title='Error')
        return None

    # motor speeds
    speedsLayout = [
        [sg.Text('', size=(16,1)), sg.Text('Moving', size=(7,1)), sg.Text('Homing', size=(7,1))],
        [sg.Text('Focus motor speed', size=(16,1)), sg.Input('', size=(7,1), key='focusSpeed', disabled=True), sg.Input('', size=(7,1), key='focusHomeSpeed', disabled=True)],
        [sg.Text('Zoom motor speed', size=(16,1)), sg.Input('', size=(7,1), key='zoomSpeed', disabled=True), sg.Input('', size=(7,1), key='zoomHomeSpeed', disabled=True)],
        [sg.Text('Iris motor speed', size=(16,1)), sg.Input('', size=(7,1), key='irisSpeed', disabled=True), sg.Input('', size=(7,1), key='irisHomeSpeed', disabled=True)],
    ]
    # communication path
    comLayout = [
        [sg.Text('Warning: Changing the communication path will reboot the controller board and the original communication path will no longer be active', 
                    size=(30,4), text_color='red')],
        [sg.Button('Change com path', key='changePath')],
        [sg.Radio('USB', group_id='comGroup', default=(initialProtocol == 'USB'), key='comUSB', visible=False), 
            sg.Radio('UART', group_id='comGroup', default=(initialProtocol == 'UART'), key='comUART', visible=False), 
            sg.Radio('I2C', group_id='comGroup', default=(initialProtocol == 'I2C'), key='comI2C', visible=False)]
    ]
    # additional settings
    addLayout = [
        [sg.Checkbox('Backlash', default=True, key='cp_backlash')],
        [sg.Checkbox('Regard limits', default=True, key='cp_limitCheck')]
    ]
    layout = [
        [sg.Frame('Motor speeds', speedsLayout, expand_x=True)], 
        [sg.Frame('Additional settings', addLayout)],
        [sg.Frame('Communication', comLayout)],
        [sg.Button('Save settings', key='save'), sg.Button('Cancel', key='discard')]
    ]

    window = sg.Window('Set values', layout, modal=True, finalize=True)
    centerWindowPosition(window, position, 50)

    if MCR.MCRInitialized:
        window['focusSpeed'].update(MCR.focus.currentSpeed)
        window['focusSpeed'].update(disabled=False)
        window['focusHomeSpeed'].update(MCR.focus.homingSpeed)
        window['focusHomeSpeed'].update(disabled=False)
        window['zoomSpeed'].update(MCR.zoom.currentSpeed)
        window['zoomSpeed'].update(disabled=False)
        window['zoomHomeSpeed'].update(MCR.zoom.homingSpeed)
        window['zoomHomeSpeed'].update(disabled=False)
        window['irisSpeed'].update(MCR.iris.currentSpeed)
        window['irisSpeed'].update(disabled=False)
        window['irisHomeSpeed'].update(MCR.iris.homingSpeed)
        window['irisHomeSpeed'].update(disabled=False)
        window['cp_backlash'].update(GUIActions.regardBacklash)
        window['cp_limitCheck'].update(GUIActions.regardLimits)

    while True:
        event, values = window.read() # type: ignore
        if event in {sg.WIN_CLOSED, 'save', 'discard'}:
            break
        elif event == 'changePath':
            window['changePath'].update(visible=False)
            window['comUSB'].update(visible=True)
            window['comUART'].update(visible=True)
            window['comI2C'].update(visible=True)
    window.close()
    if event == 'save': 
        return values
    return None

# help popup window
def helpPopup(position:tuple[int, int]):
    '''
    Open the help popup window with resources and links.
    ### input: 
    - position: the (x (center), y (top)) position to place the window
    '''
    helpLinks = help.help_init()
    if not helpLinks:
        sg.popup_ok('No help links available', title='Error')
        return
    layout = []
    for n, link in enumerate(helpLinks):
        layout.append([sg.Text(link['desc'], key=f'LINK{n}', enable_events=True)])
    layout.append([sg.Button('Close', size=(10,1))])

    window = sg.Window('Help resources and links', layout, finalize=True, modal=True)
    centerWindowPosition(window, position, 50)
    for n in range(len(helpLinks)):
        help.hyperlink(window=window, fieldKey=f'LINK{n}')

    while True:
        event, values = window.read() # type: ignore
        if event in {sg.WIN_CLOSED, 'Close'}:
            break
    
        elif event.startswith('LINK'):
            index = int(event.replace('LINK', ''))
            URL = helpLinks[index]['URL']
            if URL:
                web.open(URL)
    window.close()

# get the main window size and position
def windowPosition(mainGUIWindow) -> tuple:
    '''
    Get the main window x center and y top positions. 
    ### input: 
    - mainGUIWindow: the handle to the main GUI window
    ### return: 
    [
    (x,y)          # window (x center, y top) position
    ]
    '''
    try:
        x, y = mainGUIWindow.CurrentLocation()
        width, height = mainGUIWindow.Size
    except Exception as e:
        log.error(f'Error getting main window position and size: {e}')
        return (0,0)
    xCenter = x + int(width/2)
    yTop = y
    return (xCenter, yTop)
    
# move the window
def centerWindowPosition(window, parentPosition:tuple[int, int], yShift:int):
    '''
    Move the window to the center (x) of the main window.  
    ### input:
    - window: the window handle for the window to move
    - parentPosition: the (x (center), y (top)) position of the main window
    - yShift: the pixels to shift below the top of the main window.  
    '''
    size = window.size
    x, y = parentPosition
    if x == 0:
        x = 400
    if y == 0:
        y = 200
    window.move(x - int(size[0]/2), y + yShift)