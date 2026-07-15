"""
ULTRON Cognitive OS — MCP Server Launcher
Delegates execution to the modular server implementation in the mcp/ directory,
using robust path normalization to prevent naming collisions with the 'mcp' package.
"""

import os
import sys
import pathlib
import importlib.util

def main():
    # Resolve directories using pathlib for Windows case-insensitivity and normalization
    root_dir = pathlib.Path(__file__).parent.resolve()
    mcp_dir = (root_dir / "mcp").resolve()
    
    # Filter sys.path to remove root_dir and empty strings, avoiding collisions
    cleaned_path = []
    for p in sys.path:
        if not p:
            continue
        try:
            p_resolved = pathlib.Path(p).resolve()
            if p_resolved == root_dir:
                continue
        except Exception:
            pass
        cleaned_path.append(p)
        
    # Insert the local mcp/ directory at the front
    cleaned_path.insert(0, str(mcp_dir))
    sys.path = cleaned_path
    
    # Load the module dynamically
    mcp_server_path = os.path.join(str(mcp_dir), "server.py")
    spec = importlib.util.spec_from_file_location("ultron_mcp_server", mcp_server_path)
    if spec and spec.loader:
        mcp_server_module = importlib.util.module_from_spec(spec)
        sys.modules["ultron_mcp_server"] = mcp_server_module
        spec.loader.exec_module(mcp_server_module)
        mcp_server_module.main()
    else:
        print(f"Error: Could not load MCP server from {mcp_server_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()