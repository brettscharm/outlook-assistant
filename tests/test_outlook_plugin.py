"""
Tests for Outlook Assistant Plugin
"""

import unittest
from unittest.mock import MagicMock, patch
from outlook_plugin.mac_bridge import MacOutlookBridge, FIELD_SEP, ITEM_SEP
from outlook_plugin.engine import OutlookEngine


class TestMacOutlookBridge(unittest.TestCase):

    def setUp(self):
        self.bridge = MacOutlookBridge()

    @patch.object(MacOutlookBridge, "_run_applescript")
    def test_list_folders_parsing(self, mock_run):
        mock_run.return_value = (
            f"Inbox{FIELD_SEP}100{FIELD_SEP}5{ITEM_SEP}"
            f"Sent Items{FIELD_SEP}50{FIELD_SEP}0{ITEM_SEP}"
        )
        folders = self.bridge.list_folders()
        self.assertEqual(len(folders), 2)
        self.assertEqual(folders[0]["name"], "Inbox")
        self.assertEqual(folders[0]["total_messages"], 100)
        self.assertEqual(folders[0]["unread_messages"], 5)
        self.assertEqual(folders[1]["name"], "Sent Items")

    @patch.object(MacOutlookBridge, "_run_applescript")
    def test_get_emails_parsing(self, mock_run):
        mock_run.return_value = (
            f"101{FIELD_SEP}Project Roadmap{FIELD_SEP}Alice <alice@example.com>{FIELD_SEP}2025-05-10 09:30:00{FIELD_SEP}false{FIELD_SEP}Here is the Q2 plan...{ITEM_SEP}"
            f"102{FIELD_SEP}Urgent Review{FIELD_SEP}Bob <bob@example.com>{FIELD_SEP}2025-05-10 10:15:00{FIELD_SEP}true{FIELD_SEP}Please review the doc.{ITEM_SEP}"
        )
        emails = self.bridge.get_emails(limit=10)
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0]["id"], "101")
        self.assertEqual(emails[0]["subject"], "Project Roadmap")
        self.assertFalse(emails[0]["is_read"])
        self.assertEqual(emails[1]["id"], "102")
        self.assertTrue(emails[1]["is_read"])

    @patch.object(MacOutlookBridge, "_run_applescript")
    def test_get_upcoming_events_parsing(self, mock_run):
        mock_run.return_value = (
            f"ev-1{FIELD_SEP}Sprint Retrospective{FIELD_SEP}Thursday, May 15, 2025 2:00:00 PM{FIELD_SEP}Thursday, May 15, 2025 3:00:00 PM{FIELD_SEP}Room 4B{FIELD_SEP}false{FIELD_SEP}true{FIELD_SEP}Discuss sprint deliverables{ITEM_SEP}"
        )
        events = self.bridge.get_upcoming_events(days_ahead=7)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["subject"], "Sprint Retrospective")
        self.assertEqual(events[0]["location"], "Room 4B")
        self.assertFalse(events[0]["is_all_day"])
        self.assertTrue(events[0]["is_recurring"])

    @patch.object(MacOutlookBridge, "get_upcoming_events")
    @patch.object(MacOutlookBridge, "get_emails")
    def test_daily_briefing(self, mock_get_emails, mock_get_events):
        mock_get_events.return_value = [
            {"id": "1", "subject": "Quarterly Kickoff", "start_time": "10:00 AM", "location": "Boardroom"}
        ]
        mock_get_emails.return_value = [
            {"id": "2", "subject": "URGENT: Budget Approval Needed", "sender": "Finance <fin@example.com>", "is_read": False},
            {"id": "3", "subject": "Newsletter issue 42", "sender": "News <news@example.com>", "is_read": False},
        ]

        engine = OutlookEngine(prefer_mac=True)
        briefing = engine.get_daily_briefing()

        self.assertEqual(briefing["upcoming_events_count"], 1)
        self.assertEqual(briefing["unread_emails_count"], 2)
        self.assertEqual(len(briefing["urgent_emails"]), 1)
        self.assertEqual(briefing["urgent_emails"][0]["subject"], "URGENT: Budget Approval Needed")
        self.assertEqual(len(briefing["recent_unread_emails"]), 1)


if __name__ == "__main__":
    unittest.main()
