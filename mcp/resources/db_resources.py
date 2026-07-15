"""
MCP Database Resources — Exposes SQLite schemas and tables as read-only resources.
"""

import sqlite3
import os
import pathlib
from typing import Dict, Any

DB_PATH = pathlib.Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ultron_memory.db")))

def _get_readonly_conn():
    """Returns a read-only sqlite3 connection."""
    # Using uri=True and mode=ro forces SQLite to open the file strictly read-only
    db_uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    return sqlite3.connect(db_uri, uri=True)

def register(mcp):

    @mcp.resource("sqlite://ultron_memory.db/schema")
    def database_schema() -> str:
        """Returns the complete schema of the ULTRON memory database."""
        if not DB_PATH.is_file():
            return "Database file not found."
            
        try:
            conn = _get_readonly_conn()
            cursor = conn.cursor()
            
            # Fetch all tables
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            schema_report = ["### ULTRON MEMORY DATABASE SCHEMA\n"]
            for table_name, create_sql in tables:
                schema_report.append(f"#### Table: {table_name}")
                schema_report.append("```sql")
                schema_report.append(create_sql)
                schema_report.append("```")
                
                # Fetch column details
                cursor.execute(f"PRAGMA table_info({table_name});")
                cols = cursor.fetchall()
                schema_report.append("Columns:")
                for col in cols:
                    # col[1] = name, col[2] = type, col[3] = notnull, col[4] = dflt_value, col[5] = pk
                    pk_str = " (PRIMARY KEY)" if col[5] else ""
                    null_str = " NOT NULL" if col[3] else ""
                    schema_report.append(f"  - {col[1]} ({col[2]}){null_str}{pk_str}")
                schema_report.append("")
                
            conn.close()
            return "\n".join(schema_report)
        except Exception as exc:
            return f"Error retrieving database schema: {exc}"

    @mcp.resource("sqlite://ultron_memory.db/{table_name}")
    def database_table(table_name: str) -> str:
        """Exposes the contents of a specific table in the database (first 100 rows)."""
        if not DB_PATH.is_file():
            return "Database file not found."
            
        # Security check: whitelist valid table names to prevent SQL injection in pragma/queries
        valid_tables = [
            "preference", "permission", "project", "conversation", 
            "session", "log", "voice_settings", "provider_settings", 
            "plugin_settings", "notification", "voice_history", 
            "wake_history", "diagnostics"
        ]
        
        # Check if table starts with any of the UME table prefixes/names
        # UME prefixes tables with the store name (e.g. project_memory, etc.)
        matched_table = None
        for v_tbl in valid_tables:
            if table_name == v_tbl or table_name.startswith(v_tbl):
                matched_table = table_name
                break
                
        if not matched_table:
            return f"Access Denied: Table '{table_name}' is not in the allowed UME tables list."
            
        try:
            conn = _get_readonly_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Safe query since table name is validated against a whitelist
            cursor.execute(f"SELECT * FROM {matched_table} LIMIT 100;")
            rows = cursor.fetchall()
            
            if not rows:
                conn.close()
                return f"Table '{matched_table}' exists but contains no records."
                
            # Get columns
            columns = rows[0].keys()
            
            report = [f"### Table: {matched_table} (showing up to 100 records)\n"]
            
            # Format markdown table
            header_row = " | ".join(columns)
            separator = " | ".join(["---"] * len(columns))
            report.append(f"| {header_row} |")
            report.append(f"| {separator} |")
            
            for row in rows:
                vals = []
                for col in columns:
                    val = str(row[col])
                    # Escape newlines and pipes to preserve markdown table formatting
                    val = val.replace("\n", " ").replace("|", "\\|")
                    if len(val) > 100:
                        val = val[:97] + "..."
                    vals.append(val)
                report.append(f"| {' | '.join(vals)} |")
                
            conn.close()
            return "\n".join(report)
        except Exception as exc:
            return f"Error retrieving table data: {exc}"
