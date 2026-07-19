import logging
from ultron.core.service_manager import UltronService, service_manager

class VisionService(UltronService):
    """
    Subsystem service managing visual intelligence features.
    Orchestrates camera streams, hand tracking, and gesture recognition.
    """
    def __init__(self):
        super().__init__("VisionService")
        self.dependencies = ["CameraService", "GestureService"]
        self.logger = logging.getLogger("ultron-agent")

    def start(self) -> bool:
        self.active = True
        self.logger.info("Vision Intelligence Service started.")
        return True

    def stop(self) -> bool:
        self.active = False
        
        # Stop associated services via service_manager to ensure clean teardown
        service_manager.stop_service("GestureService")
        service_manager.stop_service("CameraService")
        
        self.logger.info("Vision Intelligence Service stopped.")
        return True

    def health(self) -> str:
        camera_srv = service_manager.get_service("CameraService")
        gesture_srv = service_manager.get_service("GestureService")
        
        cam_ok = camera_srv.health() == "Running" if camera_srv else False
        gest_ok = gesture_srv.health() == "Running" if gesture_srv else False
        
        if self.active and cam_ok and gest_ok:
            return "Running"
        elif self.active:
            return "Degraded (Subservices offline)"
        else:
            return "Offline"
