"""Frontend static files for Meshtastic UI."""

from pathlib import Path


def locate_dir() -> Path:
    """Return the path to the frontend directory."""
    return Path(__file__).parent
