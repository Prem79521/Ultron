# ULTRON Permissions Module

## Purpose
The Permissions module implements security checks that gate system operations. It classifies tools and actions into security categories (Safe, Warning, Critical) and prompts for authorization where necessary.

## Responsibilities
*   **Action Classification**: Evaluates commands or tool requests based on safety classifications.
*   **Security Gating**: Interrupts the execution loop to request developer approval when Warning or Critical actions are initiated.
*   **Audit Logging**: Maintained logs of granted, rejected, or bypassed permissions.

## Security Classifications

### 1. Safe (Auto-Approved)
*   Reading files and code layouts.
*   Initiating external internet search engines.
*   Launching system browsers or dashboards.

### 2. Warning (User Confirmation Required)
*   Deleting or writing files in the workspace.
*   Executing git repository actions (commits, checkouts).
*   Running command-line shells or terminal scripts.

### 3. Critical (Strict Verification Required / Blocked by default)
*   System shutdown or reboots.
*   Registry edits or editing core configuration parameters.
*   Accessing sensitive private credential directories.

## Public Interfaces
*   `class PermissionManager`: Gating controller.
    *   `async def check_permission(action_type: str, details: Dict[str, Any]) -> bool`
    *   `def set_policy(action_type: str, policy: str) -> None`

## Dependencies
*   `ultron.core` for audit logs.

## Future Expansion
*   Implement interactive OS system dialogue popups to prompt developers directly during audio/text interactions.
*   Add configuration rules inside `ultron.json` to allow developers to auto-approve custom warning commands.

## Design Notes
*   **Fail-Safe**: If an action type is unknown or unclassified, it must default to the **Critical** classification.
