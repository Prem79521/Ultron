from typing import Dict, Any, List
from ultron.skills.registry import CognitiveSkill
from ultron.planner import Task, ExecutionPlan

class CommandDispatcher(CognitiveSkill):
    NAME = "CommandDispatcher"

    def __init__(self, core_system, memory_manager):
        super().__init__(core_system, memory_manager)
        self._initialized = False

    def _init_cognitive_pipeline(self):
        from ultron.core.cognitive_os.base_matcher import DifflibMatcher
        from ultron.core.cognitive_os.entity_graph import EntityKnowledgeGraph
        from ultron.core.cognitive_os.learning_memory import LearningMemory
        from ultron.core.cognitive_os.app_indexer import WindowsAppIndexer
        from ultron.core.cognitive_os.intent_engine import IntentEngine
        from ultron.core.cognitive_os.spell_corrector import SpellCorrector
        from ultron.core.cognitive_os.resolver_chain import (
            ExactAliasResolver, FuzzyAliasResolver, LearningMemoryResolver,
            IndexedApplicationsResolver, DynamicSearchResolver, BrowserResolver,
            ShellNamespaceResolver, WorkspaceFolderResolver, SystemActionResolver,
            WebsiteResolver, FolderResolver, SettingsResolver, FileResolver,
            WebSearchResolver, FailureResolver
        )
        
        self._entity_graph = EntityKnowledgeGraph()
        self._matcher = DifflibMatcher()
        self._learning_memory = LearningMemory(self.memory)
        self._indexer = WindowsAppIndexer(self.memory)
        self._intent_engine = IntentEngine()
        self._spell_corrector = SpellCorrector(self._entity_graph)
        
        # Setup resolver chain matching Layered Architecture (L1-L8)
        self._resolver_chain = LearningMemoryResolver(self._learning_memory)
        r_exact = ExactAliasResolver()
        r_fuzzy = FuzzyAliasResolver(self._matcher)
        r_indexed = IndexedApplicationsResolver()
        r_browser = BrowserResolver(self._indexer)
        r_search_win = DynamicSearchResolver(self._indexer)
        r_shell = ShellNamespaceResolver()
        r_workspace = WorkspaceFolderResolver()
        r_system = SystemActionResolver()
        r_web = WebsiteResolver()
        r_folder = FolderResolver()
        r_settings = SettingsResolver()
        r_file = FileResolver()
        r_search = WebSearchResolver()
        r_fail = FailureResolver()
        
        (self._resolver_chain
         .set_next(r_exact)
         .set_next(r_fuzzy)
         .set_next(r_indexed)
         .set_next(r_browser)
         .set_next(r_search_win)
         .set_next(r_shell)
         .set_next(r_workspace)
         .set_next(r_system)
         .set_next(r_web)
         .set_next(r_folder)
         .set_next(r_settings)
         .set_next(r_file)
         .set_next(r_search)
         .set_next(r_fail))
         
        # Non-blocking background loading
        self._indexer.start_background_indexing(self._entity_graph)
        
        # Auto-register dependent skills in the registry if not already registered (helps with isolated test environments)
        skills_reg = self.core.get_module("skills_registry")
        if not skills_reg:
            from ultron.skills.registry import SkillRegistry
            skills_reg = SkillRegistry(self.core, self.memory)
            self.core.register_module("skills_registry", skills_reg)
            skills_reg._skills["commanddispatcher"] = self

        if not skills_reg.get_skill("ApplicationSkill"):
            from ultron.skills.application_skill import ApplicationSkill
            skills_reg.register_skill("ApplicationSkill", ApplicationSkill)
        if not skills_reg.get_skill("BrowserSkill"):
            from ultron.skills.browser_skill import BrowserSkill
            skills_reg.register_skill("BrowserSkill", BrowserSkill)
        if not skills_reg.get_skill("WindowsSkill"):
            from ultron.skills.windows_skill import WindowsSkill
            skills_reg.register_skill("WindowsSkill", WindowsSkill)
        if not skills_reg.get_skill("WebsiteSkill"):
            from ultron.skills.website_skill import WebsiteSkill
            skills_reg.register_skill("WebsiteSkill", WebsiteSkill)
        if not skills_reg.get_skill("SearchSkill"):
            from ultron.skills.search_skill import SearchSkill
            skills_reg.register_skill("SearchSkill", SearchSkill)
        
        self._initialized = True

    def _execute_entity(self, entity, action, command_text, start_total) -> Dict[str, Any]:
        import time
        category = entity.category
        
        # Cleaned routing map (delegates strictly to skills)
        skill_map = {
            "browser": ("BrowserSkill", "execute", {"browser": entity.name.lower(), "path": entity.executable}),
            "application": ("ApplicationSkill", "execute", {"path": entity.executable, "name": entity.name, "command": command_text}),
            "game": ("ApplicationSkill", "execute", {"path": entity.executable, "name": entity.name, "command": command_text}),
            "folder": ("WindowsSkill", "open_folder", {"folder": entity.name.lower(), "path": entity.executable}),
            "settings": ("WindowsSkill", "open_settings", {"setting": entity.name.lower(), "path": entity.executable}),
            "website": ("WebsiteSkill", "open_website", {"website": entity.name.lower(), "url": entity.website}),
            "document": ("ApplicationSkill", "execute", {"path": entity.executable, "name": entity.name, "command": command_text}),
            "system": ("ApplicationSkill", "execute", {"path": entity.executable, "name": entity.name, "command": command_text}),
            "search": ("SearchSkill", entity.metadata.get("action"), {"query": entity.metadata.get("query")})
        }
        
        skill_name, cmd_type, cmd_args = skill_map.get(category, (None, None, None))
        if skill_name:
            skills_reg = self.core.get_module("skills_registry")
            skill_inst = skills_reg.get_skill(skill_name) if skills_reg else None
            if skill_inst:
                try:
                    res = skill_inst.execute({**cmd_args, "action": cmd_type})
                except Exception as e:
                    res = {
                        "success": False,
                        "spoken_response": f"Failed to execute skill: {e}",
                        "visual_response": f"Error: {e}",
                        "execution_time": 0.0,
                        "errors": [str(e)]
                    }
            else:
                res = {
                    "success": False,
                    "spoken_response": f"Skill {skill_name} not found.",
                    "visual_response": f"Skill {skill_name} not found.",
                    "execution_time": 0.0,
                    "errors": [f"Skill {skill_name} not found"]
                }
        else:
            res = {
                "success": False,
                "spoken_response": f"Unsupported category {category}.",
                "visual_response": f"Unsupported category {category}.",
                "execution_time": 0.0,
                "errors": [f"Unsupported category {category}"]
            }
                
        elapsed_ms = (time.time() - start_total) * 1000
        res["execution_time"] = elapsed_ms
        
        status_str = "Success" if res.get("success") else "Failure"
        self.core.logger.info("Dispatcher", f"Execution Finished: {entity.name} | Elapsed Time: {elapsed_ms:.1f}ms | Status: {status_str}")
        
        # Update UME conversation log
        try:
            self.memory.create_record(
                memory_type="conversation",
                title=f"Command: {command_text[:20]}",
                content=f"Query: {command_text}\nResponse: {res.get('spoken_response')}",
                tags=["command", "os"]
            )
        except Exception as e:
            self.core.logger.error("Memory", f"Failed to save command log: {e}")
            
        dialogue_text = res.get("spoken_response", "")
        self.core.events.publish("PipelineStepCompleted", {"response": dialogue_text})
        
        return {
            "success": res.get("success", False),
            "response": dialogue_text,
            "results": [{
                "task_id": category,
                "description": f"Execute {entity.name}",
                "success": res.get("success", False),
                "output": res
            }]
        }


    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Runs a command through the Cognitive Core pipeline stages, emitting logs and status events."""
        import time
        command_text = params.get("command", "").strip()
        start_total = time.time()

        if not self._initialized:
            self._init_cognitive_pipeline()

        # Refresh applications cache rebuild
        if command_text.lower().strip() == "refresh applications":
            self.core.logger.info("Dispatcher", "Refreshing applications index...")
            self._indexer.rebuild_cache(self._entity_graph, force=True)
            dialogue_text = "Refreshing application index cache in the background."
            self.core.events.publish("PipelineStepCompleted", {"response": dialogue_text})
            return {
                "success": True,
                "response": dialogue_text,
                "results": [{"task_id": "refresh_applications", "success": True, "output": {}}]
            }

        # 1. Check for active session-scoped confirmation state
        from ultron.core.voice_session_manager import get_voice_session_manager
        session_mgr = get_voice_session_manager()
        
        if session_mgr and session_mgr.pending_confirmation:
            pending = session_mgr.pending_confirmation
            clean_cmd = command_text.lower().strip()
            
            # Check choices confirmation type
            if pending.get("type") == "choices":
                choice_idx = -1
                if "1" in clean_cmd or "first" in clean_cmd or "one" in clean_cmd:
                    choice_idx = 0
                elif "2" in clean_cmd or "second" in clean_cmd or "two" in clean_cmd:
                    choice_idx = 1
                elif "3" in clean_cmd or "third" in clean_cmd or "three" in clean_cmd:
                    choice_idx = 2
                elif "4" in clean_cmd or "fourth" in clean_cmd or "four" in clean_cmd:
                    choice_idx = 3
                elif "5" in clean_cmd or "fifth" in clean_cmd or "five" in clean_cmd:
                    choice_idx = 4
                    
                if any(w in clean_cmd for w in ["no", "nope", "cancel", "stop", "incorrect"]):
                    session_mgr.pending_confirmation = None
                    dialogue_text = "Okay, cancelled. What would you like to do instead?"
                    self.core.events.publish("PipelineStepCompleted", {"response": dialogue_text})
                    return {
                        "success": True,
                        "response": dialogue_text,
                        "results": [{"task_id": "vault_cancelled", "success": True, "output": {}}]
                    }
                elif 0 <= choice_idx < len(pending["choices"]):
                    selected = pending["choices"][choice_idx]
                    action = pending["action"]
                    session_mgr.pending_confirmation = None
                    
                    if action == "execute":
                        # Learn the choice mapping for future executions (Task 3 / Section 14)
                        phrase = pending["phrase"]
                        self._learning_memory.learn(phrase, selected.name, pending["confidence"], pending["source"])
                        return self._execute_entity(selected, action, command_text, start_total)
                        
                    selected_path = selected
                    from ultron.core.service_manager import service_manager
                    vault_service = service_manager.get_service("HiddenItemsService")
                    if vault_service:
                        if action == "hide":
                            try:
                                name = vault_service.hide_item(selected_path)
                                dialogue_text = f"{name} has been hidden."
                                success = True
                            except Exception as e:
                                dialogue_text = f"Failed to hide: {e}"
                                success = False
                        elif action == "restore":
                            try:
                                name = vault_service.unhide_item(selected_path)
                                dialogue_text = f"{name} is visible again."
                                success = True
                            except Exception as e:
                                dialogue_text = f"Failed to restore: {e}"
                                success = False
                        elif action == "open":
                            try:
                                vault_service.open_hidden_item(pending["name"])
                                dialogue_text = f"Opening hidden item."
                                success = True
                            except Exception as e:
                                dialogue_text = f"Failed to open: {e}"
                                success = False
                    else:
                        dialogue_text = "Hidden Items Vault service is not available."
                        success = False
                        
                    self.core.events.publish("PipelineStepCompleted", {"response": dialogue_text})
                    return {
                        "success": success,
                        "response": dialogue_text,
                        "results": [{"task_id": f"vault_{action}", "success": success, "output": {"path": selected_path}}]
                    }
                else:
                    response = f"Please say 1 to {len(pending['choices'])} to choose, or say cancel."
                    self.core.events.publish("PipelineStepCompleted", {"response": response})
                    return {
                        "success": True,
                        "response": response,
                        "results": []
                    }
            
            # Affirmative confirm
            elif any(w in clean_cmd for w in ["yes", "sure", "yeah", "correct", "do it", "okay"]):
                entity = pending["entity"]
                action = pending["action"]
                source = pending["source"]
                confidence = pending["confidence"]
                phrase = pending["phrase"]
                
                # Persist to learning memory upon positive confirmation
                self._learning_memory.learn(phrase, entity.name, confidence, source)
                
                # Clear session state
                session_mgr.pending_confirmation = None
                return self._execute_entity(entity, action, command_text, start_total)
                
            # Negative cancel
            elif any(w in clean_cmd for w in ["no", "nope", "cancel", "stop", "incorrect"]):
                session_mgr.pending_confirmation = None
                dialogue_text = "Okay, cancelled. What would you like to do instead?"
                self.core.events.publish("PipelineStepCompleted", {"response": dialogue_text})
                return {
                    "success": True,
                    "response": dialogue_text,
                    "results": [{"task_id": "confirmation_cancelled", "success": True, "output": {}}]
                }
            else:
                # Discard and process as a fresh command
                session_mgr.pending_confirmation = None

        # 2. Pre-Intent Spell Correction & Intent Engine Parsing (Task 1 / Section 14)
        start_stage = time.time()
        corrected_command = self._spell_corrector.correct(command_text)
        if corrected_command != command_text.lower().strip():
            self.core.logger.info("SpellCorrector", f"Corrected command typo: '{command_text}' -> '{corrected_command}'")
            
        intent_result = self._intent_engine.classify(corrected_command)
        intent_dur = (time.time() - start_stage) * 1000
        if intent_dur > 100:
            self.core.logger.warning("Performance Log", f"PERFORMANCE WARNING: Intent Engine Parse took {intent_dur:.1f}ms")

        # Check for Hidden Items Vault Intents
        if intent_result.intent in ["HIDE_ITEM", "RESTORE_ITEM", "LIST_HIDDEN", "OPEN_HIDDEN"]:
            return self._execute_hidden_items_intent(intent_result, corrected_command, start_total)

        # 3. Resolver Chain Execution
        start_stage = time.time()
        context = {
            "entity_graph": self._entity_graph,
            "matcher": self._matcher,
            "memory": self.memory,
            "learning_memory": self._learning_memory,
            "indexer": self._indexer
        }
        res = self._resolver_chain.resolve(intent_result, context)
        resolver_dur = (time.time() - start_stage) * 1000
        if resolver_dur > 100:
            self.core.logger.warning("Performance Log", f"PERFORMANCE WARNING: Resolver Chain took {resolver_dur:.1f}ms")
        
        elapsed_ms = (time.time() - start_total) * 1000
        
        # Forensic Log Stage
        self.core.logger.info(
            "Forensic Log",
            f"\n=== COGNITIVE RESOLUTION FORENSIC LOG ===\n"
            f"Raw Input: '{command_text}'\n"
            f"Normalized Input: '{intent_result.normalized_text}'\n"
            f"Intent: {intent_result.intent}\n"
            f"Extracted Entity: '{intent_result.entity}'\n"
            f"Selected Candidate: {res['entity'].name if 'entity' in res else 'None'}\n"
            f"Resolver Used: {res.get('source', 'None')}\n"
            f"Confidence Score: {res.get('confidence', 0.0):.2f}\n"
            f"Execution Time: {elapsed_ms:.1f}ms\n"
            f"Final Action: {res.get('action', 'fail').upper()}\n"
            f"=========================================="
        )

        # 4. Resolve Action Path (One and Only One path - Task 1 / Section 14)
        action = res.get("action", "fail")
        if action == "execute":
            return self._execute_entity(res["entity"], action, command_text, start_total)
            
        elif action == "confirm":
            # Save to voice session manager runtime scope
            if session_mgr:
                session_mgr.pending_confirmation = {
                    "entity": res["entity"],
                    "action": "execute",
                    "phrase": command_text,
                    "confidence": res["confidence"],
                    "source": res["source"],
                    "type": res.get("type", "yes_no"),
                    "choices": res.get("choices", [])
                }
            
            dialogue_text = res["spoken_response"]
            self.core.events.publish("PipelineStepCompleted", {"response": dialogue_text})
            return {
                "success": True,
                "response": dialogue_text,
                "results": [{"task_id": "confirm", "success": True, "output": res}]
            }
            
        else: # fail
            dialogue_text = res["spoken_response"]
            self.core.events.publish("PipelineStepCompleted", {"response": dialogue_text})
            return {
                "success": False,
                "response": dialogue_text,
                "results": [{"task_id": "fail", "success": False, "output": res}]
            }

    def _execute_hidden_items_intent(self, intent_result, command_text, start_total) -> Dict[str, Any]:
        from ultron.core.service_manager import service_manager
        from ultron.core.voice_session_manager import get_voice_session_manager
        
        vault_service = service_manager.get_service("HiddenItemsService")
        if not vault_service:
            response = "Hidden Items Vault service is not available."
            self.core.events.publish("PipelineStepCompleted", {"response": response})
            return {
                "success": False,
                "response": response,
                "results": [{"task_id": "vault_error", "success": False, "output": {}}]
            }
            
        intent = intent_result.intent
        entity = intent_result.entity.strip()
        raw_lower = command_text.lower().strip()
        
        session_mgr = get_voice_session_manager()
        
        if intent == "HIDE_ITEM":
            entity_clean = entity
            for suffix in [" folder", " directory"]:
                if entity_clean.lower().endswith(suffix):
                    entity_clean = entity_clean[:-len(suffix)].strip()
            for prefix in ["folder ", "directory "]:
                if entity_clean.lower().startswith(prefix):
                    entity_clean = entity_clean[len(prefix):].strip()
                    
            is_direct_path = (":" in entity_clean) or ("/" in entity_clean) or ("\\" in entity_clean)
            
            if is_direct_path:
                try:
                    name = vault_service.hide_item(entity_clean)
                    response = f"{name} has been hidden."
                    self.core.events.publish("PipelineStepCompleted", {"response": response})
                    return {
                        "success": True,
                        "response": response,
                        "results": [{"task_id": "hide_item", "success": True, "output": {"path": entity_clean}}]
                    }
                except Exception as e:
                    response = str(e)
                    self.core.events.publish("PipelineStepCompleted", {"response": response})
                    return {
                        "success": False,
                        "response": response,
                        "results": [{"task_id": "hide_item", "success": False, "output": {"error": str(e)}}]
                    }
            else:
                candidates = vault_service.find_paths_to_hide(entity_clean)
                if not candidates:
                    response = f"I couldn't find any folder or file named {entity_clean}."
                    self.core.events.publish("PipelineStepCompleted", {"response": response})
                    return {
                        "success": False,
                        "response": response,
                        "results": [{"task_id": "hide_item", "success": False, "output": {}}]
                    }
                elif len(candidates) == 1:
                    try:
                        name = vault_service.hide_item(candidates[0])
                        response = f"{name} has been hidden."
                        self.core.events.publish("PipelineStepCompleted", {"response": response})
                        return {
                            "success": True,
                            "response": response,
                            "results": [{"task_id": "hide_item", "success": True, "output": {"path": candidates[0]}}]
                        }
                    except Exception as e:
                        response = str(e)
                        self.core.events.publish("PipelineStepCompleted", {"response": response})
                        return {
                            "success": False,
                            "response": response,
                            "results": [{"task_id": "hide_item", "success": False, "output": {"error": str(e)}}]
                        }
                else:
                    num_candidates = len(candidates)
                    response = f"I found {num_candidates} items named {entity_clean}. Which one would you like to hide?\n"
                    for idx, c in enumerate(candidates[:5]):
                        response += f"{idx+1}. {c}\n"
                    if num_candidates > 5:
                        response += f"...and {num_candidates - 5} more."
                    
                    if session_mgr:
                        session_mgr.pending_confirmation = {
                            "type": "choices",
                            "action": "hide",
                            "choices": candidates,
                            "name": entity_clean
                        }
                        
                    self.core.events.publish("PipelineStepCompleted", {"response": response})
                    return {
                        "success": True,
                        "response": response,
                        "results": [{"task_id": "hide_item_choices", "success": True, "output": {"choices": candidates}}]
                    }
                    
        elif intent == "RESTORE_ITEM":
            if "everything i hid yesterday" in raw_lower or "everything hidden yesterday" in raw_lower:
                restored = vault_service.restore_by_date("yesterday")
                response = f"Restored {len(restored)} items hidden yesterday."
                self.core.events.publish("PipelineStepCompleted", {"response": response})
                return {"success": True, "response": response, "results": []}
            elif "everything i hid today" in raw_lower or "everything hidden today" in raw_lower:
                restored = vault_service.restore_by_date("today")
                response = f"Restored {len(restored)} items hidden today."
                self.core.events.publish("PipelineStepCompleted", {"response": response})
                return {"success": True, "response": response, "results": []}
            elif "everything" in raw_lower:
                restored = vault_service.restore_by_date("everything")
                response = f"Restored all {len(restored)} hidden items."
                self.core.events.publish("PipelineStepCompleted", {"response": response})
                return {"success": True, "response": response, "results": []}
                
            is_direct_path = (":" in entity) or ("/" in entity) or ("\\" in entity)
            if is_direct_path:
                item = vault_service.get_item_by_path(entity)
                if item and item["status"] == "hidden":
                    hidden_matches = [item]
                else:
                    matches = vault_service.find_item(os.path.basename(entity))
                    hidden_matches = [m for m in matches if m["status"] == "hidden"]
            else:
                matches = vault_service.find_item(entity)
                hidden_matches = [m for m in matches if m["status"] == "hidden"]
            
            if not hidden_matches:
                response = f"I couldn't find any hidden item named {entity}."
                self.core.events.publish("PipelineStepCompleted", {"response": response})
                return {"success": False, "response": response, "results": []}
            elif len(hidden_matches) == 1:
                try:
                    name = vault_service.unhide_item(hidden_matches[0]["original_path"])
                    response = f"{name} is visible again."
                    self.core.events.publish("PipelineStepCompleted", {"response": response})
                    return {"success": True, "response": response, "results": []}
                except Exception as e:
                    response = str(e)
                    self.core.events.publish("PipelineStepCompleted", {"response": response})
                    return {"success": False, "response": response, "results": []}
            else:
                response = f"I found {len(hidden_matches)} hidden items named {entity}. Which one would you like to restore?\n"
                for idx, m in enumerate(hidden_matches):
                    response += f"{idx+1}. {m['original_path']}\n"
                    
                if session_mgr:
                    session_mgr.pending_confirmation = {
                        "type": "choices",
                        "action": "restore",
                        "choices": [m["original_path"] for m in hidden_matches],
                        "name": entity
                    }
                self.core.events.publish("PipelineStepCompleted", {"response": response})
                return {"success": True, "response": response, "results": []}
                
        elif intent == "OPEN_HIDDEN":
            is_direct_path = (":" in entity) or ("/" in entity) or ("\\" in entity)
            if is_direct_path:
                item = vault_service.get_item_by_path(entity)
                if item and item["status"] == "hidden":
                    hidden_matches = [item]
                else:
                    matches = vault_service.find_item(os.path.basename(entity))
                    hidden_matches = [m for m in matches if m["status"] == "hidden"]
            else:
                matches = vault_service.find_item(entity)
                hidden_matches = [m for m in matches if m["status"] == "hidden"]
            
            if not hidden_matches:
                response = f"I couldn't find any hidden item named {entity}."
                self.core.events.publish("PipelineStepCompleted", {"response": response})
                return {"success": False, "response": response, "results": []}
            elif len(hidden_matches) == 1:
                try:
                    vault_service.open_hidden_item(hidden_matches[0]["name"])
                    response = f"Opening hidden {hidden_matches[0]['name']}."
                    self.core.events.publish("PipelineStepCompleted", {"response": response})
                    return {"success": True, "response": response, "results": []}
                except Exception as e:
                    response = str(e)
                    self.core.events.publish("PipelineStepCompleted", {"response": response})
                    return {"success": False, "response": response, "results": []}
            else:
                response = f"I found {len(hidden_matches)} hidden items named {entity}. Which one would you like to open?\n"
                for idx, m in enumerate(hidden_matches):
                    response += f"{idx+1}. {m['original_path']}\n"
                    
                if session_mgr:
                    session_mgr.pending_confirmation = {
                        "type": "choices",
                        "action": "open",
                        "choices": [m["original_path"] for m in hidden_matches],
                        "name": entity
                    }
                self.core.events.publish("PipelineStepCompleted", {"response": response})
                return {"success": True, "response": response, "results": []}
                
        elif intent == "LIST_HIDDEN":
            items = vault_service.list_hidden_items()
            hidden_items = [item for item in items if item["status"] == "hidden"]
            
            if not hidden_items:
                response = "You have not hidden any items."
            else:
                response = "Hidden Items\n"
                for idx, item in enumerate(hidden_items):
                    response += f"{idx+1}. {item['name']}\n   {item['original_path']}\n"
                    if idx < len(hidden_items) - 1:
                        response += "\n"
                    
            self.core.events.publish("PipelineStepCompleted", {"response": response})
            return {"success": True, "response": response, "results": []}
            
        return {"success": False, "response": "Unsupported vault action.", "results": []}
