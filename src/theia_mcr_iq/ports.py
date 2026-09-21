# Utility functions for Theia_lensIQ_GUI
#

import logging
import serial.tools.list_ports

# set up logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

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