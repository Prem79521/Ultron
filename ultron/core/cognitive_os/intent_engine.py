"""
ULTRON Cognitive OS — Intent Classification and Entity Extraction Engine.
"""

import re
from typing import List, Dict, Any

class IntentResult:
    """The structured contract passing between parsing and downstream resolvers."""
    def __init__(
        self,
        intent: str,
        entity: str,
        normalized_text: str,
        confidence: float = 1.0,
        tokens: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        self.intent = intent # "OPEN_APPLICATION", "WEB_SEARCH", "PLAY_MEDIA", "OPEN_FOLDER", "OPEN_SETTINGS", "SYSTEM_ACTION", "OPEN_WEBSITE", "UNKNOWN"
        self.entity = entity
        self.normalized_text = normalized_text
        self.confidence = confidence
        self.tokens = tokens or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "entity": self.entity,
            "normalized_text": self.normalized_text,
            "confidence": self.confidence,
            "tokens": self.tokens,
            "metadata": self.metadata
        }

class IntentEngine:
    """Classifies user queries into IntentResult objects using rule-based parsing."""
    def __init__(self):
        # Intent patterns mapping verbs to intents
        self.prefixes = {
            "SYSTEM_ACTION": ["shutdown", "restart", "reboot", "power off", "exit", "quit", "poweroff"],
            "PLAY_MEDIA": ["play", "listen to", "watch"],
            "WEB_SEARCH": ["search for", "search", "google", "look up", "find"],
            "OPEN_WEBSITE": ["go to", "open url"],
            "HIDE_ITEM": ["hide folder", "hide this folder", "hide project", "hide"],
            "RESTORE_ITEM": ["restore folder", "restore project", "restore", "unhide folder", "unhide project", "unhide", "show folder", "show project", "show"],
            "LIST_HIDDEN": ["show hidden folders", "show hidden items", "show hidden", "list hidden folders", "list hidden items", "list hidden", "what have i hidden"],
            "OPEN_HIDDEN": ["open hidden folder", "open hidden project", "open hidden"],
            "OPEN_APPLICATION": ["can you open", "please open", "open", "launch", "start", "run", "bring up", "execute"]
        }

    def classify(self, text: str) -> IntentResult:
        normalized = text.lower().strip().rstrip(".?!,")
        tokens = [t for t in re.split(r"\s+", normalized) if t]
        
        # Default fallback is UNKNOWN
        intent = "UNKNOWN"
        entity = normalized
        confidence = 0.5
        metadata = {}

        # 1. Check for specific trailing web search hints or direct prefixes
        if normalized.startswith("google "):
            intent = "WEB_SEARCH"
            entity = text[7:].strip().rstrip(".?!,")
            metadata["provider"] = "google"
            return IntentResult(intent, entity, normalized, 1.0, tokens, metadata)
        elif normalized.startswith("youtube "):
            intent = "WEB_SEARCH"
            entity = text[8:].strip().rstrip(".?!,")
            metadata["provider"] = "youtube"
            return IntentResult(intent, entity, normalized, 1.0, tokens, metadata)
        elif normalized.endswith(" on google"):
            intent = "WEB_SEARCH"
            entity = text[:-10].strip() # keep original casing for searches!
            metadata["provider"] = "google"
            return IntentResult(intent, entity, normalized, 1.0, tokens, metadata)
        elif normalized.endswith(" on youtube"):
            intent = "WEB_SEARCH"
            entity = text[:-11].strip()
            metadata["provider"] = "youtube"
            return IntentResult(intent, entity, normalized, 1.0, tokens, metadata)


        # 2. Check prefix matches
        matched_prefix = False
        for intent_name, verbs in self.prefixes.items():
            for verb in verbs:
                if normalized == verb:
                    matched_prefix = True
                    intent = intent_name
                    entity = ""
                    confidence = 1.0
                    break
                elif normalized.startswith(verb + " "):
                    matched_prefix = True
                    intent = intent_name
                    # Extract the raw entity by slicing the original casing string
                    verb_len = len(verb)
                    entity = text[verb_len:].strip().rstrip(".?!,")
                    confidence = 1.0
                    break
            if matched_prefix:
                break

        # 3. Contextual Entity Refinements
        entity_lower = entity.lower().strip()
        
        # Folder checks
        folders = ["downloads", "desktop", "documents", "pictures", "videos"]
        if entity_lower in folders or (intent == "OPEN_APPLICATION" and entity_lower.replace("folder", "").strip() in folders):
            intent = "OPEN_FOLDER"
            entity = entity_lower.replace("folder", "").strip().capitalize()
            confidence = 1.0
            
        # Settings checks
        settings_keywords = ["settings", "control panel", "wifi", "wi-fi", "bluetooth", "display", "sound", "network"]
        if any(x in entity_lower for x in settings_keywords):
            intent = "OPEN_SETTINGS"
            confidence = 1.0

        # Website checks
        websites = ["youtube", "chatgpt", "chat gpt", "gmail", "github", "google", "stackoverflow"]
        if entity_lower in websites or entity_lower.endswith(".com") or entity_lower.endswith(".org") or entity_lower.endswith(".net"):
            intent = "OPEN_WEBSITE"
            confidence = 1.0

        # System actions checks without prefix
        if normalized in ["shutdown", "restart", "reboot", "power off", "exit", "quit", "poweroff"]:
            intent = "SYSTEM_ACTION"
            entity = normalized
            confidence = 1.0

        # 4. Fallback: if no prefix matched and it wasn't refined, it might just be an app name (e.g. "chrome")
        if intent == "UNKNOWN":
            intent = "OPEN_APPLICATION" # Default guess for raw single strings
            entity = text.strip()
            confidence = 0.6

        return IntentResult(
            intent=intent,
            entity=entity,
            normalized_text=normalized,
            confidence=confidence,
            tokens=tokens,
            metadata=metadata
        )
