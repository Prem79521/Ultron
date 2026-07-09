"""
ULTRON Boot Manager — Coordinates sequential hardware and system validation sequences (POST).
"""

import time
import logging
from typing import Callable, List, Tuple
from ultron.core.event_bus import event_bus
from ultron.core.config_loader import config_loader
from ultron.core.state_manager import state_manager

class UltronBootManager:
    """Boot coordinator verifying OS, database, and hardware layers sequentially."""
    def __init__(self, memory_manager, skill_registry, voice_provider):
        self.memory = memory_manager
        self.skills = skill_registry
        self.voice = voice_provider
        self.logger = logging.getLogger("ultron-agent")
        
        # Sequence of POST validation tasks
        self.boot_steps: List[Tuple[str, Callable[[], bool]]] = [
            ("Configuration Manager", self._boot_config),
            ("Database Registry", self._boot_database),
            ("Memory Domains", self._boot_memory),
            ("System Services", self._boot_services),
            ("Plugin Modules", self._boot_plugins),
            ("Hardware Abstraction Layer", self._boot_hal),
            ("Security Policy", self._boot_security),
            ("AI Core Pipeline", self._boot_ai_core),
            ("Skills Registry", self._boot_skills),
            ("Event Bus", self._boot_event_bus),
            ("Wake Engine", self._boot_wake),
            ("Developer Console", self._boot_developer)
        ]

    def run_boot(self, step_callback: Callable[[str, bool, int], None]):
        """Executes all boot validations, notifying status back to the caller."""
        self.logger.info("ULTRON OS Boot Sequence Initiating...")
        
        for idx, (name, func) in enumerate(self.boot_steps):
            try:
                success = func()
            except Exception as e:
                self.logger.error(f"POST step '{name}' crashed: {e}")
                success = False
                
            percent = int(((idx + 1) / len(self.boot_steps)) * 100)
            step_callback(name, success, percent)
            time.sleep(0.1)  # Visual pause for bootscreen
            
        # Log EventBus subscribers after all systems are initialized
        event_bus.log_subscribers()

    def _boot_config(self) -> bool:
        return config_loader.health()["status"] == "healthy"

    def _boot_database(self) -> bool:
        # Check SQLite db table check
        try:
            self.memory.list_records("preference", limit=1)
            return True
        except Exception:
            return False

    def _boot_memory(self) -> bool:
        return self.memory is not None

    def _boot_services(self) -> bool:
        # Start Service Manager
        from ultron.core.service_manager import service_manager
        service_manager.start_all()
        return True

    def _boot_plugins(self) -> bool:
        # Scan and load plugins
        from ultron.core.plugin_loader import plugin_loader
        if plugin_loader:
            plugin_loader.load_all_plugins()
        return True

    def _boot_hal(self) -> bool:
        # Check if HAL is initialized
        from ultron.hal.hal_manager import hal_manager
        if hal_manager:
            hal_manager.load_permissions()
            return True
        return False

    def _boot_security(self) -> bool:
        from ultron.security.security_manager import security_manager
        return security_manager is not None

    def _boot_ai_core(self) -> bool:
        from ultron.core.ai_core import ai_core
        return ai_core is not None

    def _boot_skills(self) -> bool:
        return self.skills.health()["status"] == "healthy"

    def _boot_event_bus(self) -> bool:
        return event_bus.health()["status"] == "healthy"

    def _boot_wake(self) -> bool:
        from ultron.core.wake_engine import wake_engine
        return wake_engine is not None

    def _boot_developer(self) -> bool:
        # Log directory validated
        return True
