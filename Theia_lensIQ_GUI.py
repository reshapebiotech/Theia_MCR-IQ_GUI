# Live GUI motor control and Lens IQ engineering unit conversion application
# (c) 2025 Theia Technologies LLC
# contact Mark Peterson at mpeterson@theiatech.com for more information

# pyright: reportOptionalMemberAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportArgumentType=false

import FreeSimpleGUI as sg
import logging
import TheiaMCR
import sys
from os import path
import utilities
import GUI_setup
import read_settings_files as settingsFiles
import GUI_actions
import lensIQ_expansion
from typing import Optional
import threading

# logging setup
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')
# set TheiaMCR sub module log level
MCRDebugLogLevel = False

# application revision
REVISION = '3.1.0'

settingsFileName = 'Motor control config.json'
lensDataFileName = 'limits.json'                   # lens data (names and extents)
dataSetQRCode = utilities.resourcePath('config/QR-Dropbox-lensIQ-dataset.png')    # QR code for the lens data file

# create the main window GUI layout
def createMainGUI():
    '''
    Call the GUI creation function in GUI_setup.py.  
    Fill in the values of some fields.  
    '''
    global mainGUIWindow
    layout = GUI_setup.mainGUILayout()
    mainGUIWindow = sg.Window('Theia MCR IQ™ control', layout, finalize=True)
    GUI_setup.setRevisionField(mainGUIWindow, REVISION)
    
    # key bindings
    mainGUIWindow['zoomCurFld'].bind('<Return>', 'Update')
    mainGUIWindow['focusCurFld'].bind('<Return>', 'Update')
    mainGUIWindow['irisCurFld'].bind('<Return>', 'Update')

    # field updates
    mainGUIWindow['cp_lensFam'].update(value = lastLensFamily, values = lensFamiliesList, size=(18,10))
    mainGUIWindow['cp_port'].update(value = comPort, values = sorted(comPortList), size=(18,10))

    actions = GUI_actions.GUIActions(mainGUIWindow) 
    actions.setStatus('notInit')
    actions.enableLiveFrame(False)
    return actions
    
# setup lens parameters
def selectLens(name:str) -> tuple[str, list]:
    '''
    Set up lens parameters focus steps, focus PI step, zoom steps, zoom PI step, iris steps. 
    Based on lens model number, return the configuration and serial number prefix ('TW90').  
    ### input
    - name: lens family name (see lensFamiliesList variable for names. )
    ### return
    [
        prefix = ['TW50' | 'TW60' | 'TW80' | 'TW90' | 'TW46'],
        lensConfig = [zoom steps, zoom PI, focus steps, focus PI, iris steps]
    '''
    log.info(f"Select {name}")
    prefix = lensData[name]['fam']
    lensConfig = [lensData[name]['zoomSteps'], lensData[name]['zoomPI'], lensData[name]['focusSteps'], lensData[name]['focusPI'], lensData[name]['irisSteps']]
    return prefix, lensConfig

# check for a new lens family
def checkNewLensFamily(newLensFamily:str) -> str|None:
    '''
    Check if the selected lens family is different from the last lens family.
    If there is no change or no family specified, return None.  
    ### input: 
    - newLensFamily: the new lens family name
    ### return: 
    [None | new lens family name]
    '''
    if newLensFamily == None:
        return None
    
    if newLensFamily != lastLensFamily:
        actions.enableLiveFrame(False)
        actions.enableLiveFrameAbs(False)
        if enableLensIQFunctions: 
            IQEP.IQActions.clearFields()
            IQEP.IQActions.enableLiveFrame(False)
        actions.setStatus('notInit')
    else:
        return None
    return newLensFamily

# check if COM port is available
def isComPortAvailable(portName:str, timeout:float=2.0) -> tuple[bool, str]:
    '''
    Check if a COM port is available for connection (not already in use).
    Uses a timeout to prevent hanging on problematic ports (e.g., Bluetooth).
    ### input:
    - portName: COM port name (e.g. 'COM3')
    - timeout: timeout in seconds (default 2.0)
    ### return:
    [is_available (bool), error_message (str)]
    '''
    import serial
    result = {'success': False, 'error': None}
    
    def worker():
        try:
            # Try to open the port briefly
            test_port = serial.Serial(
                port=portName,
                baudrate=115200,
                timeout=0.1
            )
            test_port.close()
            result['success'] = True
        except serial.SerialException as e:
            error_msg = str(e).lower()
            if 'permissionerror' in error_msg or 'access is denied' in error_msg or 'in use' in error_msg or 'cannot access' in error_msg:
                result['error'] = f"Port {portName} is already in use by another application"
            else:
                result['error'] = f"Port {portName} error: {str(e)}"
        except Exception as e:
            result['error'] = f"Unexpected error checking port {portName}: {str(e)}"
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        # Timeout occurred - port is problematic (likely wrong port type like Bluetooth)
        log.warning(f'Port availability check timed out for {portName} after {timeout} seconds')
        return False, f"Port {portName} is unresponsive (may be wrong device type, e.g., Bluetooth adapter)"
    
    if result['error'] is not None:
        return False, result['error']
    
    return result['success'], ""

# timeout wrapper for MCR initialization
def initMCRWithTimeout(MCRCom:str, timeout:float=5.0) -> tuple[Optional[TheiaMCR.MCRControl], bool]:
    '''
    Initialize MCR with a timeout to prevent freezing on incorrect COM ports.
    ### input:
    - MCRCom: COM port name
    - timeout: timeout in seconds (default 5.0)
    ### return:
    [MCR object or None, success flag]
    '''
    result = {'MCR': None, 'error': None}
    
    def worker():
        try:
            result['MCR'] = TheiaMCR.MCRControl(MCRCom, moduleDebugLevel=MCRDebugLogLevel)
        except Exception as e:
            result['error'] = str(e)
            log.error(f'Exception during MCR initialization: {e}')
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        # Timeout occurred
        log.error(f'MCR initialization timed out after {timeout} seconds')
        return None, False
    
    if result['error'] is not None:
        return None, False
        
    return result['MCR'], True
    
# initialize motor controller
def initMCR(MCRCom:str, lensFam:str='', homeMotors:bool=True, regardLimits:bool=True) -> bool:
    '''
    Initialize the motor controller. 
    Regardlimits are set at the MCRControl.py level, not this local level
    RegardBacklash is set at the local level so moves can vary this setting
    ### input: 
    - MCRCom: comPort for MCR controllerlensConfig parameters if available
    - lensFam (optional: ''): lens family string (see variable lensFamiliesList for names)
    - homeMotors (optional: True): true to move motors to home positions
    - regardLimits (optional: True): regard the limit switches and do not exceed
    ### return: 
    [initialized state]
    '''
    global MCR
    actions.setStatus('init')
    if lensFam != '':
        # initialize configuration
        _, lensConfig = selectLens(lensFam)
    if not MCR:
        # Pre-check if COM port is available before attempting connection
        portAvailable, errorMsg = isComPortAvailable(MCRCom)
        if not portAvailable:
            log.error(f'** {errorMsg}')
            
            # Show appropriate error message
            if 'already in use' in errorMsg.lower():
                displayMsg = f'COM port {MCRCom} is already in use!\n\n'
                displayMsg += 'Another application is already connected to this port.\n\n'
                displayMsg += 'To resolve this issue:\n'
                displayMsg += '  • Close any other instances of this application\n'
                displayMsg += '  • Close other programs using this COM port\n'
                displayMsg += '  • Check Device Manager for port conflicts\n'
                displayMsg += '  • Try unplugging and reconnecting the USB cable'
                sg.popup_ok(displayMsg, title='COM Port Already In Use')
            elif 'unresponsive' in errorMsg.lower() or 'bluetooth' in errorMsg.lower():
                displayMsg = f'COM port {MCRCom} is not responding!\n\n'
                displayMsg += 'This usually means you selected the wrong type of COM port.\n\n'
                displayMsg += 'Common incorrect ports:\n'
                displayMsg += '  • Bluetooth adapters ("Standard Serial over Bluetooth link")\n'
                displayMsg += '  • GPS devices\n'
                displayMsg += '  • Other virtual COM ports\n\n'
                displayMsg += 'Please select a different COM port that corresponds to\n'
                displayMsg += 'the USB connection to your motor controller board.'
                sg.popup_ok(displayMsg, title='Wrong COM Port Type')
            else:
                sg.popup_ok(errorMsg, title='COM Port Unavailable')
            
            actions.setStatus('error')
            return False
        
        # Use timeout wrapper to prevent freezing on incorrect COM ports
        log.info(f'Attempting to connect to {MCRCom}...')
        MCR, initSuccess = initMCRWithTimeout(MCRCom, timeout=5.0) # type: ignore
        
        if not initSuccess or MCR is None:
            log.error('** MCR initialization timed out or failed')
            errorMsg = 'Motor controller initialization failed or timed out.\n\n'
            errorMsg += 'This often happens when connecting to incorrect COM ports\n'
            errorMsg += '(e.g., Bluetooth adapters, GPS devices, etc.)\n\n'
            errorMsg += 'Possible causes:\n'
            errorMsg += '  • Wrong COM port selected\n'
            errorMsg += '  • Board not connected or powered\n'
            errorMsg += '  • USB cable disconnected\n'
            errorMsg += '  • COM port already in use by another application\n'
            errorMsg += '  • Board firmware issue'
            sg.popup_ok(errorMsg, title='Connection Failed')
            MCR = None
            actions.setStatus('error')
            return False
        
        # Check if board initialization failed (not just class initialization)
        if not MCR.boardInitialized:
            log.error('** MCR board initialization failed - check COM port, connection, and power')
            
            # Check if the error was due to port already in use
            portInUse = False
            try:
                if hasattr(MCR, 'com') and MCR.com:
                    serialException = getattr(MCR.com, 'serialPortException', None)
                    if serialException:
                        error_msg = serialException.lower()
                        if 'permissionerror' in error_msg or 'access is denied' in error_msg or 'in use' in error_msg or 'cannot access' in error_msg:
                            portInUse = True
            except:
                pass  # If we can't determine the error type, show generic message
            
            if portInUse:
                errorMsg = f'COM port {MCRCom} is already in use!\n\n'
                errorMsg += 'Another application is already connected to this port.\n\n'
                errorMsg += 'To resolve this issue:\n'
                errorMsg += '  • Close any other instances of this application\n'
                errorMsg += '  • Close other programs using this COM port\n'
                errorMsg += '  • Check Device Manager for port conflicts\n'
                errorMsg += '  • Try unplugging and reconnecting the USB cable'
                sg.popup_ok(errorMsg, title='COM Port Already In Use')
            else:
                errorMsg = 'Motor controller board initialization failed.  Possible causes:\n'
                errorMsg += '  • Wrong COM port selected\n'
                errorMsg += '  • Board not connected or powered\n'
                errorMsg += '  • USB cable disconnected\n'
                errorMsg += '  • COM port already in use by another application\n'
                errorMsg += '  • Board firmware issue'
                sg.popup_ok(errorMsg, title='Board Initialization Failed')
            
            MCR = None
            actions.setStatus('error')
            return False
        
    # Read and display firmware revision and serial number with error handling
    try:
        fwRevision = MCR.MCRBoard.readFWRevision()
        if fwRevision:
            mainGUIWindow['fldFWRev'].update(f'FW: {fwRevision}')
        else:
            mainGUIWindow['fldFWRev'].update('FW: Unknown')
            log.warning('** Could not read firmware revision')
    except Exception as e:
        log.error(f'** Failed to read firmware revision: {e}')
        return False
    
    try:
        boardSN = MCR.MCRBoard.readBoardSN()
        if boardSN:
            mainGUIWindow['fldSNBoard'].update(f'SN: {boardSN}')
        else:
            mainGUIWindow['fldSNBoard'].update('SN: Unknown')
            log.warning('** Could not read board serial number')
    except Exception as e:
        log.error(f'** Failed to read board serial number: {e}')
        return False
    
    log.info('Initializing motors')
    MCR.focusInit(lensConfig[2], lensConfig[3], move=homeMotors)
    MCR.zoomInit(lensConfig[0], lensConfig[1], move=homeMotors)
    MCR.irisInit(lensConfig[4], move=homeMotors)
    MCR.IRCInit()
    MCR.IRC.state(1)
    mainGUIWindow['IRCBtn1'].update(button_color=GUI_setup.IRCSelectedColor)
    # set initial motor speeds
    setMotorSpeeds(settings.get('focusSpeed', 1000), settings.get('zoomSpeed', 1000), settings.get('irisSpeed', 100))
    setHomeSpeeds(settings.get('focusHomingSpeed', 1000), settings.get('zoomHomingSpeed', 1000), settings.get('irisHomingSpeed', 100))

    # initialize GUI settings
    actions.setRegardLimits(regardLimits)
    MCR.focus.setRespectLimits(regardLimits)
    MCR.zoom.setRespectLimits(regardLimits)
    actions.setRegardBacklash(True)
    actions.enableLiveFrame(True, absoluteInit=homeMotors)

    if enableLensIQFunctions: IQEP.initMotors(MCR, enableFields=regardLimits)

    # set current motor steps (PI positions)
    mainGUIWindow['focusCurFld'].update(MCR.focus.currentStep)
    mainGUIWindow['zoomCurFld'].update(MCR.zoom.currentStep)
    mainGUIWindow['irisCurFld'].update(MCR.iris.currentStep)

    actions.setStatus('ready')
    log.info('Lens initialized')
    return True

# check and load the calibration file data
def loadCalibrationFileData() -> None:
    ''' 
    Check the validity of the calibration file and make sure it is for the selected lens family.
    '''
    global enableLensIQFunctions
    if calibrationFileName == '':
        return None

    dataFileLensFamily = IQEP.validateCalibrationFile(calibrationFileName)
    if dataFileLensFamily == None:
        # reset calibration file name to uninitialized
        mainGUIWindow['calFile'].update('')
        mainGUIWindow['calFileFull'].update('')
    elif dataFileLensFamily != lastLensFamily:
        uninitialize(motorReset=False, calDataFileReset=False)
        log.error(f'Calibration file lens family {dataFileLensFamily} does not match selected lens family {lastLensFamily}')
        sg.popup_ok(f'The calibration data file lens family {dataFileLensFamily} does not match selected lens family {lastLensFamily}.  Please select the correct lens family ({dataFileLensFamily}) or a different calibration file.', title='Error')
    else:
        # update calibration data file
        log.debug(f'Calibration file loaded for lens family: {dataFileLensFamily}')
        enableLensIQFunctions = True
        mainGUIWindow['lensIQControlFrame'].update(visible=True)
        if actions.readyStatus == 'ready' and actions.regardLimits: 
            # if the motors are initialized allow the input fields to be usable
            IQEP.initMotors(MCR, enableFields=actions.regardLimits)
        IQEP.updateCalibrationFile()
    return None

def uninitialize(motorReset:bool=True, calDataFileReset:bool=True) -> None:
    '''
    Uninitialize motors and IQ functions 
    ### input: 
    - motorReset (optional: True): True to reset the motors
    '''
    global enableLensIQFunctions, calibrationFileName
    if motorReset:
        actions.setStatus('notInit')
        actions.enableLiveFrame(False)
        actions.enableLiveFrameAbs(False)
    if calDataFileReset:
        mainGUIWindow['calFile'].update('')
        mainGUIWindow['calFileFull'].update('')
        calibrationFileName = ''
    if enableLensIQFunctions:
        enableLensIQFunctions = False
        mainGUIWindow['lensIQControlFrame'].update(visible=False)
        IQEP.resetControlInfo()
        IQEP.IQActions.clearFields()
        IQEP.IQActions.enableLiveFrame(False)
        if motorReset and MCR: IQEP.motorsEnabled = False

# set motor speeds
def setMotorSpeeds(focusSpeed:int=1000, zoomSpeed:int=1000, irisSpeed:int=100):
    '''
    Set the motor speeds.  Speeds are saved in the local settings file (not stored in control board EEPROM)
    ### input: 
    - focusSpeed (optional: 1000): focus motor pps speed
    - zoomSpeed (optional: 1000): zoom motor pps speed
    - irisSpeed (optional: 100): iris motor pps speed
    '''
    if (MCR.focus.setMotorSpeed(int(focusSpeed)) == 0): 
        settings['focusSpeed'] = int(focusSpeed)
    else:
        log.warning(f'Focus motor speed {focusSpeed} is out of range, not changed')

    if (MCR.zoom.setMotorSpeed(int(zoomSpeed)) == 0): 
        settings['zoomSpeed'] = int(zoomSpeed)
    else:
        log.warning(f'Zoom motor speed {zoomSpeed} is out of range, not changed')

    if (MCR.iris.setMotorSpeed(int(irisSpeed)) == 0): 
        settings['irisSpeed'] = int(irisSpeed)
    else:
        log.warning(f'Iris motor speed {irisSpeed} is out of range, not changed')
    return

# set motor homing speeds
def setHomeSpeeds(focusSpeed:int=1000, zoomSpeed:int=1000, irisSpeed:int=100):
    '''
    Set the motor homing speeds.  Speeds are saved in the local settings file (not stored in control board EEPROM)
    ### input: 
    - focusSpeed (optional: 1000): focus motor pps speed
    - zoomSpeed (optional: 1000): zoom motor pps speed
    - irisSpeed (optional: 100): iris motor pps speed
    '''
    if (MCR.focus.setHomingSpeed(int(focusSpeed)) == 0): 
        settings['focusHomingSpeed'] = int(focusSpeed)
    else:
        log.warning(f'Focus motor speed {focusSpeed} is out of range, not changed')

    if (MCR.zoom.setHomingSpeed(int(zoomSpeed)) == 0): 
        settings['zoomHomingSpeed'] = int(zoomSpeed)
    else:
        log.warning(f'Zoom motor speed {zoomSpeed} is out of range, not changed')

    if (MCR.iris.setHomingSpeed(int(irisSpeed)) == 0): 
        settings['irisHomingSpeed'] = int(irisSpeed)
    else:
        log.warning(f'Iris motor speed {irisSpeed} is out of range, not changed')
    return

# handle settings values
def handleSettingsValues(values:dict):
    '''
    Respond to the values in the settings window. 
    '''
    if values['focusSpeed'] != '' or values['zoomSpeed'] != '' or values['irisSpeed'] != '':
        setMotorSpeeds(values['focusSpeed'], values['zoomSpeed'], values['irisSpeed'])

    if values['focusHomeSpeed'] != '' or values['zoomHomeSpeed'] != '' or values['irisHomeSpeed'] != '':
        setHomeSpeeds(values['focusHomeSpeed'], values['zoomHomeSpeed'], values['irisHomeSpeed'])

    if values['cp_limitCheck'] != None:
        state = values['cp_limitCheck']
        actions.setRegardLimits(state)
        if MCR:
            MCR.focus.setRespectLimits(state)
            MCR.zoom.setRespectLimits(state)

    if values['cp_backlash'] != None:
        actions.setRegardBacklash(values['cp_backlash'])
    
    return 

##################################################
### main application routine 
##################################################
# global variable
MCR: Optional[TheiaMCR.MCRControl] = None # type: ignore
mainGUIWindow: Optional[sg.Window] = None

settings = settingsFiles.readSettingsFile(settingsFileName)
comPort = settings.get('comPort', '')
comPortList = utilities.searchComPorts()
if comPort not in comPortList:
    comPort = ''

# save default files
settings['dataSetQRCode'] = dataSetQRCode

# default lens setup
lensData = settingsFiles.readUserDataFile(lensDataFileName)
if lensData == None:
    sg.popup_ok(f'Lens data file not found: {lensDataFileName}', title='Error')
    sys.exit(1)
lensFamiliesList = list(lensData.keys())
lastLensFamily = settings.get('lastLensFamily', 'TL1250P Nx')

# create the GUI window
actions = createMainGUI()

# Lens IQ setup variables
enableLensIQFunctions = False
IQEP = lensIQ_expansion.IQExpansionPack(mainGUIWindow, settings)
calibrationFileName = ''

while (True and mainGUIWindow != None):
    event, values = mainGUIWindow.read()
    #log.debug(f"Event: {event}\n{values}")
    if event in (sg.WIN_CLOSED, 'exitBtn'):
        break

    elif (event == 'cp_lensFam'):
        newLensFamily = checkNewLensFamily(values['cp_lensFam'])
        if newLensFamily != None: 
            # a new lens is selected
            lastLensFamily = newLensFamily
            settings['lastLensFamily'] = lastLensFamily
            uninitialize(motorReset=True, calDataFileReset=False)

    elif event == 'cp_port':
        newComPort = values['cp_port']
        if newComPort != comPort:
            comPort = newComPort
            settings['comPort'] = comPort
            # cancel motor initialization status
            uninitialize(motorReset=True, calDataFileReset=False)
            if MCR:
                MCR.close()
                MCR = None

    elif event == 'cp_refresh':
        newComPortList = utilities.searchComPorts()
        if comPort not in newComPortList:
            # previously selected comPort no longer available, choose the last one in the new list
            comPort = newComPortList[-1] if len(newComPortList) >= 1 else ''
            if comPort != '':
                settings['comPort'] = comPort
            # cancel motor initialization status
            uninitialize(motorReset=True, calDataFileReset=False)
            if MCR:
                MCR.close()
                MCR = None
        mainGUIWindow['cp_port'].update(value=comPort, values=sorted(newComPortList), size=(18,10))
            
    elif event == 'motorInitBtn':
        if comPort != '':
            uninitialize(motorReset=False, calDataFileReset=True)
            calibrationFileName = ''
            initMCR(MCRCom=comPort, homeMotors=False, lensFam=lastLensFamily, regardLimits=False)
        else:
            log.error("** Com port is blank")
            sg.popup_ok('Com port is blank', title='Error')
    
    elif event == 'motorInitHomeBtn':
        if comPort != '':
            success = initMCR(lensFam=lastLensFamily, MCRCom=comPort, homeMotors=True, regardLimits=True)
            if success and MCR.MCRInitialized:
                loadCalibrationFileData()
        else:
            log.error("** Com port is blank")
            sg.popup_ok('Com port is blank', title='Error')

    elif event == 'settingsPopup':
        # open the settings popup window.  The communication path for this program will always be 'USB'.  
        pos = GUI_setup.windowPosition(mainGUIWindow)
        settingsValues = GUI_setup.settingsGUI('USB', MCR, actions, pos)
        if settingsValues != None:
            handleSettingsValues(settingsValues)
            if settingsValues['comUART'] or settingsValues['comI2C']:
                # communications path was set to something else and USB is no longer available. 
                if comPort == '':
                    log.error('** Com port is blank')
                    sg.popup_ok('Com path not changed: Com port is blank', title='Error')
                    continue
                if not MCR:
                    MCR = TheiaMCR.MCRControl(comPort)
                    if not MCR.MCRInitialized:
                        log.error('** Com path not changed: MCR not initialized')
                        sg.popup_ok('Motor control initalization error, communication path not changed', title='Error')
                        MCR = None
                        continue
                MCR.MCRBoard.setCommunicationPath('UART' if settingsValues['comUART'] else 'I2C')
                sg.popup_ok(f'New communication path was set to {"UART" if settingsValues["comUART"] else "I2C"}.  USB communication is no longer available and this application will end.', title='New com path')
                break

    elif event == 'helpPopup':
        pos = GUI_setup.windowPosition(mainGUIWindow)
        GUI_setup.helpPopup(position=pos)

    elif event == 'IRCBtn1':
        mainGUIWindow['IRCBtn1'].update(button_color=GUI_setup.IRCSelectedColor)
        mainGUIWindow['IRCBtn2'].update(button_color=GUI_setup.TheiaDarkBlueColor)
        MCR.IRC.state(1)
        
    elif event == 'IRCBtn2':
        mainGUIWindow['IRCBtn1'].update(button_color=GUI_setup.TheiaDarkBlueColor)
        mainGUIWindow['IRCBtn2'].update(button_color=GUI_setup.IRCSelectedColor)
        MCR.IRC.state(2)

    elif event == 'lensIQCheckbox':
        mainGUIWindow['calFileText'].update(visible=values['lensIQCheckbox'])
        mainGUIWindow['calFile'].update(visible=values['lensIQCheckbox'])
        mainGUIWindow['calFileBrowse'].update(visible=values['lensIQCheckbox'])
        if not values['lensIQCheckbox']:
            uninitialize(motorReset=False, calDataFileReset=True)

    elif event == 'calFileFull':
        mainGUIWindow['calFile'].update(path.basename(values['calFileFull']))
        calibrationFileName = values['calFileFull']
        loadCalibrationFileData()

    if enableLensIQFunctions: 
        IQEP.IQActions.readGUIValues = values
        IQEP.checkEvents(event, values)

    if MCR:
        if MCR.MCRInitialized and event in {'moveWideBtn', 'moveTeleBtn', 'moveNearBtn', 'moveFarBtn', 'moveOpenBtn', 'moveCloseBtn', 'moveZoomAbsBtn', 'moveFocusAbsBtn', 'moveIrisAbsBtn', 'zoomCurFldUpdate', 'focusCurFldUpdate', 'irisCurFldUpdate'}:
            actions.setStatus('moving')
            if event == 'moveWideBtn':
                # move zoom motor
                MCR.zoom.moveRel(int(values['zoomStepFld']), correctForBL=actions.regardBacklash)
                # update field
                mainGUIWindow['zoomCurFld'].update(MCR.zoom.currentStep)
                if enableLensIQFunctions: IQEP.updateAfterZoom()

            elif event == 'moveTeleBtn':
                # move zoom motor
                MCR.zoom.moveRel(-int(values['zoomStepFld']), correctForBL=actions.regardBacklash)
                # update field
                mainGUIWindow['zoomCurFld'].update(MCR.zoom.currentStep)
                if enableLensIQFunctions: IQEP.updateAfterZoom()

            elif event == 'moveNearBtn':
                # move focus motor
                MCR.focus.moveRel(-int(values['focusStepFld']), correctForBL=actions.regardBacklash)
                # update field
                mainGUIWindow['focusCurFld'].update(MCR.focus.currentStep)
                if enableLensIQFunctions: IQEP.updateAfterFocus(changeOD=False)

            elif event == 'moveFarBtn':
                # move focus motor
                MCR.focus.moveRel(int(values['focusStepFld']), correctForBL=actions.regardBacklash)
                # updated field
                mainGUIWindow['focusCurFld'].update(MCR.focus.currentStep)
                if enableLensIQFunctions: IQEP.updateAfterFocus(changeOD=False)

            elif event == 'moveOpenBtn':
                # move iris motor
                MCR.iris.moveRel(-int(values['irisStepFld']), correctForBL=False)
                # update field
                mainGUIWindow['irisCurFld'].update(MCR.iris.currentStep)
                if enableLensIQFunctions: IQEP.updateAfterIris()

            elif event == 'moveCloseBtn':
                # move iris motor
                MCR.iris.moveRel(int(values['irisStepFld']), correctForBL=False)
                # updated field
                mainGUIWindow['irisCurFld'].update(MCR.iris.currentStep)
                if enableLensIQFunctions: IQEP.updateAfterIris()

            elif event in {'moveZoomAbsBtn', 'zoomCurFldUpdate'}:
                if actions.absMoveInitialized:
                    # move to absolute position
                    MCR.zoom.moveAbs(int(values['zoomCurFld']))
                    # confirm update field
                    mainGUIWindow['zoomCurFld'].update(MCR.zoom.currentStep)
                    if enableLensIQFunctions: IQEP.updateAfterZoom()

            elif event in {'moveFocusAbsBtn', 'focusCurFldUpdate'}:
                if actions.absMoveInitialized:
                    # move to absolute position
                    MCR.focus.moveAbs(int(values['focusCurFld']))
                    # confirm update field
                    mainGUIWindow['focusCurFld'].update(MCR.focus.currentStep)
                    if enableLensIQFunctions: IQEP.updateAfterFocus(changeOD=False)

            elif event in {'moveIrisAbsBtn', 'irisCurFldUpdate'}:
                if actions.absMoveInitialized:
                    # move to absolute position
                    MCR.iris.moveAbs(int(values['irisCurFld']))
                    # confirm update field
                    mainGUIWindow['irisCurFld'].update(MCR.iris.currentStep)
                    if enableLensIQFunctions: IQEP.updateAfterIris()
        
            ####### check for unknown position
            actions.setStatus('ready')

if MCR:
    MCR.close()
if mainGUIWindow: mainGUIWindow.close()
