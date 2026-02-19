# Utility functions for Theia_lensIQ_GUI
#

import os
import sys
import logging
import serial.tools.list_ports

# set up logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Find file paths based on development or deployment.  
def resourcePath(resource):
    '''
    Set the base path of the exe or development folder.  Use this function for icons and program-specific files.  
    ### input
    - resource: the resource path to find the path to
    ### return
    [basePath/resourceName]
    '''
    # Get absolute path to resource, works for dev and for PyInstaller
    base_path = os.path.dirname(sys.executable)
    if not os.path.exists(os.path.join(base_path, "data")):  # Check for data folder only available with exe file
        # use development path
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, resource)

# get the user directory
def getUserDir() -> str:
    '''
    Get the user directory (create the folder if necessary).  Use this function for attached files and configuration files.  
    Files should be in the 'data' subfolder.  Call os.path.join(utilities.getUserDir(), 'data') to get the data folder. 
    ### return:  
    [user directory]
    '''
    homeDir = os.path.expanduser("~")
    userDir = os.path.join(homeDir, 'AppData', 'Local', 'TheiaLensGUI')
    os.makedirs(userDir, exist_ok=True)
    return userDir

# searchComPorts
def searchComPorts():
    '''
    Search for connected com ports for selecting MCR motor controllers
    ### return
    [list of com ports]
    '''
    ports = serial.tools.list_ports.comports()
    portList = []
    for port, desc, hwid in sorted(ports):
        log.info("Ports: {} [{}]".format(desc, hwid))
        portList.append(port)
    return portList