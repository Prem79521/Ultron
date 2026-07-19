"""
ULTRON MCP Server — Main entry point for Model Context Protocol.
Can be run standalone: python mcp/server.py
Or as part of the ULTRON Cognitive OS service loop.
"""

import os
import sys

# Adjust sys.path immediately to prevent local 'mcp' folder from masking the installed 'mcp' library
mcp_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(mcp_dir)
if mcp_dir not in sys.path:
    sys.path.insert(0, mcp_dir)
sys.path = [p for p in sys.path if p != root_dir]

# Remove the local 'mcp' module from sys.modules to force loading the real installed 'mcp' library
if "mcp" in sys.modules:
    mcp_mod = sys.modules["mcp"]
    mcp_file = getattr(mcp_mod, "__file__", "")
    if mcp_file and (mcp_file.startswith(root_dir) or "site-packages" not in mcp_file):
        del sys.modules["mcp"]

from mcp.server.fastmcp import FastMCP
import importlib
import pkgutil
import logging

# Configure logging
logger = logging.getLogger("ultron-agent")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('[MCP] %(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Create the MCP server instance
mcp = FastMCP(
    name="ULTRON-Cognitive-OS",
    instructions=(
        "You are ULTRON, a cognitive intelligence platform and professional engineering partner. "
        "Expose tools and resources for inspectability, debugging, and controlling the runtime state. "
        "Maintain a calm, confident, and direct demeanor."
    ),
)

def register_all_modules(mcp_instance):
    """Dynamically imports and registers all tool/resource modules in the local package."""
    # Ensure local mcp directory is on sys.path, and remove root to avoid mcp package name collision
    mcp_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(mcp_dir)
    
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)
    sys.path = [p for p in sys.path if p != root_dir]
    
    logger.info("Registering MCP modules...")
    
    # Register tools
    try:
        import tools
        for _, module_name, _ in pkgutil.iter_modules(tools.__path__):
            try:
                module = importlib.import_module(f"tools.{module_name}")
                if hasattr(module, "register"):
                    module.register(mcp_instance)
                    logger.info(f"Successfully registered tool module: {module_name}")
            except Exception as exc:
                logger.error(f"Failed to import/register tool module {module_name}: {exc}", exc_info=True)
    except Exception as exc:
        logger.error(f"Error loading tools package: {exc}")

    # Register resources
    try:
        import resources
        for _, module_name, _ in pkgutil.iter_modules(resources.__path__):
            try:
                module = importlib.import_module(f"resources.{module_name}")
                if hasattr(module, "register"):
                    module.register(mcp_instance)
                    logger.info(f"Successfully registered resource module: {module_name}")
            except Exception as exc:
                logger.error(f"Failed to import/register resource module {module_name}: {exc}", exc_info=True)
    except Exception as exc:
        logger.error(f"Error loading resources package: {exc}")

# Register everything to our global instance for standalone run
register_all_modules(mcp)

def main():
    """CLI Entry point for running the MCP server standalone."""
    port = int(os.environ.get("ULTRON_MCP_PORT", 8000))
    logger.info(f"Starting standalone ULTRON MCP Server on port {port} using SSE via Uvicorn...")
    import uvicorn
    # Get the Starlette app from FastMCP via sse_app()
    app = mcp.sse_app()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    main()
