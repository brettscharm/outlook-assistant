"""
Built-in Local Web Application Server for Outlook Assistant
Runs a zero-dependency local web app at http://localhost:8484 with REST endpoints.
"""

import http.server
import json
import logging
import os
import socketserver
import urllib.parse
from pathlib import Path
from typing import Any, Dict

from .ai_agent import BobAIAgent, get_bob_api_key, save_bob_api_key
from .engine import OutlookEngine

logger = logging.getLogger(__name__)

PORT = 8484
STATIC_DIR = Path(__file__).parent / "static"


class AppRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP Request Handler for Outlook Assistant Web UI and REST API."""

    def __init__(self, *args, **kwargs):
        self.engine = OutlookEngine()
        self.ai = BobAIAgent()
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            return super().do_GET()

        if path == "/api/status":
            return self._send_json(self.engine.get_status())

        elif path == "/api/calendar":
            days = int(query.get("days", [7])[0])
            limit = int(query.get("limit", [50])[0])
            events = self.engine.get_upcoming_events(days_ahead=days, limit=limit)
            return self._send_json(events)

        elif path == "/api/emails":
            folder = query.get("folder", ["inbox"])[0]
            limit = int(query.get("limit", [25])[0])
            unread = query.get("unread_only", ["false"])[0].lower() == "true"
            emails = self.engine.get_emails(folder=folder, limit=limit, unread_only=unread)
            return self._send_json(emails)

        elif path == "/api/briefing":
            events = self.engine.get_upcoming_events(days_ahead=2, limit=20)
            unread = self.engine.get_emails(folder="inbox", limit=15, unread_only=True)
            briefing = self.ai.generate_ai_briefing(events, unread)
            return self._send_json(briefing)

        elif path == "/api/config":
            return self._send_json({
                "bob_api_key": get_bob_api_key(),
                "webhook_url": os.environ.get("OUTLOOK_TELEMETRY_WEBHOOK", ""),
            })

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/config":
            key = data.get("bob_api_key", "").strip()
            if key:
                save_bob_api_key(key)
            return self._send_json({"status": "saved"})

        elif path == "/api/smart-reply":
            email_id = data.get("email_id")
            intent = data.get("intent", "agree_meet")

            email = self.engine.get_email_details(email_id) if email_id else None
            if not email:
                # Fallback to search list
                emails = self.engine.get_emails(limit=25)
                email = next((e for e in emails if str(e.get("id")) == str(email_id)), None)

            if not email:
                return self._send_json({"error": "Email not found"}, status=404)

            events = self.engine.get_upcoming_events(days_ahead=5, limit=10)
            reply = self.ai.draft_smart_reply(email, events, intent=intent)
            return self._send_json({"reply": reply})

        self.send_error(404, "Endpoint not found")


def start_app_server(port: int = PORT, open_browser: bool = True):
    """Start local HTTP server."""
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), AppRequestHandler) as httpd:
        url = f"http://localhost:{port}"
        print(f"🚀 Outlook AI Assistant App running at: {url}")
        if open_browser:
            import webbrowser
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
