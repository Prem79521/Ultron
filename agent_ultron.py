"""
ULTRON – Voice Agent (MCP-powered)
===================================
Intelligent engineering partner for software development, planning, and system automation.

Runs:
  uv run agent_ultron.py dev      – LiveKit Cloud mode
  uv run agent_ultron.py console  – text-only console mode
"""

import os
import logging
import subprocess
import pathlib
from datetime import datetime
from dotenv import load_dotenv

from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.llm import mcp
from livekit.plugins import google as lk_google, openai as lk_openai, sarvam, silero

from ultron.config import config

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

STT_PROVIDER       = "sarvam"
LLM_PROVIDER       = "gemini"
TTS_PROVIDER       = "openai"

GEMINI_LLM_MODEL   = "gemini-2.5-flash"
OPENAI_LLM_MODEL   = "gpt-4o"

OPENAI_TTS_MODEL   = "tts-1"
OPENAI_TTS_VOICE   = "nova"
TTS_SPEED           = 1.15

SARVAM_TTS_LANGUAGE = "en-IN"
SARVAM_TTS_SPEAKER  = "rahul"

# MCP server running on host
MCP_SERVER_PORT = 8000

# ---------------------------------------------------------------------------
# Modular Prompt Loader
# ---------------------------------------------------------------------------

def load_system_prompt() -> str:
    """Loads modular system prompt components from the markdown files, with a safe fallback."""
    base_dir = pathlib.Path(__file__).parent / "ultron" / "prompts"
    prompt_files = ["system.md", "personality.md", "reasoning.md", "memory.md", "developer.md", "safety.md"]
    prompt_parts = []
    
    for filename in prompt_files:
        path = base_dir / filename
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    prompt_parts.append(content)
            except Exception as e:
                logging.getLogger("ultron-agent").warning(f"Failed to read prompt file {filename}: {e}")
                
    if prompt_parts:
        return "\n\n---\n\n".join(prompt_parts)
    
    # Fallback default prompt if files are not present
    return (
        "You are ULTRON, a cognitive intelligence platform and professional engineering partner.\n"
        "Maintain a calm, confident, and direct tone. Assist with development, architecture, and planning."
    )

# ---------------------------------------------------------------------------
# Greeting Engine (Strategy Pattern)
# ---------------------------------------------------------------------------

class GreetingStrategy:
    def greet(self, display_name: str) -> str:
        raise NotImplementedError

class DefaultGreetingStrategy(GreetingStrategy):
    def greet(self, display_name: str) -> str:
        name_suffix = f", {display_name}" if display_name else ""
        return f"System online{name_suffix}. Diagnostics clear. How can I assist with your deployment?"

class ContextAwareGreetingStrategy(GreetingStrategy):
    """Context-aware greeting matching time of day and absence updates."""
    def greet(self, display_name: str) -> str:
        hour = datetime.now().hour  # Local system hour
        name_str = f", {display_name}" if display_name else ""
        
        if 4 <= hour < 12:
            return f"Good morning{name_str}. All systems are operational."
        elif 12 <= hour < 17:
            return f"Good afternoon{name_str}. System status clear."
        elif 17 <= hour < 22:
            return f"Welcome back{name_str}. Ready to continue project analysis?"
        else:  # 22 to 4
            return f"You're working late{name_str}. Let's make the progress worth the lost sleep."

class GreetingEngine:
    def __init__(self, strategy: GreetingStrategy):
        self.strategy = strategy

    def get_greeting(self, display_name: str) -> str:
        return self.strategy.greet(display_name)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()

logger = logging.getLogger("ultron-agent")
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Resolve Windows host IP from WSL if needed
# ---------------------------------------------------------------------------

def _get_windows_host_ip() -> str:
    """Get the Windows host IP by looking at the default network route."""
    try:
        cmd = "ip route show default | awk '{print $3}'"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=2
        )
        ip = result.stdout.strip()
        if ip:
            logger.info("Resolved Windows host IP via gateway: %s", ip)
            return ip
    except Exception as exc:
        logger.warning("Gateway resolution failed: %s. Trying fallback...", exc)

    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if "nameserver" in line:
                    ip = line.split()[1]
                    logger.info("Resolved Windows host IP via nameserver: %s", ip)
                    return ip
    except Exception:
        pass

    return "127.0.0.1"

def _mcp_server_url() -> str:
    url = f"http://127.0.0.1:{MCP_SERVER_PORT}/sse"
    logger.info("MCP Server URL: %s", url)
    return url

# ---------------------------------------------------------------------------
# Provider Factories
# ---------------------------------------------------------------------------

def _build_stt():
    if STT_PROVIDER == "sarvam":
        logger.info("STT → Sarvam Saaras v3")
        return sarvam.STT(
            language="unknown",
            model="saaras:v3",
            mode="transcribe",
            flush_signal=True,
            sample_rate=16000,
        )
    elif STT_PROVIDER == "whisper":
        logger.info("STT → OpenAI Whisper")
        return lk_openai.STT(model="whisper-1")
    else:
        raise ValueError(f"Unknown STT_PROVIDER: {STT_PROVIDER!r}")

def _build_llm():
    if LLM_PROVIDER == "openai":
        logger.info("LLM → OpenAI (%s)", OPENAI_LLM_MODEL)
        return lk_openai.LLM(model=OPENAI_LLM_MODEL)
    elif LLM_PROVIDER == "gemini":
        logger.info("LLM → Google Gemini (%s)", GEMINI_LLM_MODEL)
        return lk_google.LLM(model=GEMINI_LLM_MODEL, api_key=os.getenv("GOOGLE_API_KEY"))
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}")

def _build_tts():
    if TTS_PROVIDER == "sarvam":
        logger.info("TTS → Sarvam Bulbul v3")
        return sarvam.TTS(
            target_language_code=SARVAM_TTS_LANGUAGE,
            model="bulbul:v3",
            speaker=SARVAM_TTS_SPEAKER,
            pace=TTS_SPEED,
        )
    elif TTS_PROVIDER == "openai":
        logger.info("TTS → OpenAI TTS (%s / %s)", OPENAI_TTS_MODEL, OPENAI_TTS_VOICE)
        return lk_openai.TTS(model=OPENAI_TTS_MODEL, voice=OPENAI_TTS_VOICE, speed=TTS_SPEED)
    else:
        raise ValueError(f"Unknown TTS_PROVIDER: {TTS_PROVIDER!r}")

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class UltronAgent(Agent):
    """
    ULTRON – Intelligent engineering partner.
    All tools are provided via the MCP server.
    """

    def __init__(self, stt, llm, tts) -> None:
        super().__init__(
            instructions=load_system_prompt(),
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(),
            mcp_servers=[
                mcp.MCPServerHTTP(
                    url=_mcp_server_url(),
                    transport_type="sse",
                    client_session_timeout_seconds=30,
                ),
            ],
        )
        # extesible greeting setup
        self.greeting_engine = GreetingEngine(ContextAwareGreetingStrategy())

    async def on_enter(self) -> None:
        """Greet the user utilizing the dynamic greeting strategies."""
        display_name = config.DISPLAY_NAME
        greeting_text = self.greeting_engine.get_greeting(display_name)
        
        greeting_instruction = (
            f"Greet the user with exactly this text: '{greeting_text}' "
            "Maintain a professional, composed, and direct tone."
        )
        await self.session.generate_reply(instructions=greeting_instruction)

# ---------------------------------------------------------------------------
# LiveKit entry point
# ---------------------------------------------------------------------------

def _turn_detection() -> str:
    return "stt" if STT_PROVIDER == "sarvam" else "vad"

def _endpointing_delay() -> float:
    return {"sarvam": 0.07, "whisper": 0.3}.get(STT_PROVIDER, 0.1)

async def entrypoint(ctx: JobContext) -> None:
    logger.info(
        "ULTRON online – room: %s | STT=%s | LLM=%s | TTS=%s",
        ctx.room.name, STT_PROVIDER, LLM_PROVIDER, TTS_PROVIDER,
    )

    stt = _build_stt()
    llm = _build_llm()
    tts = _build_tts()

    session = AgentSession(
        turn_detection=_turn_detection(),
        min_endpointing_delay=_endpointing_delay(),
    )

    await session.start(
        agent=UltronAgent(stt=stt, llm=llm, tts=tts),
        room=ctx.room,
    )

# ---------------------------------------------------------------------------
# Main wrappers
# ---------------------------------------------------------------------------

def main():
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

def dev():
    """Wrapper to run the agent in dev mode automatically."""
    import sys
    if len(sys.argv) == 1:
        sys.argv.append("dev")
    main()

if __name__ == "__main__":
    main()
