"""
Friday MCP Server — Entry Point
Run with: python server.py
"""

from mcp.server.fastmcp import FastMCP
from ultron.tools import register_all_tools
from ultron.prompts import register_all_prompts
from ultron.resources import register_all_resources
from ultron.config import config

# Create the MCP server instance
mcp = FastMCP(
    name=config.SERVER_NAME,
    instructions=(
        "You are ULTRON, a cognitive agent platform and professional engineering partner for developers. "
        "Provide direct, logical, and technically accurate responses. "
        "Maintain a calm, confident, and professional demeanor with dry humor."
    ),
)

# Register tools, prompts, and resources
register_all_tools(mcp)
register_all_prompts(mcp)
register_all_resources(mcp)


def main():
    mcp.run(transport='sse')

if __name__ == "__main__":
    main()