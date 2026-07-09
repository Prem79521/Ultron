import logging
import time
import datetime

logger = logging.getLogger("ultron-agent")

_last_stage = None
_last_time = None

def trace_pipeline(stage_name: str, details: str = ""):
    """Logs the progression of the microphone-to-execution pipeline and prints hop transitions."""
    global _last_stage, _last_time
    stages = [
        "Microphone",
        "Recognition callback",
        "SPEECH_RECOGNIZED",
        "WakeDetector",
        "WAKE_DETECTED",
        "VoiceSessionManager",
        "COMMAND_RECEIVED",
        "AI Queue"
    ]
    
    if stage_name not in stages:
        return
        
    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    t_now = time.time()
    
    # Log every hop transition with timestamps
    if _last_stage:
        dur_msg = f" (elapsed: {(t_now - _last_time)*1000:.1f}ms)" if _last_time else ""
        logger.info(f"[{now}] PIPELINE HOP: {_last_stage} -> {stage_name}{dur_msg}")
    else:
        logger.info(f"[{now}] PIPELINE START: {stage_name}")
        
    _last_stage = stage_name
    _last_time = t_now
    
    if details:
        logger.info(f"[{now}] PIPELINE STAGE {stage_name} DETAILS: {details}")

    # Generate flowchart
    idx = stages.index(stage_name)
    flow = []
    for i, name in enumerate(stages):
        if i == idx:
            if details:
                flow.append(f"{name} ({details})")
            else:
                flow.append(f"{name}")
        else:
            flow.append(name)
            
    trace_msg = "\n  ↓\n".join(flow)
    logger.info(f"\n{trace_msg}\n")

def pipeline_broken(stage_name: str, reason: str):
    """Logs a pipeline break message with detailed reason."""
    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    logger.error(
        f"\n[{now}] PIPELINE BROKEN HERE\n"
        f"Stage: {stage_name}\n"
        f"Reason: {reason}\n"
    )
