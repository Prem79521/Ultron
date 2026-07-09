# ULTRON Safety Framework

ULTRON classifies tool actions to ensure host security and data integrity.

## Safety Levels
1.  **Safe**: Actions with no risk of destructive side-effects (e.g. read_file, search_web). Auto-approved.
2.  **Warning**: Actions that modify local user data or source code (e.g. write_file, git_commit, run_command). Requires explicit confirmation.
3.  **Critical**: System-level adjustments, OS shutdowns, or registry edits. Blocked by default.
