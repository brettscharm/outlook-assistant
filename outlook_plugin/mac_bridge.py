"""
macOS Local Outlook Bridge using AppleScript
Directly interfaces with Microsoft Outlook for Mac to read emails and calendar events.
"""

import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

FIELD_SEP = "<--FIELD_DELIM-->"
ITEM_SEP = "<--ITEM_DELIM-->"


class MacOutlookBridge:
    """Bridge to Microsoft Outlook for Mac via AppleScript."""

    def __init__(self, timeout: int = 25):
        self.timeout = timeout

    def _run_applescript(self, script: str) -> str:
        """Run an AppleScript command and return the stdout string."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            if result.returncode != 0:
                err = result.stderr.strip()
                logger.warning(f"AppleScript error (code {result.returncode}): {err}")
                return ""
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"AppleScript timed out after {self.timeout}s")
            return ""
        except Exception as e:
            logger.error(f"Failed to execute AppleScript: {e}")
            return ""

    def is_available(self) -> bool:
        """Check if Microsoft Outlook is installed on this Mac."""
        out = self._run_applescript('id of application "Microsoft Outlook"')
        return "com.microsoft.Outlook" in out

    def is_running(self) -> bool:
        """Check if Microsoft Outlook application process is currently active."""
        script = """
        tell application "System Events"
            return (count of (every process whose bundle identifier is "com.microsoft.Outlook")) > 0
        end tell
        """
        out = self._run_applescript(script)
        return out.lower() == "true"

    def list_accounts(self) -> List[Dict[str, Any]]:
        """List configured email accounts in Outlook."""
        script = f"""
        tell application "Microsoft Outlook"
            set accList to {{}}
            try
                repeat with acc in (every exchange account)
                    set end of accList to ("Exchange" & "{FIELD_SEP}" & (name of acc) & "{FIELD_SEP}" & (email address of acc as text))
                end repeat
                repeat with acc in (every imap account)
                    set end of accList to ("IMAP" & "{FIELD_SEP}" & (name of acc) & "{FIELD_SEP}" & (email address of acc as text))
                end repeat
                repeat with acc in (every pop account)
                    set end of accList to ("POP" & "{FIELD_SEP}" & (name of acc) & "{FIELD_SEP}" & (email address of acc as text))
                end repeat
            end try
            
            set AppleScript's text item delimiters to "{ITEM_SEP}"
            return accList as text
        end tell
        """
        raw = self._run_applescript(script)
        accounts = [{"type": "All", "name": "All Accounts", "email": "all"}]
        if not raw:
            return accounts

        for item in raw.split(ITEM_SEP):
            if not item.strip():
                continue
            parts = item.split(FIELD_SEP)
            if len(parts) >= 3:
                accounts.append({
                    "type": parts[0].strip(),
                    "name": parts[1].strip(),
                    "email": parts[2].strip() or parts[1].strip(),
                })
        return accounts

    def list_folders(self) -> List[Dict[str, Any]]:
        """List all available mail folders in Outlook."""
        script = f"""
        tell application "Microsoft Outlook"
            set folderList to {{}}
            try
                set fList to every mail folder
                repeat with f in fList
                    set fName to name of f
                    set fCount to count of messages of f
                    set fUnread to count of (messages of f whose is read is false)
                    set end of folderList to (fName & "{FIELD_SEP}" & fCount & "{FIELD_SEP}" & fUnread)
                end repeat
            end try
            
            set AppleScript's text item delimiters to "{ITEM_SEP}"
            return folderList as text
        end tell
        """
        raw = self._run_applescript(script)
        folders = [
            {"name": "Inbox", "total_messages": 0, "unread_messages": 0},
            {"name": "Sent Items", "total_messages": 0, "unread_messages": 0},
            {"name": "Drafts", "total_messages": 0, "unread_messages": 0},
            {"name": "Archive", "total_messages": 0, "unread_messages": 0},
            {"name": "Deleted Items", "total_messages": 0, "unread_messages": 0},
        ]
        if not raw:
            return folders

        ret = []
        for item in raw.split(ITEM_SEP):
            if not item.strip():
                continue
            parts = item.split(FIELD_SEP)
            if len(parts) >= 3:
                ret.append({
                    "name": parts[0].strip(),
                    "total_messages": int(parts[1].strip() or "0"),
                    "unread_messages": int(parts[2].strip() or "0"),
                })
        return ret if ret else folders

    def get_emails(
        self,
        folder: str = "inbox",
        limit: int = 50,
        unread_only: bool = False,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read emails from a specified folder (e.g. 'inbox', 'Drafts', 'all').
        """
        filter_clause = "whose is read is false" if unread_only else ""
        
        if folder.lower() in ["all", "all mail"]:
            target_source = "every message"
        elif folder.lower() == "inbox":
            target_source = "messages of inbox"
        else:
            target_source = f'messages of (mail folder "{folder}")'

        script = f"""
        tell application "Microsoft Outlook"
            set msgOutput to {{}}
            try
                set msgList to ({target_source} {filter_clause})
                set maxCount to {limit}
                if (count of msgList) < maxCount then
                    set maxCount to (count of msgList)
                end if
                
                repeat with i from 1 to maxCount
                    set m to item i of msgList
                    try
                        set mId to (id of m) as text
                    on error
                        set mId to (i as text)
                    end try
                    
                    try
                        set mSubj to subject of m
                        if mSubj is "" or mSubj is missing value then set mSubj to "(No Subject)"
                    on error
                        set mSubj to "(No Subject)"
                    end try
                    
                    try
                        set sndr to sender of m
                        set mSender to (name of sndr as text) & " <" & (address of sndr as text) & ">"
                    on error
                        try
                            set mSender to (address of (sender of m) as text)
                        on error
                            set mSender to "Outlook User"
                        end try
                    end try
                    
                    try
                        set mDate to (time received of m) as text
                    on error
                        try
                            set mDate to (time sent of m) as text
                        on error
                            set mDate to "Recent"
                        end try
                    end try
                    
                    try
                        set mRead to (is read of m) as text
                    on error
                        set mRead to "true"
                    end try
                    
                    try
                        set mContent to (plain text content of m)
                        if length of mContent > 300 then
                            set mPreview to text 1 thru 300 of mContent
                        else
                            set mPreview to mContent
                        end if
                    on error
                        set mPreview to ""
                    end try
                    
                    set cleanedPreview to my replaceText(mPreview, "\\n", " ")
                    set end of msgOutput to (mId & "{FIELD_SEP}" & mSubj & "{FIELD_SEP}" & mSender & "{FIELD_SEP}" & mDate & "{FIELD_SEP}" & mRead & "{FIELD_SEP}" & cleanedPreview)
                end repeat
            end try
            
            set AppleScript's text item delimiters to "{ITEM_SEP}"
            return msgOutput as text
        end tell

        on replaceText(srcText, findText, replaceWith)
            set AppleScript's text item delimiters to findText
            set textItems to text items of srcText
            set AppleScript's text item delimiters to replaceWith
            set resText to textItems as text
            set AppleScript's text item delimiters to ""
            return resText
        end replaceText
        """
        raw = self._run_applescript(script)
        if not raw:
            return []

        emails = []
        for item in raw.split(ITEM_SEP):
            if not item.strip():
                continue
            parts = item.split(FIELD_SEP)
            if len(parts) >= 6:
                email_obj = {
                    "id": parts[0].strip(),
                    "subject": parts[1].strip() or "(No Subject)",
                    "sender": parts[2].strip() or "Unknown Sender",
                    "received_time": parts[3].strip() or "Recent",
                    "is_read": parts[4].strip().lower() == "true",
                    "preview": parts[5].strip(),
                    "folder": folder.title(),
                }
                if search_term:
                    st = search_term.lower()
                    if st not in email_obj["subject"].lower() and st not in email_obj["sender"].lower() and st not in email_obj["preview"].lower():
                        continue
                emails.append(email_obj)
        return emails

    def get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full details and body content of a specific email message."""
        script = f"""
        tell application "Microsoft Outlook"
            try
                set m to message id {message_id}
                set mSubj to subject of m
                try
                    set sndr to sender of m
                    set mSender to (name of sndr as text) & " <" & (address of sndr as text) & ">"
                on error
                    set mSender to "Outlook User"
                end try
                try
                    set mDate to (time received of m) as text
                on error
                    set mDate to "Recent"
                end try
                try
                    set mRead to (is read of m) as text
                on error
                    set mRead to "true"
                end try
                try
                    set mContent to (plain text content of m)
                on error
                    set mContent to "(No text content)"
                end try
                
                return mSubj & "{FIELD_SEP}" & mSender & "{FIELD_SEP}" & mDate & "{FIELD_SEP}" & mRead & "{FIELD_SEP}" & mContent
            on error errMsg
                return "ERROR:" & errMsg
            end try
        end tell
        """
        raw = self._run_applescript(script)
        if not raw or raw.startswith("ERROR:"):
            return None

        parts = raw.split(FIELD_SEP)
        if len(parts) >= 5:
            return {
                "id": str(message_id),
                "subject": parts[0].strip() or "(No Subject)",
                "sender": parts[1].strip(),
                "received_time": parts[2].strip(),
                "is_read": parts[3].strip().lower() == "true",
                "body": parts[4].strip(),
            }
        return None

    def get_upcoming_events(
        self,
        days_ahead: int = 7,
        limit: int = 50,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch calendar events from Outlook."""
        script = f"""
        tell application "Microsoft Outlook"
            set eventOutput to {{}}
            try
                set nowTime to current date
                set endTime to nowTime + ({days_ahead} * days)
                set evList to every calendar event
                set evCount to count of evList
                set collected to 0
                
                repeat with i from 1 to evCount
                    if collected >= {limit} then
                        exit repeat
                    end if
                    
                    set ev to item i of evList
                    try
                        set sTime to (start time of ev)
                        set eTime to (end time of ev)
                        
                        if (sTime >= nowTime) and (sTime <= endTime) then
                            try
                                set evId to (id of ev) as text
                            on error
                                set evId to (i as text)
                            end try
                            
                            try
                                set evSubj to (subject of ev)
                            on error
                                set evSubj to "(No Title)"
                            end try
                            
                            try
                                set evLoc to (location of ev)
                            on error
                                set evLoc to ""
                            end try
                            
                            try
                                set evAllDay to (all day flag of ev) as text
                            on error
                                set evAllDay to "false"
                            end try
                            
                            try
                                set evRecur to (is recurring of ev) as text
                            on error
                                set evRecur to "false"
                            end try
                            
                            try
                                set evContent to (plain text content of ev)
                                if length of evContent > 200 then
                                    set evDesc to text 1 thru 200 of evContent
                                else
                                    set evDesc to evContent
                                end if
                            on error
                                set evDesc to ""
                            end try
                            
                            set sTimeStr to (sTime as text)
                            set eTimeStr to (eTime as text)
                            set cleanedDesc to my replaceText(evDesc, "\\n", " ")
                            
                            set end of eventOutput to (evId & "{FIELD_SEP}" & evSubj & "{FIELD_SEP}" & sTimeStr & "{FIELD_SEP}" & eTimeStr & "{FIELD_SEP}" & evLoc & "{FIELD_SEP}" & evAllDay & "{FIELD_SEP}" & evRecur & "{FIELD_SEP}" & cleanedDesc)
                            set collected to collected + 1
                        end if
                    end try
                end repeat
            end try
            
            set AppleScript's text item delimiters to "{ITEM_SEP}"
            return eventOutput as text
        end tell

        on replaceText(srcText, findText, replaceWith)
            set AppleScript's text item delimiters to findText
            set textItems to text items of srcText
            set AppleScript's text item delimiters to replaceWith
            set resText to textItems as text
            set AppleScript's text item delimiters to ""
            return resText
        end replaceText
        """
        raw = self._run_applescript(script)
        if not raw:
            return []

        events = []
        for item in raw.split(ITEM_SEP):
            if not item.strip():
                continue
            parts = item.split(FIELD_SEP)
            if len(parts) >= 8:
                ev_obj = {
                    "id": parts[0].strip(),
                    "subject": parts[1].strip() or "(No Title)",
                    "start_time": parts[2].strip(),
                    "end_time": parts[3].strip(),
                    "location": parts[4].strip() or "None",
                    "is_all_day": parts[5].strip().lower() == "true",
                    "is_recurring": parts[6].strip().lower() == "true",
                    "description": parts[7].strip(),
                }
                if search_term:
                    st = search_term.lower()
                    if st not in ev_obj["subject"].lower() and st not in ev_obj["location"].lower() and st not in ev_obj["description"].lower():
                        continue
                events.append(ev_obj)
        return events
