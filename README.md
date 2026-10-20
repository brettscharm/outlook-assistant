# 📬 Outlook Assistant (Email & Calendar Intelligence App)

A zero-friction, self-updating local app and MCP plugin for macOS that connects directly to **Microsoft Outlook** on your computer. Powered by your **Bob API Key**, it reads your emails, tracks upcoming meetings, drafts calendar-aware smart replies, and delivers executive briefings.

---

## 🌟 Features

- 🧠 **Bob AI Key Powered**: Pop in your Bob API key once and let Bob's AI engine handle email synthesis, action item extraction, and smart reply drafting.
- 📅 **Calendar & Schedule Awareness**: Queries upcoming meetings, flags scheduling conflicts, and finds free slots.
- ✍️ **Calendar-Aware Smart Replies**: Drafts email replies that automatically reference your actual real-time availability (e.g. agreeing to meet, proposing open times).
- 🚨 **Priority Triage**: Detects urgent messages, deadlines, and questions awaiting your feedback.
- 💻 **Interactive Local Web Dashboard**: Beautiful dashboard at `http://localhost:8484` to view your calendar timeline, triage emails, and generate replies in 1 click.
- 🔔 **Background Watcher & macOS Notifications**: Native macOS banner alerts for urgent emails and meeting reminders.
- 🔄 **Auto-Updating via GitHub**: Automatically syncs the latest version from your GitHub repository with zero maintenance for users.
- 📊 **Usage Telemetry**: Tracks active users and installations to your Discord/Slack webhook.
- 🤖 **Native MCP Server**: Can be called on-demand by Bob, Claude Desktop, Cursor, and any LLM tool.

---

## 🚀 1-Line Installation for Macs

Anyone can install and start the app with a single terminal command:

```bash
curl -fsSL https://raw.githubusercontent.com/brettscharm/outlook-assistant/main/install.sh | bash
```

This automatically:
1. Downloads the repository to `~/.outlook-assistant`
2. Creates the global `outlook-assistant` CLI command
3. Sets up auto-start at login via macOS LaunchAgent
4. Launches the local dashboard and prompts for the Bob API key

---

## 🛠️ Usage

### 1. Launch the Web Dashboard
```bash
outlook-assistant app
# Opens http://localhost:8484 in your browser
```

### 2. Run the Background Notification Daemon
```bash
outlook-assistant daemon
```

### 3. CLI Commands
```bash
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

## 🤖 Using with Bob as an MCP Server

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
