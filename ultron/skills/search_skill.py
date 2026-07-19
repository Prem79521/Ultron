"""
ULTRON Search Skill — Performs web searches on Google and YouTube.
"""

import webbrowser
import urllib.parse
import time
from typing import Dict, Any
from ultron.skills.registry import CognitiveSkill

class SearchSkill(CognitiveSkill):
    NAME = "SearchSkill"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        action = params.get("action", "")
        query = params.get("query", "").strip()
        
        if not query:
            elapsed = (time.time() - start_time) * 1000
            return {
                "success": False,
                "spoken_response": "I didn't hear a search query. Please try again.",
                "visual_response": "Empty search query.",
                "execution_time": elapsed,
                "errors": ["Empty query"]
            }
            
        encoded_query = urllib.parse.quote(query)
        
        if action == "google_search":
            url = f"https://www.google.com/search?q={encoded_query}"
            display_dest = "Google"
            success_msg = f"Searching Google for {query}."
        elif action == "youtube_search":
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            display_dest = "YouTube"
            success_msg = f"Searching YouTube for {query}."
        else:
            elapsed = (time.time() - start_time) * 1000
            return {
                "success": False,
                "spoken_response": f"Unknown search type: {action}.",
                "visual_response": f"Unsupported search type: {action}",
                "execution_time": elapsed,
                "errors": [f"Unsupported search action: {action}"]
            }
            
        self.core.logger.info("SearchSkill", f"Opening {display_dest} search: {url}")
        
        try:
            webbrowser.open(url)
            elapsed = (time.time() - start_time) * 1000
            return {
                "success": True,
                "spoken_response": success_msg,
                "visual_response": f"Searching {display_dest} for '{query}'",
                "execution_time": elapsed,
                "errors": []
            }
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self.core.logger.error("SearchSkill", f"Search failed: {e}")
            return {
                "success": False,
                "spoken_response": "Unable to perform web search.",
                "visual_response": f"Error: {e}",
                "execution_time": elapsed,
                "errors": [str(e)]
            }
