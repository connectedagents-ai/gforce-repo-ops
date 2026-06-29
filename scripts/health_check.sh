#!/usr/bin/env bash
# ============================================================
# G Force System Health Check
# Usage: ./scripts/health_check.sh
# ============================================================
set -euo pipefail

PASS=0
FAIL=0
WARN=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo "  ✅ $name"
    ((PASS++)) || true
  else
    echo "  ❌ $name"
    ((FAIL++)) || true
  fi
}

warn() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo "  ✅ $name"
    ((PASS++)) || true
  else
    echo "  ⚠️  $name (optional)"
    ((WARN++)) || true
  fi
}

echo "🏥 G Force Repo Ops — System Health Check"
echo "==========================================="
echo ""

echo "📋 Prerequisites:"
check "Python 3.10+" "python3 -c 'import sys; assert sys.version_info >= (3, 10)'"
check "uv installed" "command -v uv"
check "Node.js 20+" "node --version | grep -E 'v(2[0-9]|[3-9][0-9])'"
check "npm installed" "command -v npm"
check "gh CLI authenticated" "gh auth status"
warn "gitleaks installed" "command -v gitleaks"
warn "op (1Password CLI)" "command -v op"

echo ""
echo "🔑 API Keys (env check — values not shown):"
warn "OPENROUTER_API_KEY" "test -n \"\${OPENROUTER_API_KEY:-}\""
warn "GITHUB_TOKEN" "test -n \"\${GITHUB_TOKEN:-}\""
warn "GEMINI_API_KEY" "test -n \"\${GEMINI_API_KEY:-}\""
warn "ANTHROPIC_API_KEY" "test -n \"\${ANTHROPIC_API_KEY:-}\""

echo ""
echo "🌐 Services:"
warn "Multi-LLM Router" "curl -sf http://localhost:9000/health"
warn "Hermes Agent API" "curl -sf http://localhost:${HERMES_API_PORT:-8642}/v1/models"
warn "Gripper Bridge (Pi)" "curl -sf http://${PI_HOST:-localhost}:${PI_GRIPPER_PORT:-8080}/health"

echo ""
echo "==========================================="
echo "  ✅ Pass: $PASS  ❌ Fail: $FAIL  ⚠️  Warn: $WARN"
echo ""
if [[ $FAIL -gt 0 ]]; then
  echo "Run 'make setup' to fix missing prerequisites."
  exit 1
fi
