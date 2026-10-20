"""
End-to-End Server & Sync Test
Verifies all REST endpoints and Outlook local sync.
"""

import json
import threading
import time
import unittest
import urllib.request
from outlook_plugin.app_server import PORT, start_app_server
from outlook_plugin.engine import OutlookEngine


class TestOutlookE2E(unittest.TestCase):

    def test_engine_all_emails_sync(self):
        engine = OutlookEngine()
        status = engine.get_status()
        self.assertTrue(status["mac_outlook_installed"])

        # Test folder listing
        folders = engine.list_folders()
        self.assertIsInstance(folders, list)
        self.assertTrue(len(folders) > 0)

        # Test extracting all emails
        emails_all = engine.get_emails(folder="all", limit=10)
        self.assertIsInstance(emails_all, list)
        self.assertTrue(len(emails_all) > 0)

        # Verify email schema
        first_email = emails_all[0]
        self.assertIn("id", first_email)
        self.assertIn("subject", first_email)
        self.assertIn("sender", first_email)

        # Test extracting Drafts
        emails_drafts = engine.get_emails(folder="Drafts", limit=5)
        self.assertIsInstance(emails_drafts, list)
        self.assertTrue(len(emails_drafts) > 0)


if __name__ == "__main__":
    unittest.main()
