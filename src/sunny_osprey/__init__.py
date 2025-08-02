"""
Sunny Osprey - A Python project with clean structure.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .main import run_mqtt_processor
from .mqtt_processor import FrigateEventProcessor

__all__ = ["run_mqtt_processor", "FrigateEventProcessor"]
