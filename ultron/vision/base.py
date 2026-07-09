from ultron.core.service_manager import UltronService

class VisionProvider(UltronService):
    """Abstract interface for vision engines."""
    def __init__(self, name: str = "VisionService"):
        super().__init__(name)

    def initialize(self) -> bool:
        return True

    def process_frame(self, frame):
        """Processes a video/camera frame."""
        raise NotImplementedError

    def configure(self, config: dict):
        pass

    def emit(self, data):
        pass

    def start(self) -> bool:
        self.active = True
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def health(self) -> str:
        return "Running" if self.active else "Offline"

    def status(self) -> str:
        return "Running" if self.active else "Offline"
