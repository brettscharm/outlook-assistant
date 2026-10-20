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
codesign --force --deep --sign "${SIGNING_IDENTITY:--}" "$OUTPUT/Outlook Assistant.app"
codesign --verify --deep --strict "$OUTPUT/Outlook Assistant.app"
