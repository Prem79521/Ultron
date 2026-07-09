"""
ULTRON Security & Cryptography Layer — Manages permission audits, token signatures, and configuration encryption.
"""

import base64
import logging
import uuid
from typing import Dict, Any
from ultron.core.event_bus import event_bus

# Obfuscation XOR key
OBFUSCATION_KEY = b"ULTRON_SECURE_COGNITIVE_OS_KEY_2026"

def encrypt_value(value: str) -> str:
    """Obfuscates sensitive credentials (e.g. key tokens) using symmetric XOR base64 representation."""
    if not value:
        return ""
    try:
        data = value.encode('utf-8')
        xored = bytes(data[i] ^ OBFUSCATION_KEY[i % len(OBFUSCATION_KEY)] for i in range(len(data)))
        return base64.b64encode(xored).decode('utf-8')
    except Exception:
        return value

def decrypt_value(encrypted: str) -> str:
    """Decodes XOR base64 obfuscated credential fields."""
    if not encrypted:
        return ""
    try:
        xored = base64.b64decode(encrypted.encode('utf-8'))
        decoded = bytes(xored[i] ^ OBFUSCATION_KEY[i % len(OBFUSCATION_KEY)] for i in range(len(xored)))
        return decoded.decode('utf-8')
    except Exception:
        return encrypted

def audit_permission(plugin_name: str, requested_capability: str) -> bool:
    """Audits third-party capabilities, ensuring plugins possess the requested OS access rights."""
    logger = logging.getLogger("ultron-agent")
    from ultron.hal.hal_manager import get_hal_manager
    hal = get_hal_manager()
    
    is_allowed = True
    if hal:
        is_allowed = hal.is_allowed(requested_capability)

    audit_record = {
        "plugin": plugin_name,
        "capability": requested_capability,
        "allowed": is_allowed,
        "session_token": str(uuid.uuid4())
    }
    
    if not is_allowed:
        logger.warning(f"[SECURITY AUDIT] Denied plugin '{plugin_name}' access to capability '{requested_capability}'")
        event_bus.publish("WARNING_OCCURRED", {"message": f"Plugin '{plugin_name}' denied access to: {requested_capability}"})
    else:
        logger.info(f"[SECURITY AUDIT] Approved plugin '{plugin_name}' access to capability '{requested_capability}'")
        
    event_bus.publish("SECURITY_AUDIT_LOG", audit_record)
    return is_allowed
