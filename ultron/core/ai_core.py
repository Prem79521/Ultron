"""
ULTRON AI Core — Directs cognitive pipeline actions: Planner, Reasoner, Skills, and Reflection.
"""

import logging
from typing import Dict, Any
import uuid
from ultron.core.event_bus import event_bus
from ultron.core.state_manager import state_manager
from ultron.core.task_manager import task_manager
from ultron.core.command_queue import UltronCommandQueue

class UltronAICore:
    """The central orchestrator driving perception, planning, and tool execution."""
    def __init__(self, core_system, memory_manager, skill_registry):
        self.core = core_system
        self.memory = memory_manager
        self.skills = skill_registry
        self.logger = logging.getLogger("ultron-agent")
        
        # Enforce FIFO Command Queue (Bug 24)
        self.queue = UltronCommandQueue(self._process_command_pipeline)
        self.queue.start()

    def execute_command(self, command_text: str):
        """Enqueue command into FIFO queue only during LISTENING or PROCESSING states."""
        from ultron.core.voice_session_manager import get_voice_session_manager, VoiceState
        mgr = get_voice_session_manager()
        if mgr and mgr.state not in [VoiceState.LISTENING, VoiceState.PROCESSING]:
            self.logger.warning(f"AICore: Ignoring command '{command_text}' because voice session is in state {mgr.state.name}.")
            return
            
        from ultron.voice.pipeline_tracker import trace_pipeline
        trace_pipeline("COMMAND_RECEIVED", f"command='{command_text}'")
        event_bus.publish("COMMAND_RECEIVED", {"command": command_text})
        self.queue.enqueue(command_text)
        trace_pipeline("AI Queue", f"command='{command_text}' enqueued")

    def _process_command_pipeline(self, command_text: str) -> Dict[str, Any]:
        """Runs the active pipeline sequence on the queue worker thread."""
        self.logger.info(f"AICore processing pipeline turn: '{command_text}'")
        
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task_manager.create_task(task_id, command_text)
        task_manager.start_task(task_id)
        event_bus.publish("COMMAND_STARTED", {"task_id": task_id, "command": command_text})
        event_bus.publish("AI_THINKING", {"command": command_text})
        
        result = {"success": False, "response": ""}
        try:
            dispatcher = self.skills.get_skill("CommandDispatcher")
            if dispatcher:
                # Dispatcher runs the entire pipeline
                result = dispatcher.execute({"command": command_text, "session_id": self.core.session.session_id})
                task_manager.complete_task(task_id)
                event_bus.publish("COMMAND_COMPLETED", {"task_id": task_id, "result": result})
                event_bus.publish("AI_RESPONSE_READY", {"response": result.get("response", "")})
            else:
                err_msg = "Dispatcher capability missing from Skill Registry."
                self.logger.error(err_msg)
                result = {"success": False, "error": err_msg, "response": err_msg}
                task_manager.fail_task(task_id, err_msg)
                event_bus.publish("ERROR_OCCURRED", {"message": err_msg})
        except Exception as e:
            err_msg = f"Pipeline execution failed: {e}"
            self.logger.error(err_msg)
            result = {"success": False, "error": err_msg, "response": err_msg}
            task_manager.fail_task(task_id, err_msg)
            from ultron.core.voice_session_manager import get_voice_session_manager
            mgr = get_voice_session_manager()
            if mgr:
                mgr.transition_to_error(err_msg)
            event_bus.publish("ERROR_OCCURRED", {"message": err_msg, "error": str(e)})
 
        # Trigger speech feedback if speaker is permitted
        from ultron.core.service_manager import service_manager
        speech = service_manager.get_service("SpeechService")
        has_spoken = False
        if speech and result.get("response"):
            from ultron.hal.hal_manager import get_hal_manager
            hal = get_hal_manager()
            if hal and hal.is_allowed("speaker"):
                speech.speak(result["response"])
                has_spoken = True
                
        # State transitions are fully managed by VoiceSessionManager.
        # No direct state_manager changes are made here.

        return result

# Global core coordinator instance
ai_core = None

def init_ai_core(core_system, memory_manager, skill_registry) -> UltronAICore:
    global ai_core
    ai_core = UltronAICore(core_system, memory_manager, skill_registry)
    return ai_core

def get_ai_core() -> UltronAICore:
    global ai_core
    return ai_core

