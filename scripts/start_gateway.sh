#!/usr/bin/env bash
# Start the OpenClaw Gateway

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/gateway"

echo "Starting OpenClaw gateway..."
openclaw gateway run
