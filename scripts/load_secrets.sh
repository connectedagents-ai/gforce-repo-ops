#!/usr/bin/env bash
# ===========================================================
# G Force — Secret Loader
# Resolves op:// references from .env and exports real values
# Usage: source scripts/load_secrets.sh
# ===========================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

echo "🔐 G Force Secret Loader"
echo "========================"

# Check 1Password auth
if ! op whoami &>/dev/null; then
    echo "❌ 1Password CLI not authenticated."
    echo "   Run: eval \$(op signin --account powerconnection)"
    return 1 2>/dev/null || exit 1
fi
echo "✅ 1Password authenticated"

# Count and resolve op:// references
RESOLVED=0
FAILED=0
SKIPPED=0

while IFS= read -r line; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$line" ]] && continue
    
    # Parse KEY=VALUE
    KEY="${line%%=*}"
    VALUE="${line#*=}"
    
    # Only resolve op:// references
    if [[ "$VALUE" == op://* ]]; then
        REAL_VALUE=$(op read "$VALUE" 2>/dev/null) || {
            echo "  ⚠️  $KEY — could not resolve ($VALUE)"
            ((FAILED++))
            continue
        }
        export "$KEY=$REAL_VALUE"
        echo "  ✅ $KEY — resolved"
        ((RESOLVED++))
    else
        export "$KEY=$VALUE"
        ((SKIPPED++))
    fi
done < "$ENV_FILE"

echo ""
echo "📊 Results: $RESOLVED resolved | $FAILED failed | $SKIPPED static"
echo "🚀 Environment ready for G Force services"
