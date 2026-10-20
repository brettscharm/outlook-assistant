#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for ARCH in arm64 amd64; do
 (cd "$ROOT/vendor/hxmail" && GOOS=darwin GOARCH="$ARCH" CGO_ENABLED=0 go build -trimpath -o "$ROOT/outlook_plugin/bin/hxmail-darwin-$ARCH" ./cmd/hxmail)
done
