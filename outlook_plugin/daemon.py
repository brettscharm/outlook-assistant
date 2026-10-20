"""
Background Watcher & macOS Desktop Notification Daemon
Monitors Outlook in background and triggers native macOS notifications for meetings and urgent emails.
"""

import logging
import subprocess
import time
from datetime import datetime
from typing import Set

from .ai_agent import BobAIAgent
from .engine import OutlookEngine
from .updater import run_background_update_check

logger = logging.getLogger(__name__)


def show_mac_notification(title: str, message: str, subtitle: str = "Outlook Assistant"):
    """Trigger native macOS desktop banner notification."""
    script = f'''
    display notification "{message}" with title "{title}" subtitle "{subtitle}"
    '''
    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=5)
    except Exception:
        pass


def run_daemon_loop(poll_interval: int = 180):
    """
    Background polling loop:
    - Runs every `poll_interval` seconds (default 3 mins)
    - Checks for upcoming meetings in the next 15 mins
    - Checks for high-priority urgent emails
    - Automatically updates from GitHub
    """
    engine = OutlookEngine()
    ai = BobAIAgent()
    notified_event_ids: Set[str] = set()
    notified_email_ids: Set[str] = set()

    print(f"🤖 Outlook Background Daemon started (polling every {poll_interval}s)...")
    show_mac_notification("Outlook Assistant Active", "Monitoring calendar and inbox in background.")

    while True:
        try:
            # 1. Background auto-updater check
            run_background_update_check()

            # 2. Check Upcoming Meetings
            events = engine.get_upcoming_events(days_ahead=1, limit=10)
            now = datetime.now()
            for ev in events:
                ev_id = ev.get("id")
                if ev_id in notified_event_ids:
                    continue

                subj = ev.get("subject", "Meeting")
                loc = ev.get("location", "")
                notified_event_ids.add(ev_id)
                show_mac_notification(f"Upcoming: {subj}", f"Location: {loc or 'Virtual'}", "Calendar Reminder")

            # 3. Check Urgent Unread Emails
            unread = engine.get_emails(folder="inbox", limit=10, unread_only=True)
            for em in unread:
                em_id = em.get("id")
                if em_id in notified_email_ids:
                    continue

                subj = em.get("subject", "")
                if any(w in subj.lower() for w in ["urgent", "asap", "deadline", "action required"]):
                    notified_email_ids.add(em_id)
                    show_mac_notification(f"🚨 Urgent: {em.get('sender')}", subj, "Priority Email")

        except Exception as e:
            logger.debug(f"Daemon cycle error: {e}")

        time.sleep(poll_interval)
