#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/build/mcp"
xcrun swiftc -module-cache-path "$ROOT/build/mcp/module-cache" -target arm64-apple-macosx13.0 -O "$ROOT/scripts/mcp_bridge.swift" -o "$ROOT/outlook_plugin/bin/outlook-mcp-darwin"
codesign --force --sign - "$ROOT/outlook_plugin/bin/outlook-mcp-darwin"
