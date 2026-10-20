"""
Telemetry & Usage Tracking Module for Outlook Assistant
Allows tracking installations, active users, and tool usage across distributed deployments.
"""

import json
import logging
import os
import platform
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

UID_FILE = Path.home() / ".outlook_assistant_uid"
CONFIG_FILE = Path.home() / ".outlook_assistant_config.json"

# Default webhook URL (Can be replaced with your Discord/Slack/Supabase/Airtable webhook)
# Or set via environment variable: export OUTLOOK_TELEMETRY_WEBHOOK="https://..."
DEFAULT_WEBHOOK_URL = os.environ.get("OUTLOOK_TELEMETRY_WEBHOOK", "")


def get_user_id() -> str:
    """Get or generate a persistent anonymous device/user ID."""
    try:
        if UID_FILE.exists():
            return UID_FILE.read_text().strip()
        uid = str(uuid.uuid4())
        UID_FILE.write_text(uid)
        return uid
    except Exception:
        return "unknown-user"


def get_user_metadata() -> Dict[str, Any]:
    """Collect anonymous device and environment metadata."""
    return {
        "user_id": get_user_id(),
        "username": os.environ.get("USER", "unknown"),
        "hostname": platform.node(),
        "os": platform.system(),
        "os_release": platform.release(),
        "arch": platform.machine(),
        "python_version": platform.python_version(),
    }


def track_event(event_name: str, extra_data: Optional[Dict[str, Any]] = None, webhook_url: Optional[str] = None):
    """
    Send a telemetry heartbeat event to your webhook/analytics endpoint.
    
    Args:
        event_name: e.g. 'install', 'launch', 'daily_briefing', 'mcp_call'
        extra_data: Optional dictionary with extra context
    """
    target_url = webhook_url or os.environ.get("OUTLOOK_TELEMETRY_WEBHOOK") or DEFAULT_WEBHOOK_URL
    if not target_url:
        return

    payload = {
        "event": event_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": get_user_metadata(),
        "data": extra_data or {},
    }

    try:
        req = urllib.request.Request(
            target_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "OutlookAssistant-Telemetry/1.0"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=4)
    except Exception as e:
        logger.debug(f"Telemetry ping failed (non-critical): {e}")
