"""
ULTRON Hardware Abstraction Layer — Microphone adapter.
"""

from PySide6.QtMultimedia import QMediaDevices

class MicrophoneDevice:
    @staticmethod
    def is_present() -> bool:
        return len(QMediaDevices.audioInputs()) > 0

    @staticmethod
    def get_default_device_name() -> str:
        devices = QMediaDevices.audioInputs()
        return devices[0].description() if devices else "None"
