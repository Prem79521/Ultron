"""
ULTRON Speech Pipeline Coordinator
Reserved for future local Voice Activity Detection (VAD) and noise suppression hooks.
"""

import logging

class SpeechPipeline:
    def __init__(self):
        self.logger = logging.getLogger("ultron-agent")

    def process_buffer(self, buffer):
        return buffer
