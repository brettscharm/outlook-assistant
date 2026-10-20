# 📬 Outlook Assistant (Mac App & Intelligence Engine)

A zero-friction, self-updating local app and MCP plugin for macOS that connects directly to **Microsoft Outlook** on your computer. Powered by your **Bob API Key**, it reads your emails, tracks upcoming meetings, manages two-column to-do lists, drafts calendar-aware smart replies, and delivers executive briefings.

---

## 🌟 Key Features

- 🧠 **Bob AI Key Powered**: Pop in your Bob API key once to let Bob's AI engine handle email synthesis, action item extraction, and smart reply drafting.
- 📅 **Calendar & Schedule Awareness**: Queries upcoming meetings, flags scheduling conflicts, and finds free slots.
- ✍️ **Calendar-Aware Smart Replies**: Drafts email replies that automatically reference your actual real-time availability (e.g. agreeing to meet, proposing open times).
- 📋 **Two-Column Task Board**: Interactive checklist separating **Your Tasks (To Do)** from **Others' Tasks (Waiting On)** with persistent local storage.
- 📧 **Multi-Account Filter**: Switch between **All Accounts**, **Work (Exchange)**, and **Personal (IMAP)**.
- 🚨 **Priority Email Triage**: Detects urgent messages, deadlines, and questions awaiting your feedback.
- 💻 **Interactive Local Web Dashboard**: Beautiful dashboard at `http://localhost:8484` to view your calendar timeline, triage emails, manage tasks, and generate replies in 1 click.
- 🔔 **Background Watcher & macOS Notifications**: Native macOS banner alerts for urgent emails and meeting reminders.
- 🔄 **Auto-Updating via GitHub**: Automatically syncs the latest version from your GitHub repository with zero maintenance for users.
- 🤖 **Native MCP Server**: Can be called on-demand by Bob, Claude Desktop, Cursor, and any LLM tool.

---

## 📦 Simple Installation Options

### Option 1: Double-Click Mac App (No Terminal / 0 Code)

1. Download the repository from GitHub: Click **Code** → **[Download ZIP](https://github.com/brettscharm/outlook-assistant/archive/refs/heads/main.zip)**.
2. Unzip the downloaded file.
3. **Double-click `Outlook Assistant.app`** (or `Install Outlook Assistant.command`).

*The app will automatically launch, set up auto-start across restarts, and open the dashboard at `http://localhost:8484` in your browser.*

> **First-Time Mac Security Note ("Cannot verify developer" / Gatekeeper):**
> 1. Right-click (or Control-click) `Outlook Assistant.app` and choose **Open**.
> 2. Alternatively, go to **System Settings → Privacy & Security**, scroll down to Security, and click **Open Anyway**.

---

### Option 2: 1-Line Terminal Install

Open Terminal and paste:

```bash
curl -fsSL https://raw.githubusercontent.com/brettscharm/outlook-assistant/main/install.sh | bash
```

This automatically:
1. Downloads the app to `~/.outlook-assistant`
2. Creates the global `outlook-assistant` terminal command
3. Configures auto-start on macOS boot
4. Launches the local dashboard at `http://localhost:8484`

---

## 🚀 Getting Started

1. When the dashboard opens at `http://localhost:8484`, click **⚙️ Settings & API Key** in the top right.
2. Get your Bob API Key from **[bob.ibm.com/admin/apikeys](https://bob.ibm.com/admin/apikeys)**.
3. Paste your key (`bob_prod_...`) into the app and click **Save & Connect**.
4. Your local Outlook inbox, calendar timeline, and task board will sync immediately!

---

## 🛠️ CLI Commands (Optional)

```bash
# Launch the Web Dashboard manually
outlook-assistant app

# View Executive Morning Briefing
outlook-assistant briefing

# Check upcoming calendar schedule
outlook-assistant calendar --days 7

# List unread emails
outlook-assistant emails --unread

# Unified search across emails and calendar
outlook-assistant search "Project Roadmap"

# Check & pull latest GitHub updates
outlook-assistant update
```

---

## 🤖 Using with Bob / Claude as an MCP Server

Add this to your MCP configuration (`~/.bob/mcp.json`):

```json
{
  "mcpServers": {
    "outlook-assistant": {
      "command": "python3",
      "args": ["-m", "outlook_plugin.cli", "mcp"],
      "cwd": "/Users/brettscharmett/.bob/playground/outlook-assistant-plugin"
    }
  }
}
```

---

## 🔒 Permissions & Privacy

- **100% Local & Private**: Your emails and calendar events are read directly on your Mac using native macOS Automation (`osascript`). No email data is sent to external databases or servers.
- **macOS Automation Prompt**: When running for the first time, macOS may ask for permission to control Microsoft Outlook. Click **OK**, or verify in:
  **System Settings → Privacy & Security → Automation → Microsoft Outlook (Checked)**.
