"""Theia Technologies MCR IQ lens motor control: GUI and command-line tool."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("theia-mcr-iq-gui")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0+unknown"
