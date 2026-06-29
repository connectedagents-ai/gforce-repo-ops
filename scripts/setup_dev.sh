#!/usr/bin/env bash
# ============================================================
# G Force Repo Ops — Full Dev Setup
# Usage: ./scripts/setup_dev.sh
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "🚀 G Force Repo Ops — Dev Setup"
echo "   Root: $REPO_ROOT"
echo ""

# ── Python / uv ──────────────────────────────────────────────
echo "📦 Setting up Python agents layer..."
if ! command -v uv &>/dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  source "$HOME/.cargo/env" 2>/dev/null || true
fi

cd "$REPO_ROOT/agents"
uv sync --all-extras
echo "✅ Python deps installed"

cd "$REPO_ROOT/hardware/gripper_bridge"
uv sync
echo "✅ Pi bridge deps installed"
cd "$REPO_ROOT"

# ── Git hooks ────────────────────────────────────────────────
echo "🔒 Installing pre-commit hooks..."
if command -v gitleaks &>/dev/null; then
  cat > .git/hooks/pre-commit <<'HOOK'
#!/bin/sh
echo "🔍 Running gitleaks..."
gitleaks detect --source . --no-git --quiet
HOOK
  chmod +x .git/hooks/pre-commit
  echo "✅ gitleaks hook installed"
else
  echo "⚠️  gitleaks not found — skipping hook (install: brew install gitleaks)"
fi

# ── .env from template ───────────────────────────────────────
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "✅ .env created from template — fill in your API keys"
else
  echo "ℹ️  .env already exists — skipping"
fi

# ── Summary ──────────────────────────────────────────────────
echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Fill in .env (or set secrets via 1Password op CLI)"
echo "  2. make router     — Start Multi-LLM router"
echo "  3. make gateway    — Start OpenClaw gateway"
echo "  4. ./hermes_config/setup_hermes.sh — Configure Hermes Agent"
echo "  5. make health     — Check system status"
echo ""
echo "Full system: make start"
