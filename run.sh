#!/usr/bin/env bash
# Outlook Assistant Simple Launcher
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
xattr -cr "$DIR" 2>/dev/null || true
PYTHONPATH="$DIR" python3 -m outlook_plugin.cli app
