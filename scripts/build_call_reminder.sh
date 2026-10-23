#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/outlook_plugin/bin/Outlook Call Reminder.app"
mkdir -p "$APP/Contents/MacOS" "$ROOT/build/reminder-cache"
xcrun swiftc -module-cache-path "$ROOT/build/reminder-cache" -target arm64-apple-macosx14.0 -O "$ROOT/scripts/mac_call_reminder.swift" -o "$APP/Contents/MacOS/Outlook Call Reminder"
python3 - "$APP/Contents/Info.plist" <<'PY'
import plistlib,sys
from pathlib import Path
Path(sys.argv[1]).write_bytes(plistlib.dumps(dict(CFBundleExecutable='Outlook Call Reminder',CFBundleIdentifier='com.brettscharm.outlookassistant.callreminder',CFBundleName='Outlook Call Reminder',CFBundlePackageType='APPL',CFBundleVersion='1',CFBundleShortVersionString='1.0',LSMinimumSystemVersion='14.2',LSUIElement=True)))
PY
codesign --force --deep --sign "${SIGNING_IDENTITY:--}" "$APP"
codesign --verify --deep --strict "$APP"
