#!/usr/bin/env bash
# Double-click this file in macOS Finder to launch the Outlook Assistant app anytime!

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="$DIR" python3 -m outlook_plugin.cli app
