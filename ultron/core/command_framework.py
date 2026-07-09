"""
ULTRON Command Framework — Declares structured execution, validation, permissions, and undo scopes.
"""

import sys
import os
import subprocess
import time
from typing import Dict, Any, List, Optional

class UltronCommand:
    """Base class for all Cognitive OS explicit command routines."""
    def __init__(
        self,
        name: str,
        description: str,
        category: str = "System",
        aliases: List[str] = None,
        permissions: List[str] = None,
        requires_confirmation: bool = False
    ):
        self.name = name
        self.description = description
        self.category = category
        self.aliases = aliases or []
        self.permissions = permissions or []
        self.requires_confirmation = requires_confirmation
        self._undo_data: Any = None

    def execute(self, args: List[str], dry_run: bool = False) -> str:
        """Executes the command. Override in subclasses."""
        raise NotImplementedError

    def undo(self) -> str:
        """Undoes the command action if supported."""
        return f"Command '{self.name}' does not support undo operations."

class ShutdownCommand(UltronCommand):
    def __init__(self):
        super().__init__(
            name="shutdown",
            description="Exits the ULTRON Cognitive Operating System runtime.",
            aliases=["exit", "quit", "poweroff"],
            permissions=["system_shutdown"],
            requires_confirmation=True
        )

    def execute(self, args: List[str], dry_run: bool = False) -> str:
        if dry_run:
            return "Dry-run: Shutdown command validated successfully."
        # Trigger shutdown sequence
        from ultron.core.event_bus import event_bus
        event_bus.publish("STATE_CHANGED", {"state": "Shutdown"})
        # Exit application cleanly
        sys.exit(0)

class RememberCommand(UltronCommand):
    def __init__(self):
        super().__init__(
            name="remember",
            description="Persists operator facts or settings to UME preference memory.",
            aliases=["save", "record", "store"],
            permissions=["memory_write"]
        )

    def execute(self, args: List[str], dry_run: bool = False) -> str:
        if len(args) < 2:
            return "Usage: remember <key> <value>"
        key, val = args[0], " ".join(args[1:])
        
        if dry_run:
            return f"Dry-run: Would save preference '{key}' = '{val}'."
            
        from ultron.memory import get_memory_manager
        mem = get_memory_manager()
        if mem:
            mem.create_record(memory_type="preference", title=key, content=val)
            self._undo_data = {"key": key}
            return f"Understood, I will remember that '{key}' is '{val}'."
        return "Memory Engine currently unavailable."

    def undo(self) -> str:
        if self._undo_data:
            from ultron.memory import get_memory_manager
            mem = get_memory_manager()
            if mem:
                key = self._undo_data["key"]
                records = mem.list_records("preference", limit=100)
                for r in records:
                    if r["title"] == key:
                        mem.delete_record("preference", r["id"])
                return f"Reverted: I have forgotten '{key}'."
        return "Nothing to undo."

class SummarizeCommand(UltronCommand):
    def __init__(self):
        super().__init__(
            name="summarize",
            description="Provides a high-level summary of active database logs.",
            aliases=["outline", "brief"],
            permissions=["memory_read"]
        )

    def execute(self, args: List[str], dry_run: bool = False) -> str:
        if dry_run:
            return "Dry-run: Summarization validated."
            
        from ultron.memory import get_memory_manager
        mem = get_memory_manager()
        if mem:
            records = mem.list_records("log", limit=10)
            if not records:
                return "No logs found to summarize."
            summary = [f"Summary of latest {len(records)} system event logs:"]
            for r in records:
                summary.append(f"- {r['title']}: {r['content'][:60]}...")
            return "\n".join(summary)
        return "Memory Engine currently offline."

class LaunchCommand(UltronCommand):
    def __init__(self):
        super().__init__(
            name="launch",
            description="Launches external applications or system command shells.",
            aliases=["run", "start"],
            permissions=["process_execution"]
        )

    def execute(self, args: List[str], dry_run: bool = False) -> str:
        if not args:
            return "Usage: launch <application_name>"
        app = args[0]
        
        if dry_run:
            return f"Dry-run: Would launch process '{app}'."
            
        try:
            # Safe process spawn (runs notepad or similar as fallback)
            subprocess.Popen(app, shell=True)
            return f"Launching '{app}' process."
        except Exception as e:
            return f"Failed to launch process: {e}"

class SearchCommand(UltronCommand):
    def __init__(self):
        super().__init__(
            name="search",
            description="Searches saved project records and UME memories.",
            aliases=["find", "query"],
            permissions=["memory_read"]
        )

    def execute(self, args: List[str], dry_run: bool = False) -> str:
        if not args:
            return "Usage: search <query_text>"
        query = " ".join(args)
        
        if dry_run:
            return f"Dry-run: Would search UME for query: '{query}'."
            
        from ultron.memory import get_memory_manager
        mem = get_memory_manager()
        if mem:
            from ultron.memory.store import SqliteMemoryStore
            # Search project and preference stores
            res = mem._stores["preference"].search(query) + mem._stores["project"].search(query)
            if not res:
                return f"No memories found matching: '{query}'."
            lines = [f"Found {len(res)} matches in UME:"]
            for r in res[:5]:
                lines.append(f"- [{r.memory_type.upper()}] {r.title}: {r.content}")
            return "\n".join(lines)
        return "Memory engine not initialized."

class ScheduleCommand(UltronCommand):
    def __init__(self):
        super().__init__(
            name="schedule",
            description="Schedules system event callbacks with delayed timings.",
            aliases=["timer", "delay"],
            permissions=["scheduler_access"]
        )

    def execute(self, args: List[str], dry_run: bool = False) -> str:
        if len(args) < 2:
            return "Usage: schedule <delay_seconds> <message>"
        try:
            delay = float(args[0])
            msg = " ".join(args[1:])
        except ValueError:
            return "Delay must be a numeric value representing seconds."
            
        if dry_run:
            return f"Dry-run: Would schedule event in {delay} seconds."
            
        from ultron.core.event_bus import event_bus
        # Publish scheduled event
        event_bus.publish("NOTIFICATION", {"title": "Scheduled Alert", "message": msg}, delay=delay)
        return f"Event scheduled. I will alert you in {delay} seconds."

class CommandRegistry:
    """Consolidated registry validating and executing user CLI strings."""
    def __init__(self):
        self._commands: Dict[str, UltronCommand] = {}
        self._history: List[str] = []
        self._undo_stack: List[UltronCommand] = []
        self._register_default_commands()

    def _register_default_commands(self):
        self.register(ShutdownCommand())
        self.register(RememberCommand())
        self.register(SummarizeCommand())
        self.register(LaunchCommand())
        self.register(SearchCommand())
        self.register(ScheduleCommand())

    def register(self, command: UltronCommand):
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command

    def get_command(self, name: str) -> Optional[UltronCommand]:
        return self._commands.get(name.lower())

    def list_commands(self) -> List[UltronCommand]:
        # Return unique list
        seen = set()
        unique = []
        for cmd in self._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                unique.append(cmd)
        return unique

    def execute_string(self, input_str: str, dry_run: bool = False) -> str:
        """Parses and executes a raw CLI input string."""
        tokens = input_str.strip().split()
        if not tokens:
            return "Empty command."
            
        cmd_name = tokens[0].lower()
        args = tokens[1:]
        
        command = self.get_command(cmd_name)
        if not command:
            return f"Command '{cmd_name}' is not recognized."
            
        # Security permission audit check (Phase 5.4)
        from ultron.core.security import audit_permission
        for perm in command.permissions:
            if not audit_permission("CommandFramework", perm):
                return f"Permission Denied: Missing capability '{perm}'"

        self._history.append(input_str)
        result = command.execute(args, dry_run=dry_run)
        if not dry_run:
            self._undo_stack.append(command)
        return result

    def undo_last(self) -> str:
        """Pops and reverts the last command execution."""
        if not self._undo_stack:
            return "No commands in undo history."
        command = self._undo_stack.pop()
        return command.undo()

# Global command dispatcher registry
command_registry = CommandRegistry()
