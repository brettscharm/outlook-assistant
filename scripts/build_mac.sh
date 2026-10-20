#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${PYTHON:=python3}"
: "${OUTPUT:=$ROOT/dist}"
"$PYTHON" -m PyInstaller --noconfirm --clean --windowed --onedir --target-arch "${TARGET_ARCH:-universal2}" \
 --name 'Outlook Assistant' --osx-bundle-identifier com.brettscharm.outlookassistant \
 --paths "$ROOT" --collect-submodules outlook_plugin \
 --add-data "$ROOT/outlook_plugin:app/outlook_plugin" \
 --distpath "$OUTPUT" --workpath "$ROOT/build/package" --specpath "$ROOT/build" \
 "$ROOT/scripts/mac_launcher.py"

"$PYTHON" - "$OUTPUT/Outlook Assistant.app/Contents/Info.plist" "$ROOT/outlook_plugin/__init__.py" <<'PYINFO'
import plistlib,re,sys
from pathlib import Path
path=Path(sys.argv[1]);info=plistlib.loads(path.read_bytes())
version=re.search(r'__version__ = "([0-9.]+)"',Path(sys.argv[2]).read_text())[1]
info.update(LSMinimumSystemVersion='13.0',CFBundleShortVersionString=version,CFBundleVersion=version)
path.write_bytes(plistlib.dumps(info))
PYINFO
# Keep the bundled Python service behind a native Cocoa/WebKit window.
mv "$OUTPUT/Outlook Assistant.app/Contents/MacOS/Outlook Assistant" "$OUTPUT/Outlook Assistant.app/Contents/MacOS/Outlook Assistant Service"
NATIVE_BUILD="$ROOT/build/native-window"
mkdir -p "$NATIVE_BUILD"
for ARCH in arm64 x86_64; do
 xcrun swiftc -module-cache-path "$NATIVE_BUILD/module-cache" -target "$ARCH-apple-macosx13.0" -O "$ROOT/scripts/mac_window.swift" -o "$NATIVE_BUILD/window-$ARCH"
done
lipo -create "$NATIVE_BUILD/window-arm64" "$NATIVE_BUILD/window-x86_64" -output "$OUTPUT/Outlook Assistant.app/Contents/MacOS/Outlook Assistant"
codesign --force --deep --sign "${SIGNING_IDENTITY:--}" "$OUTPUT/Outlook Assistant.app"
codesign --verify --deep --strict "$OUTPUT/Outlook Assistant.app"
