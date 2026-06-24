# Theia Technologies Lens Controller Interface

Theia Technologies has developed a TheiaMCR™ Python module that allows easy control of Theia's motorized lenses.

## MCR IQ controller GUI

Theia's MCR motor control board can control focus, zoom, iris, and IRC filters in a Theia motorized lens.  This MCR lens controller formats the target motor steps into specific commands that can be sent to the MCR motor control board.  The lens will respond to the commands.  This program keeps track of the lens motor positions (there is no feedback from the lens).  

With the purchase of a Theia IQ lens or calibrated lens, a data file can be installed to unlock additional features of the program.  These optional additional features are not required to control the lens using this application.  

## Core module (installed via pip)

- **`TheiaMCR`** - MCR IQ 400 motor control board interface

MCR IQ 400 board information: [Theia Technologies](https://www.theiatech.com/lenses/accessories/mcr/)

# Requirements

- Python 3.11 or higher

Install all dependencies:

```
pip install -r requirements.txt
```

Or install individually:

```
pip install FreeSimpleGUI TheiaMCR lensIQ numpy pyserial
```

# Quick start

1. Install dependencies (see above).
2. Connect the MCR IQ 400 board (or MCR IQ 600, etc.) via USB -- this creates a virtual COM port. See the MCR instructions for driver setup.
3. Run the application:
   ```
   python Theia_lensIQ_GUI.py
   ```
4. Select the **COM port** and **lens model** from the drop-down lists.
   - Click **Refresh** to rescan available COM ports if your device does not appear.
   - The application detects incorrect port types (e.g., Bluetooth adapters) and displays a descriptive error.
5 (optional). To enable IQ and calibrated lens functions with the purchase of a special IQ or calibrated lens, load a calibration file:
   - Check the **lensIQ** checkbox to reveal the calibration file browser.
   - Browse to the JSON calibration file that came with your lens.  For IQ lenses™, choose the latest dataset .json file from the selections in Dropbox.  For calibrated lenses, scan the QR code on the lens for the correct file. 
   - The file must be compatible with the selected lens model.

## Initializing motors

Two initialization options are available:

| Button | Behavior |
|--------|----------|
| **Init** | Connects to the MCR board without moving motors; limit switches not enforced. Use to reconnect without disturbing the lens position HOWEVER lens IQ™ functions will not be active. |
| **Init and home** | Connects and moves all motors to their PI limit switch home positions; limit switches enforced. Required before using lens IQ™ calibrated functions. |

After initialization, the step position fields and motor control buttons become active.

## Motor control

- **Relative movement** - Use Wide/Tele, Near/Far, and Open/Close buttons to move motors by the step count shown in the adjacent field.
- **Absolute position** - Enter a step number in the current position field and press Enter (or click the Abs button) to move to that position. Requires **Init and home**.
- **IRC filter** - For lenses with internal filters, two filter buttons appear with labels that match the lens model (e.g., visible only, clear, band pass, long pass). Click to toggle between filter positions.

## Settings

Click **Settings** to configure:

- **Motor speeds** (pps) for focus, zoom, and iris
- **Homing speeds** for each motor
- **Limit switch enforcement** (on/off)
- **Backlash correction** (on/off)
- **Communication path** - Change MCR communication from USB to UART or I2C (this disconnects USB and exits the application)

## Help

Click **Help** for context-sensitive links to documentation.

# License

Theia Technologies BSD 3-clause license  
Copyright 2023-2026 Theia Technologies

# Contact information

For more information:  
[Theia Technologies](https://www.theiatech.com/lenses/accessories/mcr/)

or contact:  
Mark Peterson at Theia Technologies  
[mpeterson@theiatech.com](mailto://mpeterson@theiatech.com)

To report any security concerns or issues privately: 
See [SECURITY.md](SECURITY.md) for detailed reporting instructions.

# Revision
v.3.2
