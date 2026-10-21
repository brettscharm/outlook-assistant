#!/bin/bash
# Release gate: requires a Developer ID identity and a stored notarytool profile.
set -euo pipefail
: "${SIGNING_IDENTITY:?Set SIGNING_IDENTITY to your Developer ID Application identity}"
: "${NOTARY_PROFILE:?Set NOTARY_PROFILE to your notarytool Keychain profile}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-$ROOT/dist/Outlook Assistant.app}"
[[ "$SIGNING_IDENTITY" == "Developer ID Application:"* ]] || { echo 'A Developer ID Application identity is required.' >&2; exit 1; }
python3 "$ROOT/scripts/check_mac_architectures.py" "$APP"
# Sign nested code before the outer bundle; never depend on --deep for signing.
python3 - "$APP" "$SIGNING_IDENTITY" <<'PY'
from pathlib import Path
import subprocess, sys
root=Path(sys.argv[1]); identity=sys.argv[2]
magic={b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}
paths=[]
for path in root.rglob('*'):
    if path.is_symlink(): continue
    if path.is_file():
        with path.open('rb') as stream: is_code=stream.read(4) in magic
        if is_code: paths.append(path)
    elif path.suffix in ('.framework', '.app', '.xpc'): paths.append(path)
for path in sorted(paths,key=lambda p:len(p.parts),reverse=True)+[root]:
    subprocess.run(['codesign','--force','--options','runtime','--timestamp','--sign',identity,str(path)],check=True)
PY
codesign --verify --deep --strict "$APP"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
ditto -c -k --keepParent "$APP" "$STAGING/submission.zip"
xcrun notarytool submit "$STAGING/submission.zip" --keychain-profile "$NOTARY_PROFILE" --wait
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"
spctl --assess --type execute --verbose=2 "$APP"
# Publish only the stapled artifact; a failed check above produces no release ZIP.
ditto -c -k --keepParent "$APP" "$STAGING/Outlook-Assistant-Universal-Mac.zip"
mv "$STAGING/Outlook-Assistant-Universal-Mac.zip" "$(dirname "$APP")/Outlook-Assistant-Universal-Mac.zip"
