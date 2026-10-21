#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/build/mcp"
for ARCH in arm64 x86_64; do
 xcrun swiftc -module-cache-path "$ROOT/build/mcp/module-cache" -target "$ARCH-apple-macosx13.0" -O "$ROOT/scripts/mcp_bridge.swift" -o "$ROOT/build/mcp/bridge-$ARCH"
done
lipo -create "$ROOT/build/mcp/bridge-arm64" "$ROOT/build/mcp/bridge-x86_64" -output "$ROOT/outlook_plugin/bin/outlook-mcp-darwin"
codesign --force --sign - "$ROOT/outlook_plugin/bin/outlook-mcp-darwin"
