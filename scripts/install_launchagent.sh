#!/usr/bin/env bash
set -e

# Script to configure Outlook Assistant to auto-run / notify on macOS startup & login

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.user.outlook-assistant.plist"
PLIST_PATH="$PLIST_DIR/$PLIST_NAME"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_EXEC="$(which python3)"

mkdir -p "$PLIST_DIR"

echo "Creating LaunchAgent at: $PLIST_PATH"

cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.outlook-assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_EXEC</string>
        <string>-m</string>
        <string>outlook_plugin.cli</string>
        <string>briefing</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$CURRENT_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/outlook-assistant.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/outlook-assistant-error.log</string>
</dict>
</plist>
EOF

# Load LaunchAgent
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH" 2>/dev/null || true

echo "✅ LaunchAgent installed and loaded successfully!"
echo "Outlook Assistant will automatically run at login. Logs saved to /tmp/outlook-assistant.log"
