#!/usr/bin/env bash
# Deploy tm-skills-api to Cloud Foundry with auto-generated API key.
#
# Usage:
#   ./deploy.sh              # Deploy (generates key on first run)
#   ./deploy.sh --rotate     # Generate a new key and redeploy
#
# The API key is stored in .api-key (gitignored). On first deploy it is
# generated automatically. On subsequent deploys the existing key is reused.

set -euo pipefail

APP_NAME="tm-skills-api"
KEY_FILE=".api-key"

# ── Handle --rotate flag ────────────────────────────────────────────────────
if [[ "${1:-}" == "--rotate" ]]; then
    echo "Rotating API key..."
    rm -f "$KEY_FILE"
fi

# ── Generate key if needed ──────────────────────────────────────────────────
if [ ! -f "$KEY_FILE" ]; then
    python3 -c "import secrets; print(secrets.token_urlsafe(32))" > "$KEY_FILE"
    echo "Generated new API key. Save this somewhere safe:"
    echo "  $(cat "$KEY_FILE")"
    echo ""
fi

API_KEY=$(cat "$KEY_FILE")

# ── Deploy ──────────────────────────────────────────────────────────────────
echo "Deploying $APP_NAME..."
cf push --no-start

echo "Setting API_KEYS..."
cf set-env "$APP_NAME" API_KEYS "$API_KEY"

echo "Setting DB_PASSWORD..."
# DB_PASSWORD must already be in CF env from a previous deploy, or set it:
#   cf set-env tm-skills-api DB_PASSWORD "your-db-password"

echo "Starting $APP_NAME..."
cf start "$APP_NAME"

echo ""
echo "Deployed. Test with:"
echo "  curl -H 'X-API-Key: $API_KEY' https://$APP_NAME.cfapps.ap10.hana.ondemand.com/health"
