"""
vosk_model_resolver.py
──────────────────────
Single, reusable Vosk model resolver.

Resolution order
  1. SQLite UME override  (vosk_model_path in provider_settings)
  2. config/voice.json    vosk_preferred_models list, in declared order
  3. Disk scan            any vosk-model-* directory found in vosk_models_dir
  4. Legacy paths         models/vosk/ subdirectory

Changing the active model requires only editing voice.json — no source changes.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ultron-agent")

# ── helpers ──────────────────────────────────────────────────────────────────

def _folder_size(path: str) -> int:
    """Return total bytes of all files under *path* (best-effort)."""
    total = 0
    try:
        for dirpath, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
    except Exception:
        pass
    return total


def _human_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"


def _load_voice_config() -> dict:
    """Load config/voice.json relative to the project root (cwd)."""
    try:
        cfg_path = Path("config") / "voice.json"
        with open(cfg_path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


# ── public API ────────────────────────────────────────────────────────────────

def resolve_vosk_model() -> Optional[str]:
    """
    Discover and return the absolute path to the best available Vosk model,
    or *None* if nothing is found.

    Also returns timing info via the module-level ``last_resolve_ms`` attribute.
    """
    global last_resolve_ms
    t0 = time.time()
    result = _resolve()
    last_resolve_ms = (time.time() - t0) * 1000
    return result


#: Set by the most recent call to resolve_vosk_model(); milliseconds.
last_resolve_ms: float = 0.0


def _resolve() -> Optional[str]:
    cfg = _load_voice_config()
    models_dir = cfg.get("vosk_models_dir", "models")
    preferred   = cfg.get("vosk_preferred_models", [])

    # ── 1. SQLite UME override ─────────────────────────────────────────────
    try:
        from ultron.memory import get_memory_manager
        mem = get_memory_manager()
        if mem:
            for r in mem.list_records("provider_settings", limit=100):
                if r["title"] == "vosk_model_path":
                    p = r["content"]
                    if os.path.isdir(p):
                        logger.debug(f"[Resolver] UME override: '{p}'")
                        return os.path.abspath(p)
    except Exception as e:
        logger.debug(f"[Resolver] UME lookup skipped: {e}")

    # ── 2. Preferred list from voice.json ─────────────────────────────────
    for name in preferred:
        candidates = [
            os.path.join(models_dir, name),
            os.path.join(models_dir, "vosk", name),
            name,  # bare name at cwd root
        ]
        for p in candidates:
            if os.path.isdir(p):
                logger.debug(f"[Resolver] preferred match: '{p}'")
                return os.path.abspath(p)

    # ── 3. Disk scan — any vosk-model-* under models_dir ──────────────────
    discovered: list[str] = []
    try:
        base = Path(models_dir)
        if base.is_dir():
            for entry in base.iterdir():
                if entry.is_dir() and entry.name.lower().startswith("vosk-model"):
                    discovered.append(str(entry))
    except Exception:
        pass

    # Rank: small models first (fast boot), then everything else alphabetically
    def _rank(p: str) -> tuple:
        name = os.path.basename(p).lower()
        is_small = "small" in name
        return (0 if is_small else 1, name)

    discovered.sort(key=_rank)
    for p in discovered:
        logger.debug(f"[Resolver] disk scan match: '{p}'")
        return os.path.abspath(p)

    # ── 4. Legacy vosk/ subdirectory ──────────────────────────────────────
    legacy = [
        os.path.join(models_dir, "vosk", "vosk-model-en-us-0.22"),
        os.path.join(models_dir, "vosk", "vosk-model-en-us-0.22", ""),
        "model",
    ]
    for p in legacy:
        if os.path.isdir(p):
            logger.debug(f"[Resolver] legacy match: '{p}'")
            return os.path.abspath(p)

    logger.warning("[Resolver] No Vosk model found on disk.")
    return None
