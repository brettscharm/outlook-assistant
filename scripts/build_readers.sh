#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
for ARCH in arm64 amd64; do
 (cd "$ROOT/vendor/hxmail" && GOOS=darwin GOARCH="$ARCH" CGO_ENABLED=0 go build -trimpath -o "$STAGING/hxmail-$ARCH" ./cmd/hxmail)
done
lipo -create "$STAGING/hxmail-arm64" "$STAGING/hxmail-amd64" -output "$ROOT/outlook_plugin/bin/hxmail-darwin"
codesign --force --sign - "$ROOT/outlook_plugin/bin/hxmail-darwin"
