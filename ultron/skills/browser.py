"""
ULTRON Browser Skill — Launches URLs, searches pages, and opens localhost projects.
"""

import webbrowser
import urllib.parse
from typing import Dict, Any
from ultron.skills.registry import CognitiveSkill

class BrowserSkill(CognitiveSkill):
    NAME = "Browser"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action", "open_url")
        url = params.get("url")

        if action == "open_url":
            if not url:
                return {"success": False, "error": "Parameter 'url' is required"}
            self.core.logger.info("BROWSER", f"Launching URL in default browser: {url}")
            try:
                webbrowser.open(url)
                return {"success": True, "message": f"URL opened: {url}"}
            except Exception as e:
                self.core.logger.error("BROWSER", f"Failed to open URL {url}: {e}")
                return {"success": False, "error": str(e)}

        elif action == "search":
            query = params.get("query")
            if not query:
                return {"success": False, "error": "Parameter 'query' is required"}
            
            # Format Google Search URL
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            self.core.logger.info("BROWSER", f"Searching web for: {query}")
            try:
                webbrowser.open(search_url)
                return {"success": True, "message": f"Search launched for query: {query}"}
            except Exception as e:
                self.core.logger.error("BROWSER", f"Search failed: {e}")
                return {"success": False, "error": str(e)}

        return {"success": False, "error": f"Unknown Browser action: {action}"}
