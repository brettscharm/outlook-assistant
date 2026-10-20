# 📬 Outlook Assistant (Mac App & AI Intelligence)

A fast, lightweight, and local AI assistant for **Microsoft Outlook** on macOS. Powered by your **Bob API Key**, it reads your emails, tracks upcoming meetings, manages two-column to-do lists, drafts calendar-aware smart replies, and delivers executive morning briefings.

---

## 🚀 Quick Setup (3 Simple Steps)

### Step 1: Download & Unzip
1. Click the green button above: **Code** → **[Download ZIP](https://github.com/brettscharm/outlook-assistant/archive/refs/heads/main.zip)**.
2. Double-click the downloaded `.zip` file in your **Downloads** folder to unzip it.

---

### Step 2: Open Terminal & Run
1. Open **Terminal** on your Mac (press <kbd>Cmd</kbd> + <kbd>Space</kbd>, type `Terminal`, and hit <kbd>Enter</kbd>).
2. Type `cd` followed by a space, then drag the unzipped folder into your Terminal window (or run):
   ```bash
   cd ~/Downloads/outlook-assistant-main
   ```
3. Run the start command:
   ```bash
   ./run.sh
   ```

*The app will automatically launch and open `http://localhost:8484` in your browser!*

---

### Step 3: Connect Your Bob API Key
1. In the top right corner of the dashboard, click **⚙️ Settings & API Key**.
2. Grab your key from **[bob.ibm.com/admin/apikeys](https://bob.ibm.com/admin/apikeys)**.
3. Paste your key (`bob_prod_...`) and click **Save & Connect**.

*Done! Your Outlook emails, calendar timeline, and task board will sync immediately.*

---

## 🌟 What You Can Do in the App

| Feature | Description |
| :--- | :--- |
| 📬 **Full Outlook Inbox** | Browse all your emails across all folders with instant search and reading pane. |
| 📅 **Calendar Schedule** | View upcoming meetings, locations, and conflict detection. |
| ✨ **Calendar-Aware Smart Reply** | Select an email, click **Generate Draft**, and Bob AI writes a contextual reply that automatically checks your real schedule. |
| ✅ **Interactive Task Board** | Separate **Your Tasks (To Do)** from **Others' Tasks (Waiting On)** with real-time checkboxes and local persistence. |
| ☀️ **Light / Dark Mode** | Crisp Light Mode enabled by default with a ☀️ / 🌙 theme switcher in the navbar. |
| 🔄 **Auto-Updates** | The app automatically checks GitHub and pulls the latest updates in the background. |

---

## 🔄 Re-Opening the App Later

Whenever you want to launch the app again, just run:
```bash
cd ~/Downloads/outlook-assistant-main && ./run.sh
```
*(Or double-click **`Launch Outlook Assistant.command`** in the folder).*

---

## 🔒 100% Local & Private
- All emails and calendar events are read directly on your Mac through native macOS Automation.
- No personal data or email contents are sent to external databases or servers.
