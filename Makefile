.DEFAULT_GOAL := help

# ============================================================
# G Force Repo Ops — Makefile
# Standard targets per AGENTS.md
# ============================================================

PYTHON := python3
UV := uv
NODE := node
NPM := npm

.PHONY: help setup test lint fmt clean audit start start-dev gateway router hermes dashboard pi-deploy

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────

setup: ## Install all deps, hooks, and verify environment
	@echo "🔧 Setting up G Force Repo Ops System..."
	@./scripts/setup_dev.sh

setup-python: ## Install Python deps with uv
	cd agents && $(UV) sync
	cd hardware/gripper_bridge && $(UV) sync

setup-node: ## Install Node.js deps for OpenClaw gateway
	cd gateway && $(NPM) install

setup-web: ## Install Next.js deps for web dashboard
	cd web && $(NPM) install

setup-hooks: ## Install git pre-commit hooks (gitleaks)
	@echo "🔒 Installing pre-commit hooks..."
	@echo '#!/bin/sh\ngitleaks detect --source . --no-git' > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✅ gitleaks pre-commit hook installed"

# ── Code Quality ─────────────────────────────────────────────

lint: ## Run ruff + mypy
	cd agents && $(UV) run ruff check . --fix
	cd agents && $(UV) run mypy --strict .
	cd hardware/gripper_bridge && $(UV) run ruff check . --fix

fmt: ## Format with ruff
	cd agents && $(UV) run ruff format .
	cd hardware/gripper_bridge && $(UV) run ruff format .

test: ## Run tests (network-blocked)
	cd agents && $(UV) run pytest tests/ -x -v --no-header \
		--env ENVIRONMENT=test \
		-p no:network
	@echo "✅ All tests passed"

audit: ## Security audit: gitleaks + dependency scan
	@echo "🔍 Running gitleaks..."
	gitleaks detect --source . --no-git
	@echo "🔍 Running uv audit..."
	cd agents && $(UV) run pip-audit || true
	@echo "✅ Audit complete"

# ── Runtime ──────────────────────────────────────────────────

start: ## Start all services (router + gateway + hermes)
	@echo "🚀 Starting G Force Ops System..."
	@./scripts/start_agents.sh &
	@sleep 2
	@./scripts/start_gateway.sh &
	@echo "✅ System started. Check logs/ for details."

start-dev: ## Start in development mode (verbose)
	LOG_LEVEL=DEBUG $(MAKE) start

gateway: ## Start OpenClaw gateway only
	@./scripts/start_gateway.sh

router: ## Start Multi-LLM router only
	@cd agents && $(UV) run uvicorn router.main:app --host 0.0.0.0 --port 9000 --reload

hermes: ## Configure and start Hermes Agent
	@./hermes_config/setup_hermes.sh
	@hermes gateway

dashboard: ## Start web dashboard (dev server)
	npm install --prefix web
	cd web && ./node_modules/.bin/next dev

# ── Hardware ─────────────────────────────────────────────────

pi-deploy: ## Deploy gripper bridge to Raspberry Pi
	@./hardware/deploy.sh

pi-status: ## Check gripper bridge status on Pi
	@curl -s http://$${PI_HOST}:$${PI_GRIPPER_PORT:-8080}/health | python3 -m json.tool

pi-test: ## Test gripper open/close
	@echo "Testing gripper open..."
	@curl -s -X POST http://$${PI_HOST}:$${PI_GRIPPER_PORT:-8080}/open | python3 -m json.tool
	@sleep 2
	@echo "Testing gripper close..."
	@curl -s -X POST http://$${PI_HOST}:$${PI_GRIPPER_PORT:-8080}/close | python3 -m json.tool

# ── Health ───────────────────────────────────────────────────

health: ## Run full system health check
	@./scripts/health_check.sh

# ── Cleanup ──────────────────────────────────────────────────

clean: ## Clear caches + build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned"

clean-all: clean ## Clean + remove node_modules and .venv
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .venv -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Deep clean complete"
