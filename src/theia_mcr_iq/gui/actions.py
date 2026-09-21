# GUI actions for Theia_lensIQ_GUI.py
#
# v.1.0.1 250812 removed MCR references
# v.1.0.0 250811 extracted from Theia_lensIQ_GUI.py v.2.5.7

class GUIActions:
    controllerStatusList = {
        'notInit': ('Not initialized','red'),                   # default
        'init': ('Initializing', 'yellow'),                     # -- in motion
        'ready': ('Ready', 'green'),                            # ready to move     
        'moving': ('Moving','yellow'),                          # -- in motion
        'posUnknown': ('Position unknown','lightgreen'),        # set if steps exceeds min/max steps at any point, reset by initializing
        'error': ('ERROR', 'red')                               # program or data error
    }

    def __init__(self, gui):
        '''
        These are the action functions that integrate with the main window GUI.  
        # input: 
        - gui: the main GUI object
        '''
        self.GUIWindow = gui

        self.absMoveInitialized = False  # Flag to check if absolute movement is initialized
        self.regardBacklash = False
        self.regardLimits = False
        self.readyStatus = 'notInit'

    # enableLiveFrame
    def enableLiveFrame(self, enable:bool=True, absoluteInit:bool=False):
        '''
        Enable buttons and inputs in the live frame. 
        ### input
        - enable (optional: True): state
        - absoluteInit (optional: False): enable absolute motor movements from home positions
        ### global
        - absMoveInit: set if relativeOnly is False
        '''
        self.absMoveInitialized = absoluteInit

        # relative movement buttons
        componentList = ['moveTeleBtn', 'moveWideBtn', 'moveNearBtn', 'moveFarBtn', 'moveOpenBtn', 'moveCloseBtn', 
                         'zoomCurFld', 'focusCurFld', 'irisCurFld', 'zoomStepFld', 'focusStepFld', 'irisStepFld']
        for component in componentList:
            self.GUIWindow[component].update(disabled = not enable)

        # absolute movement buttons
        if absoluteInit:
            componentList = ['moveZoomAbsBtn', 'moveFocusAbsBtn', 'moveIrisAbsBtn']
            for component in componentList:
                self.GUIWindow[component].update(disabled = not enable)
        return
    
    # enableLiveFrameAbs
    def enableLiveFrameAbs(self, enable:bool=True):
        '''
        Enable buttons and inputs for absolute movements. 
        ### input
        - enable (bool): state
        '''
        componentList = ['moveZoomAbsBtn', 'moveFocusAbsBtn', 'moveIrisAbsBtn']
        for component in componentList:
            self.GUIWindow[component].update(disabled = not enable)
        return

    # enableLiveFrameIRC
    def enableLiveFrameIRC(self, enable:bool=True):
        '''
        Enable IRC filter buttons.
        ### input
        - enable (bool): state
        '''
        componentList = ['IRCBtn1', 'IRCBtn2']
        for component in componentList:
            self.GUIWindow[component].update(disabled = not enable)
        return
    
    # enableInitHomeBtn
    def enableInitHomeBtn(self, enable:bool=True):
        '''
        Enable the initialize and home motors button.  PI is required in the lens for this operation. 
        ### input
        - enable (bool): state
        '''
        self.GUIWindow['motorInitHomeBtn'].update(disabled = not enable)
        self.GUIWindow['lensIQCheckbox'].update(disabled = not enable)
        if not enable:
            self.GUIWindow['lensIQCheckbox'].update(value=False)
        return
    
    # set the regard limits flag in MCR module
    def setRegardLimits(self, state:bool=True) -> bool:
        '''
        Set the regard limits flag in MCR module. 
        Limit steps to avoid going past the hard stop.  
        This setting is stored in the MCRControl.py variables (not local)
        ### input: 
        - state: the regard setting
        ### return: 
        - state: the updated regard limits setting
        '''
        self.regardLimits = state
        self.enableLiveFrameAbs(state)
        return state

    # set the backlash flag in MCR move relative commands
    def setRegardBacklash(self,state:bool=True) -> bool:
        '''
        Set the backalsh flag in the MCR move relative command.   
        *This function is not active*
        ### input
        - state: the regard setting (not used)
        ### return: 
        - state: the updated regard backlash setting
        '''
        self.regardBacklash = state
        return state

    # set the controller status indicators
    def setStatus(self, status:str='notInit') -> None:
        '''
        Set the status indicators to the current controller status.  
        ### input:
        - status: the new status (from controllerStatusList)
        '''
        self.readyStatus = status
        
        self.GUIWindow['fldStatus'].update(GUIActions.controllerStatusList[self.readyStatus][0])
        self.GUIWindow['fldStatus'].update(background_color=GUIActions.controllerStatusList[self.readyStatus][1])
        self.GUIWindow.refresh()
        return