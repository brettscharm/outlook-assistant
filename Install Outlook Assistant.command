#!/usr/bin/env bash
# Double-click this file in macOS Finder to install Outlook Assistant with 0 typing!

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "========================================================"
echo "📬 Setting up Outlook Assistant on your Mac..."
echo "========================================================"

chmod +x ./install.sh
./install.sh

echo ""
echo "🚀 Launching Outlook Assistant Dashboard..."
PYTHONPATH="$DIR" python3 -m outlook_plugin.cli app
