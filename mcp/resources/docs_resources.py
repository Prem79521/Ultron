"""
MCP Documentation Resources — Exposes documentation files as resources.
"""

import os
import pathlib

WORKSPACE_ROOT = pathlib.Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))).resolve()

def register(mcp):

    @mcp.resource("docs://list")
    def list_all_docs() -> str:
        """Returns the list of all documentation files available in the workspace."""
        docs_list = []
        for dir_name in ["docs", "documentation"]:
            dir_path = WORKSPACE_ROOT / dir_name
            if dir_path.is_dir():
                for file_path in dir_path.glob("*.md"):
                    title = file_path.stem
                    try:
                        # Extract first header
                        content = file_path.read_text(encoding="utf-8")
                        for line in content.splitlines():
                            if line.startswith("# "):
                                title = line.replace("# ", "").strip()
                                break
                    except Exception:
                        pass
                    docs_list.append(f"- **{file_path.name}** ({title}) - URI: `docs://{file_path.name}`")
        
        return "### ULTRON Documentation Registry\n\n" + "\n".join(sorted(docs_list))

    @mcp.resource("docs://{filename}")
    def get_doc_content(filename: str) -> str:
        """Exposes the content of a specific documentation markdown file."""
        for dir_name in ["docs", "documentation"]:
            file_path = WORKSPACE_ROOT / dir_name / filename
            if file_path.is_file():
                if file_path.resolve().is_relative_to(WORKSPACE_ROOT):
                    try:
                        return file_path.read_text(encoding="utf-8")
                    except Exception as exc:
                        return f"Error reading document: {exc}"
        return f"Document '{filename}' not found."
