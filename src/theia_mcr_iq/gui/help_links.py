# Lens IQ and MCR IQ help functions and links
# Create the list of hyperlinks in the helpLinks.json file in the format: {"link_text": "URL"}

from theia_mcr_iq import settings as read_settings_files


# global variables
helpLinksFileName = 'help_links.json'   # file containing the help links


def help_init() -> dict | None:
    '''
    Initialize the help links by reading them from the help_links.json file.
    ### return: 
    [True | False] if the import was successful or not
    '''
    help_links = read_settings_files.readUserDataFile(helpLinksFileName)
    return help_links

def hyperlink(window, fieldKey:str):
    '''
    Format the GUI text element to look like a hyperlink.  Pass the window and field key (text element) 
    to be formatted: lensIQ_help.hyperlink(window, '-LINK-').  Make sure the enable_events=True.  
    In the event loop, handle the event '-LINK-' with webbrowser.open(URL)
    ### input: 
    - window: the PySimpleGUI window object
    - fieldKey: the key of the Text element to be made clickable
    '''
    window[fieldKey].update(text_color='blue', font=('Helvetica', 10, 'underline'))
    return