"""Allow `python -m theia_mcr_iq` to start the GUI."""

import sys

from theia_mcr_iq.gui.app import main

sys.exit(main())
