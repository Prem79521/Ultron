from ultron.core.service_manager import UltronService

class LLMProvider(UltronService):
    """Abstract interface for LLM engines."""
    def __init__(self, name: str = "LlmService"):
        super().__init__(name)

    def initialize(self) -> bool:
        return True

    def generate_response(self, prompt: str) -> str:
        """Generates text completion based on prompt."""
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
