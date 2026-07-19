"""
ULTRON Website Skill — Opens target URLs in default system browser.
"""

import webbrowser
import time
from typing import Dict, Any
from ultron.skills.registry import CognitiveSkill

class WebsiteSkill(CognitiveSkill):
    NAME = "WebsiteSkill"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        website_name = params.get("website", "").lower().strip()
        url = params.get("url") or params.get("website") or ""
        url = url.strip()
        
        if not url:
            elapsed = (time.time() - start_time) * 1000
            return {
                "success": False,
                "spoken_response": "No website URL or name was provided.",
                "visual_response": "No URL provided.",
                "execution_time": elapsed,
                "errors": ["No target URL provided"]
            }
            
        display_name = params.get("name") or website_name.title()
        
        # If url is not an absolute link, try to map it
        if not url.lower().startswith(("http://", "https://")):
            websites = {
                "youtube": ("https://youtube.com", "YouTube"),
                "chatgpt": ("https://chat.openai.com", "ChatGPT"),
                "gmail": ("https://gmail.com", "Gmail"),
                "github": ("https://github.com", "GitHub"),
                "google": ("https://google.com", "Google"),
                "stackoverflow": ("https://stackoverflow.com", "StackOverflow")
            }
            if url.lower() in websites:
                url, display_name = websites[url.lower()]
            else:
                display_name = url.title()
                url = f"https://{url}" if "." in url else f"https://{url}.com"
        
        self.core.logger.info("WebsiteSkill", f"Opening website {display_name} via URL: {url}")
        
        try:
            success = webbrowser.open(url)
            elapsed = (time.time() - start_time) * 1000
            
            if success:
                success_msg = f"Opening {display_name}."
                return {
                    "success": True,
                    "spoken_response": success_msg,
                    "visual_response": f"Navigating to {url}",
                    "execution_time": elapsed,
                    "errors": []
                }
            else:
                return {
                    "success": False,
                    "spoken_response": "Unable to open website.",
                    "visual_response": "Browser launch returned failure.",
                    "execution_time": elapsed,
                    "errors": ["webbrowser.open returned False"]
                }
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self.core.logger.error("WebsiteSkill", f"Failed to open website: {e}")
            return {
                "success": False,
                "spoken_response": "Unable to open website.",
                "visual_response": f"Error: {e}",
                "execution_time": elapsed,
                "errors": [str(e)]
            }

