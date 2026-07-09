"""
Data resources — expose static content or dynamic data via MCP resources.
"""


def register(mcp):

    @mcp.resource("ultron://info")
    def server_info() -> str:
        """Returns basic info about this MCP server."""
        return (
            "Ultron MCP Server\n"
            "A modular cognitive system for developers.\n"
            "Built with FastMCP."
        )

