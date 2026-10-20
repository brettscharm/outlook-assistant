#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${PYTHON:=python3}"
: "${OUTPUT:=$ROOT/dist}"
"$PYTHON" -m PyInstaller --noconfirm --clean --windowed --onedir \
 --name 'Outlook Assistant' --osx-bundle-identifier com.brettscharm.outlookassistant \
 --paths "$ROOT" --collect-submodules outlook_plugin \
 --add-data "$ROOT/outlook_plugin:app/outlook_plugin" \
 --distpath "$OUTPUT" --workpath "$ROOT/build/package" --specpath "$ROOT/build" \
 "$ROOT/scripts/mac_launcher.py"
