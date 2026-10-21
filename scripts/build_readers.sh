#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
(cd "$ROOT/vendor/hxmail" && GOOS=darwin GOARCH=arm64 CGO_ENABLED=0 go build -trimpath -o "$STAGING/hxmail-darwin" ./cmd/hxmail)
(cd "$ROOT/vendor/teams-calendar" && GOOS=darwin GOARCH=arm64 CGO_ENABLED=0 go build -trimpath -o "$STAGING/teams-calendar-darwin" ./cmd/calendar)
for HELPER in hxmail teams-calendar; do
 cp "$STAGING/$HELPER-darwin" "$ROOT/outlook_plugin/bin/$HELPER-darwin"
 codesign --force --sign - "$ROOT/outlook_plugin/bin/$HELPER-darwin"
done
