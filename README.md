> **MOVED** → This repository has moved to [Connected-Energy-AI/gforce-repo-ops](https://github.com/Connected-Energy-AI/gforce-repo-ops)

# ⚡ G Force Repo Operations System

> Multi-agent, multi-LLM operations hub wiring together OpenClaw, Hermes Agent, and a full AI model router across all platforms and hardware.

[![CI](https://github.com/connectedagents-ai/gforce-repo-ops/actions/workflows/lint.yml/badge.svg)](https://github.com/connectedagents-ai/gforce-repo-ops/actions)
[![Security](https://github.com/connectedagents-ai/gforce-repo-ops/actions/workflows/security.yml/badge.svg)](https://github.com/connectedagents-ai/gforce-repo-ops/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Architecture

```
Telegram · Discord · Slack · WhatsApp · Signal · Web UI
                          ↓
              OpenClaw Gateway (Node.js)
         Skills: GitHub · Gripper · Energy
                          ↓
            Multi-LLM Router (Python/FastAPI)
     Mercury Hermes · Hermes 3 · Gemini · Claude · GPT-4o
                          ↓
         Hermes Agent (Persistent / Memory / Skills)
                          ↓
            MCP Tool Servers (GitHub · Gripper · Energy)
                          ↓
    Raspberry Pi Gripper Bridge  ·  GitHub API  ·  ERCOT API
```

---

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **OpenClaw Gateway** | `gateway/` | Messaging platform bridge + Skill registry |
| **Multi-LLM Router** | `agents/router/` | Task-based model selection (6 LLMs) |
| **Hermes Agent** | `agents/hermes/` | Persistent autonomous agent w/ memory |
| **GitHub MCP Server** | `agents/mcp_servers/github_mcp.py` | Repo automation tools |
| **Gripper MCP Server** | `agents/mcp_servers/gripper_mcp.py` | Hardware control bridge |
| **Energy MCP Server** | `agents/mcp_servers/energy_mcp.py` | ERCOT/Power Connection tools |
| **Pi Gripper Bridge** | `hardware/gripper_bridge/` | FastAPI server on Raspberry Pi |
| **Web Dashboard** | `web/` | Real-time operations dashboard |

---

## Quick Start

### Prerequisites
- Node.js 20+ (for OpenClaw)
- Python 3.11+ with `uv`
- `gh` CLI authenticated
- 1Password CLI (`op`) for secrets

### Setup
```bash
make setup
```

This installs all dependencies, configures environment variables (via 1Password), and starts the full system.

### Start Everything
```bash
make start       # Start all services
make start-dev   # Start in development mode with verbose logging
```

### Individual Services
```bash
make gateway     # Start OpenClaw gateway only
make router      # Start Multi-LLM router only
make hermes      # Start Hermes Agent only
make dashboard   # Start web dashboard only
```

---

## LLM Router — Model Selection

| Task Type | Model | Latency | Use Case |
|-----------|-------|---------|----------|
| Quick Q&A, simple tasks | Mercury Hermes | ~200ms | Fast replies |
| Code generation, analysis | Hermes 3 70B | ~2s | Dev tasks |
| Deep reasoning, litigation | Gemini 2.5 Pro | ~3s | Complex analysis |
| Documents, drafts | Claude Sonnet 4.x | ~2s | Writing |
| Vision, images | GPT-4o | ~3s | Multimodal |
| Private/local | Ollama Mistral | ~5s | Air-gapped |

Call the router at `http://localhost:9000/v1` (OpenAI-compatible).

---

## OpenClaw Skills

| Skill | Trigger Examples |
|-------|-----------------|
| `github_ops` | "Review PR #42", "What issues are open?", "Run CI on main" |
| `gripper_control` | "Open the gripper", "Close with 50% force", "Gripper status" |
| `energy_ops` | "Get ERCOT 4CP status", "List active customers", "Run proforma" |

---

## Hermes Agent

Hermes Agent runs as a persistent daemon with cross-session memory:

```bash
# First-time setup
./hermes_config/setup_hermes.sh

# Launch
hermes gateway

# Or use the API directly
curl http://127.0.0.1:8642/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "hermes-3", "messages": [{"role": "user", "content": "Check GitHub CI status"}]}'
```

---

## Hardware — Raspberry Pi Gripper Bridge

The OpenClaw gripper runs on a Raspberry Pi exposing a FastAPI REST API:

```bash
# On the Pi:
cd hardware/gripper_bridge
./deploy.sh

# Test:
curl http://<pi-ip>:8080/status
curl -X POST http://<pi-ip>:8080/open
curl -X POST http://<pi-ip>:8080/close
curl -X POST http://<pi-ip>:8080/set_force/75
```

Accessible as an MCP tool from any agent in the system.

---

## Security

- **No secrets in git** — all values via `op read "op://Private/..."` or GitHub Secrets
- **gitleaks** runs on every commit (pre-commit hook + CI)
- **Force limits enforced** in hardware safety middleware
- **Network isolation** — Pi bridge only accessible via Tailscale VPN in prod

---

## CI/CD

```
push → lint (ruff + mypy) → test (pytest, network-blocked) → security (gitleaks)
```

All on GitHub Actions. Protected `main` branch requires full CI pass + PR review.

---

## Project Structure

```
gforce-repo-ops/
├── .github/workflows/     # CI: lint, test, security
├── gateway/               # OpenClaw gateway + skills
│   ├── skills/
│   │   ├── github_ops/
│   │   ├── gripper_control/
│   │   └── energy_ops/
│   └── personas/
├── agents/                # Python agent layer
│   ├── router/            # Multi-LLM router
│   ├── hermes/            # Hermes Agent integration
│   └── mcp_servers/       # MCP tool servers
├── hardware/              # Raspberry Pi code
│   └── gripper_bridge/    # FastAPI gripper bridge
├── hermes_config/         # Hermes Agent setup
├── web/                   # Next.js dashboard
├── scripts/               # Dev helper scripts
└── tests/                 # Test suite
```

---

## AGENTS.md Compliance

This repo follows all rules in `~/.gemini/config/AGENTS.md`:
- `uv` for Python package management (never global pip)
- `ruff` + `mypy` for linting and types
- `gitleaks` pre-commit hook
- All secrets via 1Password CLI
- Evidence/litigation files: immutable originals, copies only
- No destructive operations without explicit approval

---

*Built by Robert Bailey · Power Connection AI · Connected Energy Services*
*Multi-agent orchestration powered by Google Antigravity SDK*