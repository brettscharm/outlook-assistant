"""
MCP (Model Context Protocol) Server for Outlook Assistant Plugin
Exposes Outlook emails and calendar tools over stdio for LLMs and AI Assistants.
"""

import json
import logging
import sys
from typing import Any, Dict, List

from .engine import OutlookEngine

logger = logging.getLogger(__name__)

TOOLS_DEFINITION = [
    {
        "name": "outlook_get_unread_emails",
        "description": "Fetch the latest unread emails from the user's Outlook inbox.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of unread emails to retrieve (default: 15)",
                    "default": 15,
                },
                "search_term": {
                    "type": "string",
                    "description": "Optional search term to filter emails by sender or subject",
                },
            },
        },
    },
    {
        "name": "outlook_get_recent_emails",
        "description": "Retrieve recent emails from Outlook from any folder (Inbox, Sent Items, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Folder name (e.g. 'inbox', 'Sent Items', 'Drafts'). Default is 'inbox'.",
                    "default": "inbox",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of emails to retrieve (default: 20)",
                    "default": 20,
                },
                "search_term": {
                    "type": "string",
                    "description": "Optional keyword to search across subject, sender, or body preview",
                },
            },
        },
    },
    {
        "name": "outlook_get_email_body",
        "description": "Retrieve the full text content and details of a specific email message using its ID.",
        "inputSchema": {
            "type": "object",
            "required": ["message_id"],
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The unique ID of the message to retrieve",
                },
            },
        },
    },
    {
        "name": "outlook_get_upcoming_events",
        "description": "Fetch all upcoming calendar events and meetings from the user's Outlook calendar.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days into the future to look (e.g. 1 for today/tomorrow, 7 for weekly schedule). Default is 7.",
                    "default": 7,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of events to return (default: 50)",
                    "default": 50,
                },
                "search_term": {
                    "type": "string",
                    "description": "Optional filter keyword (e.g., meeting topic, participant, or location)",
                },
            },
        },
    },
    {
        "name": "outlook_get_daily_briefing",
        "description": "Get an executive morning/daily briefing combining today's upcoming meetings, schedule conflicts, and urgent unread emails.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "outlook_search",
        "description": "Unified search across both Outlook emails and calendar events simultaneously for a keyword, client name, or project topic.",
        "inputSchema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query or keyword",
                },
            },
        },
    },
]


def handle_tool_call(engine: OutlookEngine, name: str, args: Dict[str, Any]) -> Any:
    """Execute the requested tool against the Outlook engine."""
    if name == "outlook_get_unread_emails":
        limit = args.get("limit", 15)
        search_term = args.get("search_term")
        return engine.get_emails(folder="inbox", limit=limit, unread_only=True, search_term=search_term)

    elif name == "outlook_get_recent_emails":
        folder = args.get("folder", "inbox")
        limit = args.get("limit", 20)
        search_term = args.get("search_term")
        return engine.get_emails(folder=folder, limit=limit, unread_only=False, search_term=search_term)

    elif name == "outlook_get_email_body":
        msg_id = args.get("message_id")
        res = engine.get_email_details(msg_id)
        return res if res else {"error": f"Message with ID {msg_id} not found."}

    elif name == "outlook_get_upcoming_events":
        days_ahead = args.get("days_ahead", 7)
        limit = args.get("limit", 50)
        search_term = args.get("search_term")
        return engine.get_upcoming_events(days_ahead=days_ahead, limit=limit, search_term=search_term)

    elif name == "outlook_get_daily_briefing":
        return engine.get_daily_briefing()

    elif name == "outlook_search":
        query = args.get("query", "")
        return engine.search_all(query)

    else:
        raise ValueError(f"Unknown tool: {name}")


def run_mcp_server():
    """Run JSON-RPC MCP server over stdio."""
    engine = OutlookEngine()

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": "outlook-assistant-plugin",
                            "version": "1.0.0",
                        },
                    },
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "notifications/initialized":
                continue

            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": TOOLS_DEFINITION,
                    },
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                try:
                    result_data = handle_tool_call(engine, tool_name, tool_args)
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result_data, indent=2),
                                }
                            ]
                        },
                    }
                except Exception as e:
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                            "isError": True,
                        },
                    }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "ping":
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method {method} not found"},
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

        except Exception as e:
            logger.error(f"MCP server loop error: {e}")


if __name__ == "__main__":
    run_mcp_server()
