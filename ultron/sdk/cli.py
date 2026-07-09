"""
ULTRON Developer CLI — Generates extension templates and boilerplate packages.
"""

import os
import sys
import json

def create_plugin_template(name: str, description: str, category: str = "skills"):
    """Scaffolds a new plugin package structure including manifest and plugin source."""
    plugin_dir = os.path.abspath(os.path.join(os.getcwd(), "plugins", category, name))
    
    if os.path.exists(plugin_dir):
        print(f"Error: Plugin directory already exists at: {plugin_dir}")
        return

    try:
        os.makedirs(plugin_dir, exist_ok=True)
        
        # 1. Scaffolding manifest.json
        manifest = {
            "name": name,
            "version": "1.0.0",
            "author": "Developer",
            "description": description,
            "minimum_ultron_version": "1.0.0",
            "dependencies": [],
            "permissions": [],
            "entry_point": "plugin.py"
        }
        with open(os.path.join(plugin_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4)

        # 2. Scaffolding plugin.py
        plugin_code = f'''"""
Boilerplate source for ULTRON plugin: {name}
"""

def on_load():
    """Triggered dynamically when imported by the ULTRON OS loader."""
    print("Plugin loaded: {name}")

def on_enable():
    """Triggered when system dependencies are verified and service is activated."""
    print("Plugin enabled: {name}")

def on_disable():
    """Triggered prior to unregistering active skills."""
    print("Plugin disabled: {name}")

def on_unload():
    """Triggered on hot reload or clean teardown."""
    print("Plugin unloaded: {name}")

def register_plugin(registry):
    """Registers modular Cognitive Skills or wrappers into the OS registry."""
    pass
'''
        with open(os.path.join(plugin_dir, "plugin.py"), "w", encoding="utf-8") as f:
            f.write(plugin_code)
            
        print(f"Successfully created plugin template: {name}")
        print(f"Scaffold path: {plugin_dir}")
    except Exception as e:
        print(f"Failed to generate plugin scaffold: {e}")

def main():
    if len(sys.argv) < 4 or sys.argv[1] != "create_plugin":
        print("Usage: python -m ultron.sdk.cli create_plugin <Name> <Description> [Category]")
        print("Categories: skills (default), voice, vision, camera, llm, automation")
        sys.exit(1)
        
    name = sys.argv[2]
    desc = sys.argv[3]
    cat = sys.argv[4] if len(sys.argv) > 4 else "skills"
    
    create_plugin_template(name, desc, cat)

if __name__ == "__main__":
    main()
