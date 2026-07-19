"""
ULTRON Cognitive OS — Pre-Intent Spell Correction Engine.
"""

import difflib
import re
from typing import List, Optional, Set
from ultron.core.cognitive_os.entity_graph import EntityKnowledgeGraph

class SpellCorrector:
    """Corrects common typos in command verbs and application names before intent parsing."""
    
    def __init__(self, entity_graph: Optional[EntityKnowledgeGraph] = None):
        self.graph = entity_graph
        self.vocabulary = {
            # Verbs
            "open", "play", "search", "google", "youtube", "remember", "shutdown", "restart", "sleep", "lock",
            "launch", "start", "run", "execute", "can", "you", "please",
            # Nouns / System Apps / Folders
            "chrome", "edge", "firefox", "brave", "discord", "steam", "nvidia", "geforce", "vscode", "photoshop", 
            "powerpoint", "excel", "word", "spiderman", "tlauncher", "recycle", "bin", "downloads", "desktop", 
            "documents", "recent", "bluetooth", "startup", "calculator", "notepad", "control", "panel", "folder",
            "my", "project", "pc"
        }

    def _get_dynamic_vocabulary(self) -> Set[str]:
        vocab = set(self.vocabulary)
        if self.graph:
            for entity in self.graph.list_entities():
                # Add names and aliases
                vocab.add(entity.name.lower())
                for alias in entity.aliases.keys():
                    vocab.update(alias.split())
        return vocab

    def correct(self, text: str) -> str:
        """Corrects typos in the raw input text and returns the corrected string."""
        if not text:
            return ""
            
        clean_text = text.lower().strip()
        words = re.split(r"(\s+)", clean_text)  # Keep whitespace delimiters for reconstructing
        
        vocab = self._get_dynamic_vocabulary()
        corrected_words = []
        
        for w in words:
            if not w.strip():
                corrected_words.append(w)
                continue
                
            # If word is in vocab, keep it
            if w in vocab:
                corrected_words.append(w)
                continue
                
            # Try to find a close match in the vocabulary
            matches = difflib.get_close_matches(w, vocab, n=1, cutoff=0.75)
            if matches:
                match = matches[0]
                # Length constraint: prevent matching completely different words (e.g. launch -> tlauncher)
                if abs(len(w) - len(match)) <= 2:
                    corrected_words.append(match)
                else:
                    corrected_words.append(w)
            else:
                corrected_words.append(w)
                
        return "".join(corrected_words)
