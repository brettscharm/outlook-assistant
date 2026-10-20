"""
CLI for Outlook Assistant Plugin
Allows direct command-line inspection, running the local web app, and background daemon.
"""

import argparse
import json
import sys
from .engine import OutlookEngine
from .updater import check_and_apply_update, run_background_update_check
from .telemetry import track_event


def format_table(headers, rows):
    if not rows:
        return "No items found."
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)[:50]))

    fmt = " | ".join(f"{{:<{w}}}" for w in widths)
    divider = "-+-".join("-" * w for w in widths)

    lines = [fmt.format(*headers), divider]
    for row in rows:
        lines.append(fmt.format(*[str(val)[:50] for val in row]))
    return "\n".join(lines)


def main():
    # Background update check (non-blocking / periodic)
    run_background_update_check()

    parser = argparse.ArgumentParser(
        prog="outlook-assistant",
        description="Outlook Assistant Plugin - Read emails and know upcoming calendar events directly from your computer.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # App Web UI
    p_app = subparsers.add_parser("app", help="Launch the local Outlook Assistant Web App & Dashboard")
    p_app.add_argument("--port", type=int, default=8484, help="Port to run on (default: 8484)")
    p_app.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")

    # Daemon
    p_daemon = subparsers.add_parser("daemon", help="Run background watcher with native macOS notifications")
    p_daemon.add_argument("--interval", type=int, default=180, help="Polling interval in seconds (default: 180)")

    # Status
    subparsers.add_parser("status", help="Check Outlook application status and connectivity")

    # Update
    subparsers.add_parser("update", help="Check and apply latest updates from GitHub")

    # Emails
    p_emails = subparsers.add_parser("emails", help="List recent or unread emails")
    p_emails.add_argument("--folder", default="inbox", help="Mail folder name (default: inbox)")
    p_emails.add_argument("--limit", type=int, default=15, help="Number of emails to fetch (default: 15)")
    p_emails.add_argument("--unread", action="store_true", help="Fetch unread emails only")
    p_emails.add_argument("--search", type=str, default=None, help="Search filter text")
    p_emails.add_argument("--json", action="store_true", help="Output as JSON")

    # Read Email Body
    p_email_get = subparsers.add_parser("read-email", help="Fetch complete email message by ID")
    p_email_get.add_argument("id", type=str, help="Message ID")
    p_email_get.add_argument("--json", action="store_true", help="Output as JSON")

    # Calendar
    p_cal = subparsers.add_parser("calendar", help="List upcoming calendar events")
    p_cal.add_argument("--days", type=int, default=7, help="Days ahead to search (default: 7)")
    p_cal.add_argument("--limit", type=int, default=25, help="Max events to return (default: 25)")
    p_cal.add_argument("--search", type=str, default=None, help="Filter event by title or location")
    p_cal.add_argument("--json", action="store_true", help="Output as JSON")

    # Daily Briefing
    p_brief = subparsers.add_parser("briefing", help="Display an executive briefing of your day (agenda & unread mail)")
    p_brief.add_argument("--json", action="store_true", help="Output as JSON")

    # Search
    p_search = subparsers.add_parser("search", help="Search both emails and calendar events")
    p_search.add_argument("query", type=str, help="Search term")
    p_search.add_argument("--json", action="store_true", help="Output as JSON")

    # MCP Server
    subparsers.add_parser("mcp", help="Launch the MCP (Model Context Protocol) Server on stdio")

    args = parser.parse_args()

    if not args.command:
        # Default to launching the web app when run with no arguments
        from .app_server import start_app_server
        start_app_server()
        return

    # Fire telemetry heartbeat
    track_event(f"cli_{args.command}")

    if args.command == "app":
        from .app_server import start_app_server
        start_app_server(port=args.port, open_browser=not args.no_browser)
        return

    if args.command == "daemon":
        from .daemon import run_daemon_loop
        run_daemon_loop(poll_interval=args.interval)
        return

    if args.command == "update":
        updated, msg = check_and_apply_update(auto_pull=True)
        print(f"📦 Update Status: {msg}")
        return

    if args.command == "mcp":
        from .mcp_server import run_mcp_server
        run_mcp_server()
        return

    engine = OutlookEngine()

    if args.command == "status":
        status = engine.get_status()
        print(json.dumps(status, indent=2))
        return

    if args.command == "emails":
        emails = engine.get_emails(
            folder=args.folder,
            limit=args.limit,
            unread_only=args.unread,
            search_term=args.search,
        )
        if args.json:
            print(json.dumps(emails, indent=2))
        else:
            headers = ["ID", "Status", "Sender", "Received", "Subject"]
            rows = [
                [
                    e.get("id", ""),
                    "UNREAD" if not e.get("is_read") else "READ",
                    e.get("sender", "")[:30],
                    e.get("received_time", "")[:20],
                    e.get("subject", "")[:45],
                ]
                for e in emails
            ]
            print(f"=== Emails in '{args.folder}' ({len(emails)} results) ===")
            print(format_table(headers, rows))
        return

    if args.command == "read-email":
        em = engine.get_email_details(args.id)
        if not em:
            print(f"Error: Could not retrieve email with ID '{args.id}'")
            sys.exit(1)
        if args.json:
            print(json.dumps(em, indent=2))
        else:
            print("=" * 60)
            print(f"Subject: {em.get('subject')}")
            print(f"From:    {em.get('sender')}")
            print(f"Date:    {em.get('received_time')}")
            print(f"Status:  {'READ' if em.get('is_read') else 'UNREAD'}")
            print("=" * 60)
            print(em.get("body", ""))
            print("=" * 60)
        return

    if args.command == "calendar":
        events = engine.get_upcoming_events(
            days_ahead=args.days,
            limit=args.limit,
            search_term=args.search,
        )
        if args.json:
            print(json.dumps(events, indent=2))
        else:
            headers = ["ID", "Start Time", "End Time", "Subject", "Location"]
            rows = [
                [
                    ev.get("id", ""),
                    ev.get("start_time", "")[:20],
                    ev.get("end_time", "")[:20],
                    ev.get("subject", "")[:35],
                    ev.get("location", "")[:25],
                ]
                for ev in events
            ]
            print(f"=== Upcoming Events (Next {args.days} Days: {len(events)} found) ===")
            print(format_table(headers, rows))
        return

    if args.command == "briefing":
        briefing = engine.get_daily_briefing()
        if args.json:
            print(json.dumps(briefing, indent=2))
        else:
            print("=" * 60)
            print(f"🗓️ OUTLOOK EXECUTIVE BRIEFING — {briefing['generated_at']}")
            print("=" * 60)
            print(f"\n📅 UPCOMING CALENDAR EVENTS ({briefing['upcoming_events_count']}):")
            if not briefing["upcoming_events"]:
                print("   (No upcoming events scheduled)")
            for ev in briefing["upcoming_events"]:
                print(f"   • [{ev.get('start_time')}] {ev.get('subject')} (📍 {ev.get('location')})")

            print(f"\n✉️ UNREAD EMAILS ({briefing['unread_emails_count']}):")
            if briefing["urgent_emails"]:
                print("   🚨 URGENT / HIGH PRIORITY:")
                for em in briefing["urgent_emails"]:
                    print(f"     ! {em.get('sender')} — {em.get('subject')}")

            if briefing["recent_unread_emails"]:
                print("   📬 Recent Unread:")
                for em in briefing["recent_unread_emails"]:
                    print(f"     • {em.get('sender')} — {em.get('subject')}")

            if not briefing["urgent_emails"] and not briefing["recent_unread_emails"]:
                print("   (Inbox is clean / zero unread)")
            print("=" * 60)
        return

    if args.command == "search":
        res = engine.search_all(args.query)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"=== Unified Search Results for '{args.query}' ===")
            print(f"\n✉️ Matching Emails ({len(res['emails'])}):")
            for em in res["emails"]:
                print(f"  • [{em.get('received_time')}] {em.get('sender')}: {em.get('subject')}")
            print(f"\n📅 Matching Calendar Events ({len(res['events'])}):")
            for ev in res["events"]:
                print(f"  • [{ev.get('start_time')}] {ev.get('subject')} (📍 {ev.get('location')})")
        return


if __name__ == "__main__":
    main()
