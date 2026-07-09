"""
ULTRON Hardware Abstraction Layer — Speaker adapter.
"""

from PySide6.QtMultimedia import QMediaDevices

class SpeakerDevice:
    @staticmethod
    def is_present() -> bool:
        return len(QMediaDevices.audioOutputs()) > 0

    @staticmethod
    def get_default_device_name() -> str:
        devices = QMediaDevices.audioOutputs()
        return devices[0].description() if devices else "None"
