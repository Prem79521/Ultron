import logging
from typing import Dict, Any, Tuple
from ultron.core.service_manager import UltronService
from ultron.core.event_bus import event_bus

class GraphicsService(UltronService):
    """Subsystem service managing visual themes, status indicators, and animation parameters."""
    def __init__(self):
        super().__init__("GraphicsService")
        self.logger = logging.getLogger("ultron-agent")
        self.current_theme = "Default"
        self.animation_speed_multiplier = 1.0
        self.glow_intensity = 1.0

    def start(self) -> bool:
        self.active = True
        self.logger.info("GraphicsService started. Default theme: Amber Gold.")
        return True

    def stop(self) -> bool:
        self.active = False
        self.logger.info("GraphicsService stopped.")
        return True

    def health(self) -> str:
        return "Running" if self.active else "Offline"

    def set_theme(self, theme_name: str) -> None:
        """Dynamically switches visual color palettes."""
        self.current_theme = theme_name
        self.logger.info(f"Graphics theme changed to: {theme_name}")
        event_bus.publish("GRAPHICS_THEME_CHANGED", {"theme": theme_name})

    def set_animation_speed(self, multiplier: float) -> None:
        """Sets scaling factor for UI rendering loop velocities."""
        self.animation_speed_multiplier = max(0.1, min(5.0, multiplier))
        event_bus.publish("GRAPHICS_SPEED_CHANGED", {"speed": self.animation_speed_multiplier})

    def set_glow_intensity(self, intensity: float) -> None:
        """Sets scale multiplier for visual drop shadows and particle bloom."""
        self.glow_intensity = max(0.0, min(3.0, intensity))
        event_bus.publish("GRAPHICS_GLOW_CHANGED", {"glow": self.glow_intensity})
