"""
ULTRON Hardware Abstraction Layer — System queries.
"""

import sys
import os

class SystemDevice:
    @staticmethod
    def get_cpu_count() -> int:
        return os.cpu_count() or 1

    @staticmethod
    def get_platform() -> str:
        return sys.platform

    @staticmethod
    def get_memory_info() -> str:
        # Platform agnostic simple info
        return "Active (64-bit Core OS)"
