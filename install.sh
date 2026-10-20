#!/usr/bin/env bash
set -e

# One-Line Installer for Outlook Assistant on macOS
# Usage: curl -fsSL https://raw.githubusercontent.com/brettscharm/outlook-assistant/main/install.sh | bash

REPO_URL="https://github.com/brettscharm/outlook-assistant.git"
INSTALL_DIR="$HOME/.outlook-assistant"
BIN_DIR="$HOME/.local/bin"

echo "=============================================="
echo "📬 Installing Outlook Assistant for macOS..."
echo "=============================================="

# 1. Verify macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "❌ Error: This installer is intended for macOS."
    exit 1
fi

# 2. Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required. Please install Python 3 first."
    exit 1
fi

# 3. Clone or Update Repository
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "🔄 Existing installation detected. Updating..."
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    echo "📥 Downloading Outlook Assistant..."
    rm -rf "$INSTALL_DIR"
    if command -v git &> /dev/null; then
        git clone "$REPO_URL" "$INSTALL_DIR"
    else
        mkdir -p "$INSTALL_DIR"
        curl -fsSL "https://github.com/brettscharm/outlook-assistant/archive/refs/heads/main.tar.gz" | tar -xz -C "$INSTALL_DIR" --strip-components=1
    fi
fi

cd "$INSTALL_DIR"

# 4. Set up CLI executable
mkdir -p "$BIN_DIR"
WRAPPER="$BIN_DIR/outlook-assistant"

cat <<EOF > "$WRAPPER"
#!/usr/bin/env bash
PYTHONPATH="$INSTALL_DIR" python3 -m outlook_plugin.cli "\$@"
EOF
chmod +x "$WRAPPER"

# 5. Configure Shell PATH if needed
SHELL_RC="$HOME/.zshrc"
if [[ "$SHELL" == *"bash"* ]]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    export PATH="$BIN_DIR:$PATH"
fi

# 6. Configure LaunchAgent for Auto-run on Startup
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/com.user.outlook-assistant.plist"
mkdir -p "$PLIST_DIR"

cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.outlook-assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>-m</string>
        <string>outlook_plugin.cli</string>
        <string>briefing</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$INSTALL_DIR</string>
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

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH" 2>/dev/null || true

# 7. Fire initial installation telemetry ping
PYTHONPATH="$INSTALL_DIR" python3 -c "from outlook_plugin.telemetry import track_event; track_event('install')" 2>/dev/null || true

echo "=============================================="
echo "✅ Outlook Assistant installed successfully!"
echo "=============================================="
echo "• Command: 'outlook-assistant briefing'"
echo "• Auto-run: Configured at startup (/tmp/outlook-assistant.log)"
echo "• Auto-updates: Automatic git synchronization on run"
echo ""
echo "Try running: outlook-assistant briefing"
