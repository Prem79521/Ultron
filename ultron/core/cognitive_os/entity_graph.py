"""
ULTRON Cognitive OS — Optimized RAM Entity Knowledge Graph.
"""

from typing import Dict, Any, List, Tuple, Optional
from ultron.core.cognitive_os.base_matcher import BaseMatcher

class UltronEntity:
    """Represents a unified system entity (Application, Game, Folder, Setting, Website)."""
    def __init__(
        self,
        name: str,
        category: str,
        executable: str = "",
        website: str = "",
        publisher: str = "",
        install_path: str = "",
        aliases: Dict[str, float] = None,
        metadata: Dict[str, Any] = None
    ):
        self.name = name
        self.category = category # "application", "game", "folder", "settings", "website"
        self.executable = executable
        self.website = website
        self.publisher = publisher
        self.install_path = install_path
        self.aliases = aliases or {} # alias_name -> weight (float)
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "executable": self.executable,
            "website": self.website,
            "publisher": self.publisher,
            "install_path": self.install_path,
            "aliases": self.aliases,
            "metadata": self.metadata
        }

class EntityKnowledgeGraph:
    """Manages discoverable OS entities with O(1) RAM cache lookups."""
    def __init__(self):
        self._entities: Dict[str, UltronEntity] = {}
        
        # RAM caches for O(1) lookups
        self.alias_lookup: Dict[str, Tuple[UltronEntity, float]] = {}
        self.application_lookup: Dict[str, Tuple[UltronEntity, float]] = {}
        self.website_lookup: Dict[str, Tuple[UltronEntity, float]] = {}
        self.folder_lookup: Dict[str, Tuple[UltronEntity, float]] = {}
        self.settings_lookup: Dict[str, Tuple[UltronEntity, float]] = {}
        
        self._prepopulate_builtins()

    def add_entity(self, entity: UltronEntity):
        name_key = entity.name.lower().strip()
        self._entities[name_key] = entity
        
        # Add to lookup tables for O(1) retrieval
        for alias, weight in entity.aliases.items():
            alias_key = alias.lower().strip()
            val = (entity, weight)
            self.alias_lookup[alias_key] = val
            
            if entity.category in ["application", "game"]:
                self.application_lookup[alias_key] = val
            elif entity.category == "website":
                self.website_lookup[alias_key] = val
            elif entity.category == "folder":
                self.folder_lookup[alias_key] = val
            elif entity.category == "settings":
                self.settings_lookup[alias_key] = val

    def get_entity(self, name: str) -> Optional[UltronEntity]:
        name_key = name.lower().strip()
        # Check direct graph key
        if name_key in self._entities:
            return self._entities[name_key]
        # Fallback to alias lookup
        if name_key in self.alias_lookup:
            return self.alias_lookup[name_key][0]
        return None

    def list_entities(self) -> List[UltronEntity]:
        return list(self._entities.values())

    def search(self, query: str, matcher: BaseMatcher, cutoff: float = 0.5) -> List[Tuple[UltronEntity, float]]:
        """
        Searches the Entity Graph with fallback levels:
        1. O(1) RAM Cache exact alias hit (0ms).
        2. Fuzzy string matching over all entities using BaseMatcher.
        """
        query_clean = query.lower().strip()
        
        # Level 1: O(1) RAM Cache direct lookup
        if query_clean in self.alias_lookup:
            ent, weight = self.alias_lookup[query_clean]
            return [(ent, 1.0 * weight)]

        # Level 2: Fuzzy matching fallback
        results = []
        for entity in self._entities.values():
            best_entity_score = 0.0
            
            if query_clean == entity.name.lower().strip():
                best_entity_score = 1.0
            
            for alias, weight in entity.aliases.items():
                sim = matcher.ratio(query_clean, alias)
                weighted_score = sim * weight
                if weighted_score > best_entity_score:
                    best_entity_score = weighted_score
            
            if best_entity_score >= cutoff:
                results.append((entity, best_entity_score))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def _prepopulate_builtins(self):
        # 1. Folders
        folders = ["downloads", "desktop", "documents", "pictures", "videos"]
        for f in folders:
            self.add_entity(UltronEntity(
                name=f.capitalize(),
                category="folder",
                aliases={f: 1.0, f"my {f}": 0.8, f"{f} folder": 0.9}
            ))

        # 2. Settings
        settings_map = {
            "Settings": (["settings", "control panel"], "ms-settings:"),
            "Bluetooth": (["bluetooth", "bluetooth settings"], "ms-settings:bluetooth"),
            "Wifi": (["wifi", "wifi settings", "wi-fi", "wi-fi settings"], "ms-settings:network-wifi"),
            "Display": (["display", "display settings", "screen settings"], "ms-settings:display"),
            "Sound": (["sound", "sound settings", "volume settings"], "ms-settings:sound"),
            "Network": (["network", "network settings", "internet settings"], "ms-settings:network")
        }
        for name, (aliases, uri) in settings_map.items():
            alias_weights = {a: 1.0 for a in aliases}
            if name == "Settings":
                alias_weights["control panel"] = 0.7
            self.add_entity(UltronEntity(
                name=name,
                category="settings",
                executable=uri,
                aliases=alias_weights
            ))

        # 3. Websites
        websites_map = {
            "YouTube": (["youtube", "yt", "play music", "play video"], "https://youtube.com"),
            "ChatGPT": (["chatgpt", "chat gpt", "openai", "ai chat"], "https://chat.openai.com"),
            "Gmail": (["gmail", "google mail", "mail", "inbox"], "https://gmail.com"),
            "GitHub": (["github", "git hub", "git repo"], "https://github.com"),
            "Google": (["google", "googel", "search engine"], "https://google.com"),
            "StackOverflow": (["stackoverflow", "stack overflow", "coding help"], "https://stackoverflow.com")
        }
        for name, (aliases, url) in websites_map.items():
            alias_weights = {a: 1.0 for a in aliases}
            if "play music" in alias_weights:
                alias_weights["play music"] = 0.5
            if "mail" in alias_weights:
                alias_weights["mail"] = 0.6
            if "openai" in alias_weights:
                alias_weights["openai"] = 0.7
            self.add_entity(UltronEntity(
                name=name,
                category="website",
                website=url,
                aliases=alias_weights
            ))
            
        # 4. Standard Apps
        apps_map = {
            "Calculator": (["calculator", "calc"], "calc.exe"),
            "Notepad": (["notepad", "text editor"], "notepad.exe"),
            "Paint": (["paint", "mspaint", "draw"], "mspaint.exe"),
            "Task Manager": (["task manager", "taskmgr", "activity monitor"], "taskmgr.exe"),
            "Device Manager": (["device manager", "devmgmt"], "devmgmt.msc"),
            "File Explorer": (["file explorer", "explorer", "my computer"], "explorer.exe")
        }
        for name, (aliases, exec_path) in apps_map.items():
            alias_weights = {a: 1.0 for a in aliases}
            if "draw" in alias_weights:
                alias_weights["draw"] = 0.5
            self.add_entity(UltronEntity(
                name=name,
                category="application",
                executable=exec_path,
                aliases=alias_weights
            ))
