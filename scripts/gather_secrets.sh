#!/usr/bin/env bash
# G Force - Secret Gathering & Injection Script
# Extracts keys from 1Password and writes them to a local .env file.
# Auto-generates OPENCLAW_GATEWAY_TOKEN if missing.

set -e

ENV_FILE="../.env"
cd "$(dirname "$0")"

echo "🔐 Initializing G Force Secret Gathering..."

# Ensure user is signed in to 1Password CLI
if ! op whoami &>/dev/null; then
    echo "❌ Not signed into 1Password CLI. Run: eval \$(op signin --account powerconnection)"
    exit 1
fi

echo "✅ Authenticated with 1Password."
echo "Creating .env template..."

cat << 'EOF' > .env.tpl
OPENROUTER_API_KEY={{ op://AI-Agents/OpenRouter API Key/credential }}
GEMINI_API_KEY={{ op://AI-Agents/Gemini API Key/credential }}
ANTHROPIC_API_KEY={{ op://AI-Agents/Anthropic API Key/credential }}
OPENAI_API_KEY={{ op://AI-Agents/OpenAI API Key/credential }}
OPENCLAW_GATEWAY_TOKEN={{ op://MCP-Servers/OpenClaw Gateway Token/credential }}
EOF

# Check if OpenClaw token exists in 1Password
echo "🔍 Checking for OpenClaw Gateway Token in 1Password..."
if ! op read "op://MCP-Servers/OpenClaw Gateway Token/credential" &>/dev/null; then
    echo "⚠️ OpenClaw Gateway Token not found in 1Password. Auto-generating..."
    
    # Generate a random secure token
    NEW_TOKEN=$(openssl rand -hex 32)
    
    # Save to 1Password
    op item create \
        --category "API Credential" \
        --vault "MCP-Servers" \
        --title "OpenClaw Gateway Token" \
        "credential[password]=$NEW_TOKEN"
    
    echo "✅ Auto-generated OpenClaw Gateway Token and saved to 1Password (Vault: MCP-Servers)."
fi

# Inject secrets into .env
echo "💉 Injecting secrets into $ENV_FILE..."
op inject -i .env.tpl -o "$ENV_FILE"

# Clean up template
rm .env.tpl

echo "🚀 Secrets successfully gathered and injected into $ENV_FILE!"
echo "You can now safely restart the backend: make start-dev"
