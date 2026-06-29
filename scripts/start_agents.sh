#!/usr/bin/env bash
# ============================================================
# Start Multi-LLM Router + Hermes Agent
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"

echo "🚀 Starting agent services..."

# Multi-LLM Router
echo "  Starting Multi-LLM Router on :${ROUTER_PORT:-9000}..."
cd "$REPO_ROOT/agents"
uv run uvicorn router.main:app \
  --host "${ROUTER_HOST:-0.0.0.0}" \
  --port "${ROUTER_PORT:-9000}" \
  --log-level "${LOG_LEVEL:-info}" \
  >> "$LOG_DIR/router.log" 2>&1 &

ROUTER_PID=$!
echo "  Router PID: $ROUTER_PID"
echo "$ROUTER_PID" > "$LOG_DIR/router.pid"

echo "✅ Agents started. Logs: $LOG_DIR/"
echo "   curl http://localhost:${ROUTER_PORT:-9000}/health"
