"""
MCP Filesystem Tools — Browse, read, search files and symbols securely.
"""

import os
import ast
import pathlib
import subprocess
from typing import List, Dict, Any

# Root workspace directory to prevent directory traversal
WORKSPACE_ROOT = pathlib.Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))).resolve()

def _resolve_secure_path(subpath: str) -> pathlib.Path:
    """Resolves a subpath relative to the workspace root, checking for traversal."""
    resolved = (WORKSPACE_ROOT / subpath).resolve()
    if not resolved.is_relative_to(WORKSPACE_ROOT):
        raise ValueError(f"Access denied: path '{subpath}' is outside the repository root.")
    return resolved

def register(mcp):

    @mcp.tool()
    def list_directory(path: str = ".") -> List[Dict[str, Any]]:
        """
        List files and subdirectories within the workspace.
        Path is relative to the workspace root.
        """
        try:
            target_dir = _resolve_secure_path(path)
            if not target_dir.is_dir():
                raise ValueError(f"Path '{path}' is not a directory.")
                
            entries = []
            for entry in target_dir.iterdir():
                # Skip common ignored files/folders
                if entry.name in [".git", "__pycache__", ".venv", "venv"]:
                    continue
                entries.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size_bytes": entry.stat().st_size if entry.is_file() else None,
                    "relative_path": str(entry.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
                })
            return sorted(entries, key=lambda x: (x["type"] != "directory", x["name"]))
        except Exception as exc:
            return [{"error": str(exc)}]

    @mcp.tool()
    def read_file(path: str, start_line: int = 1, end_line: int = None) -> str:
        """
        Read the contents of a file in the workspace.
        Path is relative to the workspace root. Start_line and end_line are 1-indexed (inclusive).
        """
        try:
            file_path = _resolve_secure_path(path)
            if not file_path.is_file():
                raise ValueError(f"Path '{path}' is not a file.")
                
            # Detect common binary extensions to avoid reading garbage
            binary_exts = {".png", ".jpg", ".jpeg", ".ico", ".db", ".exe", ".dll", ".pyd"}
            if file_path.suffix.lower() in binary_exts:
                return f"[Binary file: {file_path.name} ({file_path.stat().st_size} bytes)]"

            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            
            total_lines = len(lines)
            start = max(1, start_line) - 1
            end = min(total_lines, end_line) if end_line else total_lines
            
            sliced_lines = lines[start:end]
            header = f"# File: {path} (Lines {start+1}-{end} of {total_lines})\n"
            return header + "\n".join(sliced_lines)
        except Exception as exc:
            return f"Error reading file: {exc}"

    @mcp.tool()
    def grep_search(query: str, path: str = ".") -> str:
        """
        Search for a pattern/regex in text files recursively.
        Uses native 'git grep' for fast search excluding gitignored files.
        Path is relative to the workspace root.
        """
        try:
            # Resolve target directory to start search
            target_dir = _resolve_secure_path(path)
            
            # Run git grep inside the resolved path
            cmd = ["git", "grep", "-nI", "--color=never", query]
            
            # Run process
            result = subprocess.run(
                cmd,
                cwd=str(target_dir),
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            elif result.returncode == 1:
                return f"No matches found for pattern: '{query}'"
            else:
                # Fallback to manual directory walk if git fails or is not in target directory
                matches = []
                for root, _, files in os.walk(target_dir):
                    # Skip common ignored directories
                    if any(ignored in root for ignored in [".git", "__pycache__", ".venv", "venv"]):
                        continue
                    for file in files:
                        file_path = pathlib.Path(root) / file
                        if file_path.suffix.lower() in [".py", ".md", ".json", ".txt", ".toml", ".bat", ".ps1"]:
                            try:
                                content = file_path.read_text(encoding="utf-8", errors="ignore")
                                for i, line in enumerate(content.splitlines(), 1):
                                    if query.lower() in line.lower():
                                        rel_path = file_path.relative_to(WORKSPACE_ROOT)
                                        matches.append(f"{rel_path}:{i}:{line.strip()}")
                            except Exception:
                                pass
                return "\n".join(matches) if matches else f"No matches found for: '{query}'"
        except Exception as exc:
            return f"Error searching: {exc}"

    @mcp.tool()
    def symbol_search(query: str) -> List[Dict[str, Any]]:
        """
        Search for Python symbols (classes, functions, methods) defined in the codebase.
        Matches symbol names matching the query (case-insensitive).
        """
        symbols = []
        try:
            # Recursively walk codebase to find .py files
            for root, _, files in os.walk(WORKSPACE_ROOT):
                if any(ignored in root for ignored in [".git", "__pycache__", ".venv", "venv", ".agents"]):
                    continue
                for file in files:
                    if file.endswith(".py"):
                        file_path = pathlib.Path(root) / file
                        try:
                            content = file_path.read_text(encoding="utf-8")
                            tree = ast.parse(content, filename=str(file_path))
                            
                            # Parse AST nodes
                            for node in ast.walk(tree):
                                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    if query.lower() in node.name.lower():
                                        symbols.append({
                                            "name": node.name,
                                            "type": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                                            "line": node.lineno,
                                            "file": str(file_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
                                        })
                                elif isinstance(node, ast.ClassDef):
                                    if query.lower() in node.name.lower():
                                        symbols.append({
                                            "name": node.name,
                                            "type": "class",
                                            "line": node.lineno,
                                            "file": str(file_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
                                        })
                        except Exception:
                            # Skip files that fail parsing
                            pass
            return sorted(symbols, key=lambda x: (x["file"], x["line"]))
        except Exception as exc:
            return [{"error": str(exc)}]
