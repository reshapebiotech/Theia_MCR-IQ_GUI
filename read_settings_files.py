# Read files specific to Theia_lensIQ_GUI.py
#
# v.1.0.0 250811 extracted from Theia_lensIQ_GUI v.2.5.7 

import FreeSimpleGUI as sg
import utilities
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import json
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def readSettingsFile(settingsFileName:str) -> sg.UserSettings:
    '''
    Read the settings file data
    ### input: 
    - settingsFileName: the short name of the settings file
    ### return: 
    [settings values]
    '''
    appDir = utilities.getUserDir()
    settingsFullFileName = os.path.join(appDir, settingsFileName)
    if not os.path.exists(settingsFullFileName):
        settings = sg.UserSettings(filename=settingsFileName, path=appDir)
        settings['comPort'] = ''
        settings['lastLensFamily'] = ''
    settings = sg.UserSettings(filename=settingsFileName, path=appDir, autosave=True)
    return settings

# read lens data file
def readUserDataFile(lensDataFileName:str) -> dict | None:
    '''
    Read the lens data file from the AppData/local folder/data.  
    ### return:  
    [lens data]
    '''
    userData = None
    appDir = os.path.join(utilities.getUserDir(), 'data')
    lensDataFullFileName = os.path.join(appDir, lensDataFileName)
    if not os.path.exists(lensDataFullFileName):
        log.warning(f'No data file in {lensDataFullFileName}.  Find the "{lensDataFileName}" file. ')
        # Open the data file and save to appDir
        Tk().withdraw() 
        filename = askopenfilename(defaultextension='.json', filetypes=[('JSON File', '.json')], title=f"Open {lensDataFileName} file")
        if filename:
            with open(filename, 'r') as f:
                userData = json.load(f)
            os.makedirs(appDir, exist_ok=True)
            with open(lensDataFullFileName, 'w') as f:
                json.dump(userData, f)
        else: 
            return None
    else:
        userData = json.load(open(lensDataFullFileName))
    return userData
