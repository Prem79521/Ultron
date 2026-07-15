"""
MCP Git Tools — Expose repository metadata, status, diffs, and logs.
"""

import subprocess
from typing import Dict, Any

def _run_git_cmd(args: list) -> str:
    """Helper to run a git command and return stripped output or error."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Git error (code {result.returncode}): {result.stderr.strip()}"
    except Exception as exc:
        return f"Process execution failed: {exc}"

def register(mcp):

    @mcp.tool()
    def git_status() -> str:
        """Get the current working directory status of the git repository."""
        return _run_git_cmd(["status"])

    @mcp.tool()
    def git_diff() -> str:
        """Get the unstaged changes (git diff) of the repository."""
        diff = _run_git_cmd(["diff"])
        if not diff:
            return "No unstaged changes in the working directory."
        return diff

    @mcp.tool()
    def git_log(limit: int = 15) -> str:
        """
        Get the git commit log.
        Limit is the maximum number of commits to return (default: 15).
        """
        return _run_git_cmd(["log", f"-n", str(limit), "--oneline"])

    @mcp.tool()
    def get_repo_metadata() -> Dict[str, Any]:
        """Get metadata about the repository (active branch, remote URLs, last commit)."""
        active_branch = _run_git_cmd(["branch", "--show-current"])
        remote_url = _run_git_cmd(["remote", "get-url", "origin"])
        last_commit_hash = _run_git_cmd(["log", "-1", "--format=%H"])
        last_commit_msg = _run_git_cmd(["log", "-1", "--format=%s"])
        last_commit_date = _run_git_cmd(["log", "-1", "--format=%cd"])
        
        return {
            "active_branch": active_branch,
            "remote_origin_url": remote_url,
            "last_commit": {
                "hash": last_commit_hash,
                "message": last_commit_msg,
                "date": last_commit_date
            }
        }
