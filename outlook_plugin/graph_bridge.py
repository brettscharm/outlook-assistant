"""
Microsoft Graph API Bridge for Outlook (M365 / Exchange Online)
Allows cross-platform or cloud-synced access to Outlook emails and calendar events.
"""

import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GraphOutlookBridge:
    """Bridge for Microsoft Graph API (Office 365 / Outlook)."""

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0"

    def is_available(self) -> bool:
        """Check if an access token is configured."""
        return bool(self.access_token)

    def _api_get(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make an authenticated GET request to Microsoft Graph API."""
        if not self.access_token:
            raise ValueError("Microsoft Graph access token is required.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        if params:
            url += f"?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Prefer": 'outlook.timezone="UTC"',
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except Exception as e:
            logger.error(f"Graph API request failed on {endpoint}: {e}")
            raise

    def get_emails(
        self,
        folder: str = "inbox",
        limit: int = 25,
        unread_only: bool = False,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch emails via Microsoft Graph API."""
        endpoint = f"me/mailFolders/{folder}/messages" if folder.lower() != "inbox" else "me/messages"
        params = {
            "$top": str(limit),
            "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview",
            "$orderby": "receivedDateTime desc",
        }
        filters = []
        if unread_only:
            filters.append("isRead eq false")
        if search_term:
            # Simple contains filter or search query
            params["$search"] = f'"{search_term}"'
        if filters and "$search" not in params:
            params["$filter"] = " and ".join(filters)

        data = self._api_get(endpoint, params)
        raw_msgs = data.get("value", [])

        emails = []
        for m in raw_msgs:
            from_info = m.get("from", {}).get("emailAddress", {})
            sender = f"{from_info.get('name', 'Unknown')} <{from_info.get('address', '')}>"
            emails.append({
                "id": m.get("id", ""),
                "subject": m.get("subject", "(No Subject)"),
                "sender": sender,
                "received_time": m.get("receivedDateTime", ""),
                "is_read": m.get("isRead", False),
                "preview": m.get("bodyPreview", ""),
            })
        return emails

    def get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full message details including HTML/text body."""
        endpoint = f"me/messages/{message_id}"
        params = {"$select": "id,subject,from,receivedDateTime,isRead,body"}
        try:
            m = self._api_get(endpoint, params)
            from_info = m.get("from", {}).get("emailAddress", {})
            sender = f"{from_info.get('name', 'Unknown')} <{from_info.get('address', '')}>"
            body_content = m.get("body", {}).get("content", "")
            return {
                "id": m.get("id", message_id),
                "subject": m.get("subject", "(No Subject)"),
                "sender": sender,
                "received_time": m.get("receivedDateTime", ""),
                "is_read": m.get("isRead", False),
                "body": body_content,
            }
        except Exception:
            return None

    def get_upcoming_events(
        self,
        days_ahead: int = 7,
        limit: int = 50,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch calendar events for the upcoming N days via calendarView endpoint."""
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days_ahead)

        params = {
            "startDateTime": now.isoformat(),
            "endDateTime": end.isoformat(),
            "$top": str(limit),
            "$select": "id,subject,start,end,location,isAllDay,recurrence,bodyPreview",
            "$orderby": "start/dateTime asc",
        }

        data = self._api_get("me/calendarView", params)
        raw_events = data.get("value", [])

        events = []
        for ev in raw_events:
            loc = ev.get("location", {}).get("displayName", "None")
            subject = ev.get("subject", "(No Title)")
            if search_term:
                st = search_term.lower()
                if st not in subject.lower() and st not in loc.lower() and st not in ev.get("bodyPreview", "").lower():
                    continue

            events.append({
                "id": ev.get("id", ""),
                "subject": subject,
                "start_time": ev.get("start", {}).get("dateTime", ""),
                "end_time": ev.get("end", {}).get("dateTime", ""),
                "location": loc or "None",
                "is_all_day": ev.get("isAllDay", False),
                "is_recurring": bool(ev.get("recurrence")),
                "description": ev.get("bodyPreview", ""),
            })
        return events
