import logging
import time
import json
import os
import winreg
import re
from typing import Optional, Dict, Any, Tuple
from ultron.core.cognitive_os.intent_engine import IntentResult
from ultron.core.cognitive_os.entity_graph import EntityKnowledgeGraph, UltronEntity
from ultron.core.cognitive_os.base_matcher import BaseMatcher
from ultron.core.cognitive_os.learning_memory import LearningMemory

def find_browser_executable_path(exec_name: str) -> Optional[str]:
    """
    Searches for a browser executable (e.g. chrome.exe, msedge.exe)
    using Registry, PATH, Program Files, Program Files (x86), LocalAppData, WindowsApps.
    """
    exec_name = exec_name.lower().strip()
    if not exec_name.endswith(".exe"):
        exec_name += ".exe"

    # 1. Query Registry App Paths
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            reg_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{exec_name}"
            with winreg.OpenKey(root, reg_path) as key:
                val, _ = winreg.QueryValueEx(key, "")
                if val and os.path.exists(val):
                    return val
        except Exception:
            pass

    # 2. Query PATH
    path_env = os.environ.get("PATH", "")
    for p in path_env.split(os.pathsep):
        full_path = os.path.join(p, exec_name)
        if os.path.exists(full_path):
            return full_path

    # 3. Check Program Files, Program Files (x86), LocalAppData, WindowsApps
    user_profile = os.environ.get("USERPROFILE", "C:\\Users\\default")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    
    # Common locations for these browsers
    search_dirs = [
        os.path.join(program_files, "Google\\Chrome\\Application"),
        os.path.join(program_files_x86, "Google\\Chrome\\Application"),
        os.path.join(program_files_x86, "Microsoft\\Edge\\Application"),
        os.path.join(program_files, "Microsoft\\Edge\\Application"),
        os.path.join(program_files, "Mozilla Firefox"),
        os.path.join(program_files_x86, "Mozilla Firefox"),
        os.path.join(program_files, "BraveSoftware\\Brave-Browser\\Application"),
        os.path.join(local_app_data, "BraveSoftware\\Brave-Browser\\Application"),
        os.path.join(program_files, "Opera"),
        os.path.join(local_app_data, "Programs\\Opera"),
        os.path.join(program_files, "Vivaldi\\Application"),
        os.path.join(local_app_data, "Vivaldi\\Application"),
        os.path.join(local_app_data, "Programs\\Arc"),
        os.path.join(local_app_data, "Microsoft\\WindowsApps"),
        os.path.join(program_files, "WindowsApps")
    ]
    
    for d in search_dirs:
        full_path = os.path.join(d, exec_name)
        if os.path.exists(full_path):
            return full_path

    # 4. If still not found, do a shallow scan in WindowsApps or LocalAppData
    check_roots = [local_app_data, os.path.join(program_files, "WindowsApps")]
    for root_dir in check_roots:
        if not root_dir or not os.path.exists(root_dir):
            continue
        try:
            for root, dirs, files in os.walk(root_dir):
                # Restrict depth to 2
                rel_depth = root[len(root_dir):].count(os.sep)
                if rel_depth > 2:
                    dirs.clear()
                    continue
                for f in files:
                    if f.lower() == exec_name:
                        return os.path.join(root, f)
        except Exception:
            pass

    return None


# Centralized thresholds (Task 8 / Section 14)
RESOLVER_THRESHOLDS = {
    "IMMEDIATE_LAUNCH": 0.90,
    "ASK_CONFIRMATION": 0.75,
    "MATCH_CUTOFF": 0.50
}

class BaseResolver:
    """Base abstract handler for the resolver chain."""
    def __init__(self):
        self._next_handler: Optional[BaseResolver] = None
        self.logger = logging.getLogger("ultron-agent")

    def set_next(self, handler: 'BaseResolver') -> 'BaseResolver':
        self._next_handler = handler
        return handler

    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        if self._next_handler:
            return self._next_handler.resolve(intent, context)
        return {"success": False, "action": "fail", "spoken_response": "I couldn't understand that command."}


class LearningMemoryResolver(BaseResolver):
    """Stage 1: Checks UME learning memory for previously confirmed mapping matches."""
    def __init__(self, learning_memory: LearningMemory):
        super().__init__()
        self.learning = learning_memory

    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 1: Learning Memory")
        
        mapping = self.learning.get_mapping(intent.normalized_text)
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Stage 1 Latency: {dur_ms:.2f}ms")
        
        if mapping:
            entity_name = mapping["resolved_entity"]
            graph: EntityKnowledgeGraph = context["entity_graph"]
            entity = graph.get_entity(entity_name)
            
            if entity:
                self.logger.info(f"STATUS: SUCCESS | Instantly matched '{intent.normalized_text}' -> '{entity.name}'")
                return {
                    "success": True,
                    "action": "execute",
                    "entity": entity,
                    "spoken_response": f"Opening {entity.name}.",
                    "source": "learning_memory",
                    "confidence": 1.0,
                    "latency_ms": dur_ms
                }
        self.logger.info("STATUS: FAILED")
        return super().resolve(intent, context)


class ExactAliasResolver(BaseResolver):
    """Stage 2: Checks the O(1) RAM Cache exact alias dictionary."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 2: Exact Cache / Alias Cache")
        graph: EntityKnowledgeGraph = context["entity_graph"]
        query_clean = intent.entity.lower().strip()
        
        matches = []
        for entity in graph.list_entities():
            for alias, weight in entity.aliases.items():
                if query_clean == alias.lower().strip():
                    matches.append((entity, 1.0 * weight))
                    
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Stage 2 Latency: {dur_ms:.2f}ms")
        
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            best_entity, score = matches[0]
            
            if score >= RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                self.logger.info(f"STATUS: SUCCESS | Exact alias match: '{best_entity.name}' (confidence: {score:.2f})")
                return {
                    "success": True,
                    "action": "execute",
                    "entity": best_entity,
                    "spoken_response": f"Opening {best_entity.name}.",
                    "source": "exact_alias_match",
                    "confidence": score,
                    "latency_ms": dur_ms
                }
            elif RESOLVER_THRESHOLDS["ASK_CONFIRMATION"] <= score < RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                choices = [m[0] for m in matches if m[1] >= RESOLVER_THRESHOLDS["ASK_CONFIRMATION"]][:5]
                if len(choices) > 1:
                    choice_strings = [f"{i+1}. {c.name}" for i, c in enumerate(choices)]
                    spoken = f"Did you mean: {', or '.join(choice_strings)}?"
                    self.logger.info(f"STATUS: SUCCESS (requires multiple choice confirmation: {choice_strings})")
                    return {
                        "success": True,
                        "action": "confirm",
                        "type": "choices",
                        "choices": choices,
                        "entity": choices[0],
                        "spoken_response": spoken,
                        "source": "exact_alias_confirm",
                        "confidence": score,
                        "latency_ms": dur_ms
                    }
                else:
                    self.logger.info(f"STATUS: SUCCESS (requires confirmation) | Exact alias match: '{best_entity.name}' (confidence: {score:.2f})")
                    return {
                        "success": True,
                        "action": "confirm",
                        "entity": best_entity,
                        "spoken_response": f"Did you mean {best_entity.name}?",
                        "source": "exact_alias_confirm",
                        "confidence": score,
                        "latency_ms": dur_ms
                    }
                    
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Stage 2 Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class FuzzyAliasResolver(BaseResolver):
    """Stage 3: Performs full fuzzy sequence matching over all entity aliases."""
    def __init__(self, matcher: BaseMatcher, cutoff: float = None):
        super().__init__()
        self.matcher = matcher
        self.cutoff = cutoff if cutoff is not None else RESOLVER_THRESHOLDS["MATCH_CUTOFF"]

    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 3: Fuzzy Match")
        graph: EntityKnowledgeGraph = context["entity_graph"]
        query_clean = intent.entity.lower().strip()
        
        results = []
        for entity in graph.list_entities():
            best_score = 0.0
            if query_clean == entity.name.lower().strip():
                best_score = 1.0
                
            for alias, weight in entity.aliases.items():
                sim = self.matcher.ratio(query_clean, alias)
                weighted_score = sim * weight
                if weighted_score > best_score:
                    best_score = weighted_score
            
            if best_score >= self.cutoff:
                results.append((entity, best_score))
                
        matches = sorted(results, key=lambda x: x[1], reverse=True)
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Stage 3 Latency: {dur_ms:.2f}ms")
        
        if matches:
            best_entity, score = matches[0]
            self.logger.info(f"Candidate: {best_entity.name} | Similarity: {score * 100:.1f}%")
            if score >= RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                self.logger.info("STATUS: SUCCESS")
                return {
                    "success": True,
                    "action": "execute",
                    "entity": best_entity,
                    "spoken_response": f"Opening {best_entity.name}.",
                    "source": "fuzzy_alias_match",
                    "confidence": score,
                    "latency_ms": dur_ms
                }
            elif RESOLVER_THRESHOLDS["ASK_CONFIRMATION"] <= score < RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                # Check if there are multiple candidates in the confirmation range (Task 3 / Section 14)
                choices = [m[0] for m in matches if m[1] >= RESOLVER_THRESHOLDS["ASK_CONFIRMATION"]][:5]
                if len(choices) > 1:
                    choice_strings = [f"{i+1}. {c.name}" for i, c in enumerate(choices)]
                    spoken = f"Did you mean: {', or '.join(choice_strings)}?"
                    self.logger.info(f"STATUS: SUCCESS (requires multiple choice confirmation: {choice_strings})")
                    return {
                        "success": True,
                        "action": "confirm",
                        "type": "choices",
                        "choices": choices,
                        "entity": choices[0],
                        "spoken_response": spoken,
                        "source": "fuzzy_alias_confirm",
                        "confidence": score,
                        "latency_ms": dur_ms
                    }
                else:
                    self.logger.info("STATUS: SUCCESS (requires confirmation)")
                    return {
                        "success": True,
                        "action": "confirm",
                        "entity": best_entity,
                        "spoken_response": f"Did you mean {best_entity.name}?",
                        "source": "fuzzy_alias_confirm",
                        "confidence": score,
                        "latency_ms": dur_ms
                    }
        self.logger.info("STATUS: FAILED")
        return super().resolve(intent, context)


class IndexedApplicationsResolver(BaseResolver):
    """Stage 4: Queries SQLite database app cache directly as fallback lookup."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 4: Indexed Applications (SQLite Cache)")
        query_clean = intent.entity.lower().strip()
        
        # Load from SQLite database store directly
        res = None
        try:
            from ultron.memory import get_memory_manager
            mem = get_memory_manager()
            if mem:
                records = mem.list_records("app_cache", limit=1000)
                candidates = []
                for r in records:
                    app_data = json.loads(r["content"])
                    name = app_data["name"]
                    aliases = app_data.get("aliases", {})
                    
                    # Direct key check
                    best_score = 0.0
                    if query_clean == name.lower().strip():
                        best_score = 1.0
                    for alias, weight in aliases.items():
                        if query_clean == alias.lower().strip():
                            best_score = max(best_score, 1.0 * weight)
                            
                    if best_score >= RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                        candidates.append((app_data, best_score))
                        
                if candidates:
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    best_app, score = candidates[0]
                    metadata = {
                        "working_dir": best_app.get("working_dir", ""),
                        "last_modified": best_app.get("last_modified", "")
                    }
                    entity = UltronEntity(
                        name=best_app["name"],
                        category=best_app["category"],
                        executable=best_app["executable"],
                        publisher=best_app["publisher"],
                        install_path=best_app["install_path"],
                        aliases=best_app["aliases"],
                        metadata=metadata
                    )
                    # Add to graph cache
                    context["entity_graph"].add_entity(entity)
                    dur_ms = (time.perf_counter() - start_time) * 1000
                    self.logger.info(f"Stage 4 Latency: {dur_ms:.2f}ms | STATUS: SUCCESS")
                    res = {
                        "success": True,
                        "action": "execute",
                        "entity": entity,
                        "spoken_response": f"Opening {entity.name}.",
                        "source": "indexed_app_match",
                        "confidence": score,
                        "latency_ms": dur_ms
                    }
        except Exception as e:
            self.logger.error(f"Error querying SQLite app cache in Stage 4: {e}")

        if res:
            return res
            
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Stage 4 Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class DynamicSearchResolver(BaseResolver):
    """Stage 5: Performs targeted Windows dynamic search on demand with timeout."""
    def __init__(self, indexer: Any):
        super().__init__()
        self.indexer = indexer

    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 5: Dynamic Windows Search")
        if intent.intent in ["OPEN_APPLICATION", "PLAY_MEDIA"]:
            entity = self.indexer.dynamic_search(intent.entity)
            dur_ms = (time.perf_counter() - start_time) * 1000
            self.logger.info(f"Stage 5 Latency: {dur_ms:.2f}ms")
            
            if entity:
                graph = context["entity_graph"]
                # Store discovered application to prevent future searches
                self.indexer.cache_newly_discovered_app(entity, graph, query=intent.entity)
                
                score = 0.95 if entity.name.lower().strip() == intent.entity.lower().strip() else 0.80
                if score >= RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                    self.logger.info("STATUS: SUCCESS")
                    return {
                        "success": True,
                        "action": "execute",
                        "entity": entity,
                        "spoken_response": f"Opening {entity.name}.",
                        "source": "dynamic_search",
                        "confidence": score,
                        "latency_ms": dur_ms
                    }
                else:
                    self.logger.info("STATUS: SUCCESS (requires confirmation)")
                    return {
                        "success": True,
                        "action": "confirm",
                        "entity": entity,
                        "spoken_response": f"Did you mean {entity.name}?",
                        "source": "dynamic_search_confirm",
                        "confidence": score,
                        "latency_ms": dur_ms
                    }
                    
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Stage 5 Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class BrowserResolver(BaseResolver):
    """Stage 5/6: Dynamically resolves browser applications using registry."""
    def __init__(self, indexer: Any = None):
        super().__init__()
        self.indexer = indexer

    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage: Browser Resolver")
        
        query_clean = intent.entity.lower().strip()
        
        # Discover all installed browsers dynamically from registry (Task 3 / Section 14)
        browsers = {}
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                reg_path = "SOFTWARE\\Clients\\StartMenuInternet"
                with winreg.OpenKey(root, reg_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, f"{subkey_name}\\shell\\open\\command") as cmd_key:
                                val, _ = winreg.QueryValueEx(cmd_key, "")
                                if val:
                                    path = val.strip().replace('"', '')
                                    if os.path.exists(path):
                                        name_clean = subkey_name.lower().replace(".exe", "")
                                        browsers[name_clean] = path
                                        try:
                                            with winreg.OpenKey(key, subkey_name) as b_key:
                                                disp, _ = winreg.QueryValueEx(b_key, "")
                                                if disp:
                                                    browsers[disp.lower()] = path
                                        except Exception:
                                            pass
                        except Exception:
                            pass
            except Exception:
                pass
                
        # If we didn't find any browsers via StartMenuInternet, fall back to search common paths
        if not browsers:
            common = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe", "arc.exe"]
            for b in common:
                path = find_browser_executable_path(b)
                if path:
                    browsers[b.replace(".exe", "")] = path
                    
        # Check if the query matches any browser name or alias
        matched_path = None
        matched_name = None
        for name, path in browsers.items():
            if query_clean == name or query_clean in name or name in query_clean:
                matched_path = path
                matched_name = name.title()
                break
                
        if intent.intent == "OPEN_APPLICATION" and matched_path:
            dur_ms = (time.perf_counter() - start_time) * 1000
            browser_entity = UltronEntity(
                name=matched_name,
                category="browser",
                executable=matched_path,
                aliases={query_clean: 1.0}
            )
            
            indexer = self.indexer or context.get("indexer")
            if indexer:
                graph = context["entity_graph"]
                indexer.cache_newly_discovered_app(browser_entity, graph, query_clean)
                
            self.logger.info(f"STATUS: SUCCESS | Resolved browser {matched_name} to: {matched_path}")
            return {
                "success": True,
                "action": "execute",
                "entity": browser_entity,
                "spoken_response": f"Opening {matched_name}.",
                "source": "browser_resolver",
                "confidence": 1.0,
                "latency_ms": dur_ms
            }
            
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Browser Resolver Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)



class WebsiteResolver(BaseResolver):
    """Stage 7: Website Resolver."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 7: Website Resolver")
        
        res = None
        if intent.intent == "OPEN_WEBSITE":
            graph: EntityKnowledgeGraph = context["entity_graph"]
            matches = graph.search(intent.entity, context["matcher"], 0.5)
            web_matches = [m for m in matches if m[0].category == "website"]
            dur_ms = (time.perf_counter() - start_time) * 1000
            self.logger.info(f"Stage 7 Latency: {dur_ms:.2f}ms")
            
            if web_matches:
                best_web, score = web_matches[0]
                if score >= RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                    self.logger.info(f"STATUS: SUCCESS | Website matched: {best_web.name}")
                    return {
                        "success": True,
                        "action": "execute",
                        "entity": best_web,
                        "spoken_response": f"Opening {best_web.name}.",
                        "source": "website_match",
                        "confidence": score,
                        "latency_ms": dur_ms
                    }
                elif RESOLVER_THRESHOLDS["ASK_CONFIRMATION"] <= score < RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                    self.logger.info(f"STATUS: SUCCESS (requires confirmation) | Website matched: {best_web.name}")
                    return {
                        "success": True,
                        "action": "confirm",
                        "entity": best_web,
                        "spoken_response": f"Did you mean {best_web.name}?",
                        "source": "website_match_confirm",
                        "confidence": score,
                        "latency_ms": dur_ms
                    }
            if intent.entity.endswith((".com", ".org", ".net", ".io")):
                url = intent.entity if intent.entity.startswith("http") else f"https://{intent.entity}"
                fallback_entity = UltronEntity(name=intent.entity, category="website", website=url)
                self.logger.info(f"STATUS: SUCCESS | Direct website URL parsed: {url}")
                return {
                    "success": True,
                    "action": "execute",
                    "entity": fallback_entity,
                    "spoken_response": f"Navigating to {intent.entity}.",
                    "source": "website_url_fallback",
                    "confidence": 1.0,
                    "latency_ms": dur_ms
                }
        
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Stage 7 Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class FolderResolver(BaseResolver):
    """Stage 8: Resolves folder intents using a fast recursive fuzzy search."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 8: Folder Resolver (Recursive Fuzzy Search)")
        
        query_clean = intent.entity.lower().strip()
        # Remove helper words like "my", "folder"
        words_to_remove = {"my", "the", "a", "an", "folder", "project", "directory"}
        query_words = [w for w in re.split(r"[\s\-_]+", query_clean) if w and w not in words_to_remove]
        search_term = " ".join(query_words) if query_words else query_clean
        
        if not search_term or intent.intent not in ["OPEN_APPLICATION", "OPEN_FOLDER", "UNKNOWN"]:
            return super().resolve(intent, context)
            
        user_profile = os.environ.get("USERPROFILE", "C:\\Users\\default")
        workspace_parent = os.path.dirname("c:\\Users\\craft\\Desktop\\Ultron")
        
        search_roots = [
            os.path.join(user_profile, "Desktop"),
            os.path.join(user_profile, "Documents"),
            os.path.join(user_profile, "Downloads"),
            user_profile,
            workspace_parent
        ]
        
        candidates = []
        seen_paths = set()
        
        def scan_root(root_dir: str):
            if not os.path.isdir(root_dir):
                return
            try:
                root_depth = root_dir.count(os.sep)
                for root, dirs, files in os.walk(root_dir):
                    # Prune unneeded/massive dirs (Task 2 / Section 14)
                    prune_dirs = {".git", "node_modules", "venv", ".venv", "appdata", "local", "roaming", "__pycache__", "temp", "tmp"}
                    dirs[:] = [d for d in dirs if d.lower() not in prune_dirs and not d.startswith(".")]
                    
                    current_depth = root.count(os.sep)
                    if current_depth - root_depth >= 2:
                        dirs.clear() # Prune deeper walks
                        
                    for d in dirs:
                         path = os.path.join(root, d)
                         if path in seen_paths:
                             continue
                         seen_paths.add(path)
                         
                         d_lower = d.lower()
                         if search_term == d_lower:
                             score = 1.0
                         elif d_lower.startswith(search_term):
                             score = 0.90 * (len(search_term) / len(d_lower))
                         elif search_term in d_lower:
                             score = 0.80 * (len(search_term) / len(d_lower))
                         else:
                             score = context["matcher"].ratio(search_term, d_lower)
                             
                         if score >= 0.70:
                             candidates.append({
                                 "name": d,
                                 "path": path,
                                 "score": score
                             })
            except Exception:
                pass
                
        for root in search_roots:
            scan_root(root)
            
        if candidates:
            candidates.sort(key=lambda x: x["score"], reverse=True)
            best = candidates[0]
            dur_ms = (time.perf_counter() - start_time) * 1000
            self.logger.info(f"Folder Resolver Best Candidate: '{best['name']}' at {best['path']} (score: {best['score']:.2f})")
            
            entity = UltronEntity(
                name=best["name"],
                category="folder",
                executable=best["path"],
                aliases={best["name"].lower(): 1.0}
            )
            
            # Save dynamically discovered folder immediately to cache & learning memory (Task 6 / Section 14)
            try:
                # Add directly to graph cache
                context["entity_graph"].add_entity(entity)
                
                indexer = context.get("indexer")
                if indexer:
                    indexer.cache_newly_discovered_app(entity, context["entity_graph"], query=intent.entity)
                
                learning_memory = context.get("learning_memory")
                if learning_memory:
                    learning_memory.learn(intent.entity, entity.name, best["score"], "folder_resolver")
            except Exception:
                pass
                
            if best["score"] >= RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                self.logger.info(f"STATUS: SUCCESS | Folder Resolved: '{best['name']}'")
                return {
                    "success": True,
                    "action": "execute",
                    "entity": entity,
                    "spoken_response": f"Opening {best['name']} folder.",
                    "source": "folder_resolver",
                    "confidence": best["score"],
                    "latency_ms": dur_ms
                }
            elif RESOLVER_THRESHOLDS["ASK_CONFIRMATION"] <= best["score"] < RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                self.logger.info(f"STATUS: SUCCESS (requires confirmation)")
                return {
                    "success": True,
                    "action": "confirm",
                    "entity": entity,
                    "spoken_response": f"Did you mean {best['name']} folder?",
                    "source": "folder_resolver_confirm",
                    "confidence": best["score"],
                    "latency_ms": dur_ms
                }
                
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Folder Resolver Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class SettingsResolver(BaseResolver):
    """Stage 9: Resolves setting/URI intents."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 9: Settings Resolver")
        
        res = None
        if intent.intent == "OPEN_SETTINGS":
            graph: EntityKnowledgeGraph = context["entity_graph"]
            matches = graph.search(intent.entity, context["matcher"], 0.5)
            settings_matches = [m for m in matches if m[0].category == "settings"]
            dur_ms = (time.perf_counter() - start_time) * 1000
            self.logger.info(f"Stage 9 Latency: {dur_ms:.2f}ms")
            
            if settings_matches:
                best_setting, score = settings_matches[0]
                if score >= RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                    return {
                        "success": True,
                        "action": "execute",
                        "entity": best_setting,
                        "spoken_response": f"Opening {best_setting.name} Settings.",
                        "source": "settings_match",
                        "confidence": score,
                        "latency_ms": dur_ms
                    }
                    
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Stage 9 Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class WebSearchResolver(BaseResolver):
    """Stage 10: Web Search Resolver."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 10: Web Search Resolver")
        
        if intent.intent == "WEB_SEARCH":
            provider = intent.metadata.get("provider", "google")
            action = "google_search" if provider == "google" else "youtube_search"
            dest_name = "Google" if provider == "google" else "YouTube"
            
            search_entity = UltronEntity(
                name=f"{dest_name} Search",
                category="search",
                aliases={},
                metadata={"action": action, "query": intent.entity}
            )
            dur_ms = (time.perf_counter() - start_time) * 1000
            self.logger.info(f"Stage 10 Latency: {dur_ms:.2f}ms | STATUS: SUCCESS")
            return {
                "success": True,
                "action": "execute",
                "entity": search_entity,
                "spoken_response": f"Searching {dest_name} for {intent.entity}.",
                "source": "web_search",
                "confidence": 1.0,
                "latency_ms": dur_ms
            }
            
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Stage 10 Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class FileResolver(BaseResolver):
    """Stage 10: Resolves document/file requests by searching user directories."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 10: File Resolver")
        
        query_clean = intent.entity.lower().strip()
        # Remove helper words
        words_to_remove = {"my", "the", "a", "an", "folder", "file", "document", "notes"}
        query_words = [w for w in re.split(r"[\s\-_]+", query_clean) if w and w not in words_to_remove]
        search_term = " ".join(query_words) if query_words else query_clean
        
        if not search_term or intent.intent not in ["OPEN_APPLICATION", "UNKNOWN"]:
            return super().resolve(intent, context)
            
        user_profile = os.environ.get("USERPROFILE", "C:\\Users\\default")
        search_dirs = [
            os.path.join(user_profile, "Desktop"),
            os.path.join(user_profile, "Documents"),
            os.path.join(user_profile, "Downloads"),
            os.path.join(user_profile, "AppData\\Roaming\\Microsoft\\Windows\\Recent")
        ]
        
        candidates = []
        allowed_exts = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".png", ".jpg", ".zip"}
        
        for d in search_dirs:
            if not os.path.exists(d):
                continue
            try:
                with os.scandir(d) as entries:
                    for entry in entries:
                        if entry.is_file():
                            name, ext = os.path.splitext(entry.name)
                            ext_lower = ext.lower()
                            if ext_lower not in allowed_exts:
                                continue
                            name_lower = name.lower()
                            
                            # Check if search term is in filename
                            if search_term in name_lower:
                                ratio = len(search_term) / len(name_lower)
                                candidates.append((entry.path, ratio))
                            else:
                                sim = context["matcher"].ratio(search_term, name_lower)
                                if sim >= 0.70:
                                    candidates.append((entry.path, sim))
            except Exception:
                pass
                
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_path, score = candidates[0]
            display_name = os.path.basename(best_path)
            
            file_entity = UltronEntity(
                name=display_name,
                category="document",
                executable=best_path,
                aliases={query_clean: 1.0}
            )
            
            dur_ms = (time.perf_counter() - start_time) * 1000
            self.logger.info(f"STATUS: SUCCESS | Resolved document {display_name} to: {best_path} (score: {score:.2f})")
            
            if score >= RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                return {
                    "success": True,
                    "action": "execute",
                    "entity": file_entity,
                    "spoken_response": f"Opening {display_name}.",
                    "source": "file_resolver",
                    "confidence": score,
                    "latency_ms": dur_ms
                }
            elif RESOLVER_THRESHOLDS["ASK_CONFIRMATION"] <= score < RESOLVER_THRESHOLDS["IMMEDIATE_LAUNCH"]:
                return {
                    "success": True,
                    "action": "confirm",
                    "entity": file_entity,
                    "spoken_response": f"Did you mean {display_name}?",
                    "source": "file_resolver_confirm",
                    "confidence": score,
                    "latency_ms": dur_ms
                }
                
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"File Resolver Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class ShellNamespaceResolver(BaseResolver):
    """Stage: Resolves Windows Shell Namespace folders (e.g. recycle bin, control panel)."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage: Shell Namespace Resolver")
        
        query_clean = intent.entity.lower().strip()
        
        shell_mappings = {
            "recycle bin": "shell:RecycleBinFolder",
            "recyclebin": "shell:RecycleBinFolder",
            "control panel": "shell:ControlPanelFolder",
            "downloads": "shell:Downloads",
            "desktop": "shell:Desktop",
            "documents": "shell:Personal",
            "my documents": "shell:Personal",
            "apps": "shell:AppsFolder",
            "applications": "shell:AppsFolder",
            "startup": "shell:Startup",
            "recent": os.path.expandvars("%APPDATA%\\Microsoft\\Windows\\Recent")
        }
        
        matched_uri = None
        matched_name = None
        for term, uri in shell_mappings.items():
            if query_clean == term or query_clean in term or term in query_clean:
                matched_uri = uri
                matched_name = term.title()
                break
                
        if intent.intent == "OPEN_APPLICATION" and matched_uri:
            dur_ms = (time.perf_counter() - start_time) * 1000
            entity = UltronEntity(
                name=matched_name,
                category="folder" if "folder" in matched_uri.lower() or matched_uri.startswith("shell:") else "application",
                executable=matched_uri,
                aliases={query_clean: 1.0}
            )
            self.logger.info(f"STATUS: SUCCESS | Resolved Shell Namespace {matched_name} to: {matched_uri}")
            return {
                "success": True,
                "action": "execute",
                "entity": entity,
                "spoken_response": f"Opening {matched_name}.",
                "source": "shell_namespace_resolver",
                "confidence": 1.0,
                "latency_ms": dur_ms
            }
            
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Shell Namespace Resolver Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class WorkspaceFolderResolver(BaseResolver):
    """Stage: Resolves workspace-scoped implicit queries (e.g. my folder, my project)."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage: Workspace Folder Resolver")
        
        query_clean = intent.entity.lower().strip()
        
        workspace_terms = {"my folder", "my project", "my ultron folder", "ultron folder", "ultron project"}
        
        is_match = False
        for term in workspace_terms:
            if query_clean == term or query_clean in term or term in query_clean:
                is_match = True
                break
                
        if intent.intent == "OPEN_APPLICATION" and is_match:
            workspace_path = "c:\\Users\\craft\\Desktop\\Ultron"
            dur_ms = (time.perf_counter() - start_time) * 1000
            entity = UltronEntity(
                name="Ultron Project Folder",
                category="folder",
                executable=workspace_path,
                aliases={query_clean: 1.0}
            )
            self.logger.info(f"STATUS: SUCCESS | Resolved workspace folder to: {workspace_path}")
            return {
                "success": True,
                "action": "execute",
                "entity": entity,
                "spoken_response": "Opening your project folder.",
                "source": "workspace_folder_resolver",
                "confidence": 1.0,
                "latency_ms": dur_ms
            }
            
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"Workspace Folder Resolver Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class SystemActionResolver(BaseResolver):
    """Stage: Resolves system actions (e.g. shutdown, restart, sleep, lock)."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage: System Action Resolver")
        
        query_clean = intent.normalized_text.lower().strip()
        
        system_actions = {
            "shutdown pc": ("Shutdown PC", "shutdown /s /t 0"),
            "shutdown": ("Shutdown PC", "shutdown /s /t 0"),
            "power off": ("Shutdown PC", "shutdown /s /t 0"),
            "poweroff": ("Shutdown PC", "shutdown /s /t 0"),
            "restart pc": ("Restart PC", "shutdown /r /t 0"),
            "restart": ("Restart PC", "shutdown /r /t 0"),
            "reboot": ("Restart PC", "shutdown /r /t 0"),
            "sleep pc": ("Sleep PC", "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"),
            "sleep": ("Sleep PC", "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"),
            "lock pc": ("Lock PC", "rundll32.exe user32.dll,LockWorkStation"),
            "lock": ("Lock PC", "rundll32.exe user32.dll,LockWorkStation")
        }
        
        matched_action = None
        matched_cmd = None
        for term, (action_name, cmd) in system_actions.items():
            if query_clean == term or query_clean in term or term in query_clean:
                matched_action = action_name
                matched_cmd = cmd
                break
                
        if (intent.intent == "SYSTEM_ACTION" or matched_action) and matched_cmd:
            dur_ms = (time.perf_counter() - start_time) * 1000
            entity = UltronEntity(
                name=matched_action,
                category="system",
                executable=matched_cmd,
                aliases={query_clean: 1.0}
            )
            self.logger.info(f"STATUS: SUCCESS | Resolved System Action {matched_action} to: {matched_cmd}")
            return {
                "success": True,
                "action": "execute",
                "entity": entity,
                "spoken_response": f"Performing {matched_action.lower()}.",
                "source": "system_action_resolver",
                "confidence": 1.0,
                "latency_ms": dur_ms
            }
            
        dur_ms = (time.perf_counter() - start_time) * 1000
        self.logger.info(f"System Action Resolver Latency: {dur_ms:.2f}ms | STATUS: FAILED")
        return super().resolve(intent, context)


class FailureResolver(BaseResolver):
    """Stage 11: Final Failure Sink."""
    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        self.logger.info("Resolver Stage 11: Failure Sink")
        entity_name = intent.entity
        self.logger.info(f"STATUS: COMPLETE FAILURE | Could not resolve '{entity_name}'")
        dur_ms = (time.perf_counter() - start_time) * 1000
        
        return {
            "success": False,
            "action": "fail",
            "spoken_response": f"I couldn't identify the requested application, folder, or setting: {entity_name}.",
            "source": "failure_sink",
            "confidence": 0.0,
            "latency_ms": dur_ms
        }


# Backwards compatibility class bindings (Task 13 / Section 14)
class AliasResolver(FuzzyAliasResolver):
    def __init__(self, matcher: BaseMatcher, cutoff: float = None):
        super().__init__(matcher, cutoff)

    def resolve(self, intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
        res = super().resolve(intent, context)
        if "source" in res:
            if res["source"] == "fuzzy_alias_match":
                res["source"] = "alias_match"
            elif res["source"] == "fuzzy_alias_confirm":
                res["source"] = "alias_match_confirm"
        return res

class ApplicationResolver(DynamicSearchResolver):
    def __init__(self, indexer_or_matcher: Any):
        if indexer_or_matcher is not None and (hasattr(indexer_or_matcher, "ratio") or not hasattr(indexer_or_matcher, "dynamic_search")):
            # Fallback when test suite passes matcher instead of indexer
            super().__init__(None)
        else:
            super().__init__(indexer_or_matcher)
