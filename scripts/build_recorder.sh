#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/outlook_plugin/bin/Outlook Recorder.app"
mkdir -p "$APP/Contents/MacOS" "$ROOT/build/recorder-cache"
xcrun swiftc -module-cache-path "$ROOT/build/recorder-cache" -target arm64-apple-macosx14.0 -O "$ROOT/scripts/mac_recorder.swift" -o "$APP/Contents/MacOS/Outlook Recorder"
python3 - "$APP/Contents/Info.plist" <<'PY'
import plistlib,sys
from pathlib import Path
Path(sys.argv[1]).write_bytes(plistlib.dumps(dict(CFBundleExecutable='Outlook Recorder',CFBundleIdentifier='com.brettscharm.outlookassistant.recorder',CFBundleName='Outlook Recorder',CFBundlePackageType='APPL',CFBundleVersion='1',CFBundleShortVersionString='1.0',LSMinimumSystemVersion='14.0',LSUIElement=True,NSMicrophoneUsageDescription='Record your voice with call audio when you choose Start recording.',NSScreenCaptureUsageDescription='Record the screen or call audio you choose using the macOS sharing picker.')))
PY
codesign --force --deep --sign "${SIGNING_IDENTITY:--}" "$APP"
codesign --verify --deep --strict "$APP"
