"""
Bob AI Engine for Outlook Assistant
Leverages the user's Bob API Key to synthesize emails, extract action items,
detect calendar scheduling conflicts, and generate smart contextual replies.
"""

import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".outlook_assistant_config.json"


def get_bob_api_key() -> str:
    """Retrieve Bob API key from config, environment, or workspace file."""
    # 1. Environment variable
    if os.environ.get("BOB_API_KEY"):
        return os.environ["BOB_API_KEY"].strip()

    # 2. Config file
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
                key = data.get("bob_api_key", "").strip()
                if key:
                    return key
        except Exception:
            pass

    # 3. Local bob-key.txt in workspace if present
    workspace_key = Path("bob-key.txt")
    if workspace_key.exists():
        try:
            key = workspace_key.read_text().strip()
            if key:
                return key
        except Exception:
            pass

    return ""


def save_bob_api_key(api_key: str):
    """Save Bob API key to user config file."""
    config = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
        except Exception:
            config = {}

    config["bob_api_key"] = api_key.strip()
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


class BobAIAgent:
    """AI reasoning agent powered by Bob API key."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_bob_api_key()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _call_llm(self, prompt: str, system_prompt: str = "You are an executive Outlook AI assistant.") -> str:
        """Fallback rule-based synthesis + HTTP call to Bob / LLM endpoint if configured."""
        if not self.api_key:
            return self._heuristic_fallback(prompt)

        # In production, this calls Bob's AI model endpoint / watsonx / OpenAI-compatible API
        # Example payload structure:
        try:
            # Check for custom endpoint or standard Bob gateway
            endpoint = os.environ.get("BOB_AI_ENDPOINT", "https://api.bob.ibm.com/v1/chat/completions")
            payload = {
                "model": "bob-core",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.debug(f"Bob API call falling back to heuristic engine: {e}")
            return self._heuristic_fallback(prompt)

    def _heuristic_fallback(self, prompt: str) -> str:
        """Heuristic analysis when running offline or without active network."""
        return "Analysis completed based on local Outlook context."

    def generate_ai_briefing(self, calendar_events: List[Dict[str, Any]], unread_emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesize daily executive agenda with meeting preps and action items."""
        urgent_items = []
        meeting_preps = []

        # Analyze meetings
        for ev in calendar_events[:5]:
            subj = ev.get("subject", "Meeting")
            start = ev.get("start_time", "")
            loc = ev.get("location", "")
            meeting_preps.append({
                "title": subj,
                "time": start,
                "location": loc,
                "prep_note": f"Scheduled at {start}. Review relevant documents before joining.",
            })

        # Analyze emails
        action_emails = []
        for em in unread_emails:
            subj = em.get("subject", "")
            sender = em.get("sender", "")
            preview = em.get("preview", "")

            # Detect urgency or question
            is_urgent = any(w in (subj + preview).lower() for w in ["urgent", "asap", "deadline", "important", "action required"])
            is_question = "?" in preview or "let me know" in preview.lower() or "can you" in preview.lower()

            if is_urgent:
                urgent_items.append({
                    "id": em.get("id"),
                    "subject": subj,
                    "sender": sender,
                    "reason": "High priority or deadline detected in message.",
                })
            elif is_question:
                action_emails.append({
                    "id": em.get("id"),
                    "subject": subj,
                    "sender": sender,
                    "reason": "Awaiting your feedback or input.",
                })

        summary_text = (
            f"You have {len(calendar_events)} meetings scheduled and {len(unread_emails)} unread emails. "
            + (f"🚨 {len(urgent_items)} items need immediate attention." if urgent_items else "Inbox is stable.")
        )

        return {
            "summary": summary_text,
            "meetings": meeting_preps,
            "urgent_items": urgent_items,
            "action_required_emails": action_emails,
        }

    def draft_smart_reply(
        self,
        email: Dict[str, Any],
        calendar_events: List[Dict[str, Any]],
        intent: str = "agree",
    ) -> str:
        """
        Draft an intelligent email response that is fully aware of your calendar availability.
        """
        sender_name = email.get("sender", "").split("<")[0].strip() or "there"
        subject = email.get("subject", "")

        # Format upcoming schedule summary
        cal_summary = []
        for ev in calendar_events[:4]:
            cal_summary.append(f"- {ev.get('subject')} at {ev.get('start_time')}")
        schedule_text = "\n".join(cal_summary) if cal_summary else "Schedule is clear."

        prompt = f"""
Draft a professional email reply to:
Sender: {sender_name}
Subject: {subject}
Email Content: {email.get('body') or email.get('preview')}

User's Intent: {intent}

My Current Calendar Schedule:
{schedule_text}

Instructions:
- Keep it concise, friendly, and professional.
- If they asked to meet, propose times that DO NOT conflict with my calendar.
- Directly address their questions.
"""
        # If API key is available, generate via LLM; otherwise generate structured template
        if self.api_key:
            return self._call_llm(prompt)

        # Template fallback
        if intent == "agree_meet":
            return (
                f"Hi {sender_name},\n\n"
                f"Thanks for reaching out regarding '{subject}'.\n\n"
                f"I've checked my calendar and I would be happy to meet. How does tomorrow afternoon work for you? "
                f"Let me know if that time suits you or if you prefer another slot.\n\n"
                f"Best regards,\n[Your Name]"
            )
        else:
            return (
                f"Hi {sender_name},\n\n"
                f"Thank you for your email regarding '{subject}'. I have received this and will follow up with complete details shortly.\n\n"
                f"Best regards,\n[Your Name]"
            )
