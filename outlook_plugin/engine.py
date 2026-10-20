"""
Unified Outlook Assistant Engine
Provides high-level intelligence across emails and calendar events.
"""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional, Tuple

from .mac_bridge import MacOutlookBridge
from .local_store import LocalStoreBridge
from .graph_bridge import GraphOutlookBridge

logger = logging.getLogger(__name__)


class OutlookEngine:
    """Unified engine to read, correlate, and analyze Outlook emails and calendar events."""

    def __init__(
        self,
        prefer_mac: bool = True,
        graph_token: Optional[str] = None,
    ):
        self.mac_bridge = MacOutlookBridge()
        self.local_store = LocalStoreBridge()
        self.graph_bridge = GraphOutlookBridge(access_token=graph_token) if graph_token else None
        self.prefer_mac = prefer_mac

    def get_active_backend(self):
        """Returns the primary active bridge (macOS local or Graph API)."""
        if self.prefer_mac and self.local_store.is_available():
            return self.local_store
        if self.prefer_mac and self.mac_bridge.is_available():
            return self.mac_bridge
        if self.graph_bridge and self.graph_bridge.is_available():
            return self.graph_bridge
        return self.mac_bridge

    def get_status(self) -> Dict[str, Any]:
        """Check connection status of local Outlook and cloud integrations."""
        if self.local_store.is_available() and self.prefer_mac:
            return self.local_store.status()
        is_mac_avail = self.mac_bridge.is_available()
        is_mac_running = self.mac_bridge.is_running() if is_mac_avail else False
        is_graph_avail = self.graph_bridge.is_available() if self.graph_bridge else False

        active_type = "mac_local" if is_mac_avail else ("graph_api" if is_graph_avail else "none")

        return {
            "active_backend": active_type,
            "mac_outlook_installed": is_mac_avail,
            "mac_outlook_running": is_mac_running,
            "graph_api_configured": is_graph_avail,
        }

    def list_accounts(self) -> List[Dict[str, Any]]:
        """List configured Outlook email accounts."""
        backend = self.get_active_backend()
        if hasattr(backend, "list_accounts"):
            return backend.list_accounts()
        return [{"type": "all", "name": "All Accounts", "email": "all"}]

    def list_folders(self) -> List[Dict[str, Any]]:
        """List all mailbox folders."""
        backend = self.get_active_backend()
        if hasattr(backend, "list_folders"):
            return backend.list_folders()
        return []

    def get_emails(
        self,
        folder: str = "inbox",
        limit: int = 25,
        unread_only: bool = False,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent or unread emails."""
        backend = self.get_active_backend()
        return backend.get_emails(
            folder=folder,
            limit=limit,
            unread_only=unread_only,
            search_term=search_term,
        )

    def get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full body and headers of an email."""
        backend = self.get_active_backend()
        return backend.get_email_details(message_id)

    def get_upcoming_events(
        self,
        days_ahead: int = 7,
        limit: int = 50,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve upcoming calendar events."""
        backend = self.get_active_backend()
        return backend.get_upcoming_events(
            days_ahead=days_ahead,
            limit=limit,
            search_term=search_term,
        )

    def search_all(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """Search across both emails and calendar events simultaneously."""
        emails = self.get_emails(limit=25, search_term=query)
        events = self.get_upcoming_events(days_ahead=30, limit=25, search_term=query)
        return {
            "query": query,
            "emails": emails,
            "events": events,
        }

    def get_daily_briefing(self) -> Dict[str, Any]:
        """
        Generate a comprehensive executive daily briefing:
        - Upcoming agenda for today and tomorrow
        - Unread important emails
        - Schedule summary
        """
        today_events = self.get_upcoming_events(days_ahead=2, limit=20)
        unread_emails = self.get_emails(folder="inbox", limit=15, unread_only=True)

        urgent_emails = []
        normal_unread = []
        urgent_keywords = ["urgent", "asap", "action required", "important", "immediate", "deadline", "reminder"]

        for em in unread_emails:
            subj_lower = em.get("subject", "").lower()
            if any(k in subj_lower for k in urgent_keywords):
                urgent_emails.append(em)
            else:
                normal_unread.append(em)

        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "upcoming_events_count": len(today_events),
            "upcoming_events": today_events,
            "unread_emails_count": len(unread_emails),
            "urgent_emails": urgent_emails,
            "recent_unread_emails": normal_unread[:10],
        }
