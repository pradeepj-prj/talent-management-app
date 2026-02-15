#!/usr/bin/env bash
# Deploy tm-skills-api to Cloud Foundry with auto-generated API key.
#
# Usage:
#   ./deploy.sh              # Deploy (generates API key on first run)
#   ./deploy.sh --rotate     # Generate a new API key and redeploy
#
# Secrets are stored locally in gitignored files:
#   .api-key      — API key for X-API-Key auth
#   .db-password   — Database password
#
# On first deploy you will be prompted for the DB password.

set -euo pipefail

APP_NAME="tm-skills-api"
KEY_FILE=".api-key"
DB_PW_FILE=".db-password"

# ── Handle --rotate flag ────────────────────────────────────────────────────
if [[ "${1:-}" == "--rotate" ]]; then
    echo "Rotating API key..."
    rm -f "$KEY_FILE"
fi

# ── Generate API key if needed ──────────────────────────────────────────────
if [ ! -f "$KEY_FILE" ]; then
    python3 -c "import secrets; print(secrets.token_urlsafe(32))" > "$KEY_FILE"
    echo "Generated new API key. Save this somewhere safe:"
    echo "  $(cat "$KEY_FILE")"
    echo ""
fi

# ── Get DB password ─────────────────────────────────────────────────────────
if [ ! -f "$DB_PW_FILE" ]; then
    echo -n "Enter DB password (first-time setup): "
    read -rs DB_PASSWORD
    echo ""
    echo "$DB_PASSWORD" > "$DB_PW_FILE"
    echo "DB password saved to $DB_PW_FILE (gitignored)."
fi

API_KEY=$(cat "$KEY_FILE")
DB_PASSWORD=$(cat "$DB_PW_FILE")

# ── Deploy ──────────────────────────────────────────────────────────────────
echo "Deploying $APP_NAME..."
cf push --no-start

echo "Setting secrets..."
cf set-env "$APP_NAME" API_KEYS "$API_KEY"
cf set-env "$APP_NAME" DB_PASSWORD "$DB_PASSWORD"

echo "Starting $APP_NAME..."
cf start "$APP_NAME"

echo ""
echo "Deployed. Test with:"
echo "  curl -H 'X-API-Key: $API_KEY' https://$APP_NAME.cfapps.ap10.hana.ondemand.com/health"
