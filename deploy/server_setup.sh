#!/usr/bin/env bash
# STEP 1 of going live. Run ON the new Ubuntu server, as root, from the repo root:
#     sudo ./deploy/server_setup.sh app.yourdomain.com.au
# It installs Docker (if missing), creates .env with FRESH random secrets (APP_SECRET_KEY, CREDENTIALS_ENCRYPTION_KEY,
# POSTGRES_PASSWORD) and your domain filled in, and tells you which values you still have to paste in yourself.
# Safe to re-run: an existing .env is never overwritten. Nothing here touches Google Ads.
set -euo pipefail

DOMAIN="${1:?usage: sudo ./deploy/server_setup.sh app.yourdomain.com.au}"
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo ">> Installing Docker ..."
  curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null

if [ -f .env ]; then
  echo ">> .env already exists - leaving it untouched."
else
  echo ">> Creating .env with fresh secrets ..."
  cp .env.production.example .env
  rand()  { python3 -c "import secrets; print(secrets.token_urlsafe(48))"; }
  fernet() { python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"; }
  sed -i "s|^APP_SECRET_KEY=.*|APP_SECRET_KEY=$(rand)|" .env
  sed -i "s|^CREDENTIALS_ENCRYPTION_KEY=.*|CREDENTIALS_ENCRYPTION_KEY=$(fernet)|" .env
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(rand)|" .env
  sed -i "s|app\.yourdomain\.com\.au|${DOMAIN}|g" .env
  chmod 600 .env
fi

mkdir -p secrets backups
chmod 700 secrets

echo
echo "================ STILL TO DO BY YOU (secrets are never typed into chat) ================"
echo "1) Open .env (nano .env) and paste these from your local backend/.env:"
echo "     GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_ADS_DEVELOPER_TOKEN,"
echo "     GOOGLE_ADS_LOGIN_CUSTOMER_ID (if you use one), ANTHROPIC_API_KEY"
echo "   Leave ADS_EXECUTION_KILL_SWITCH=true."
if [ ! -f secrets/gsc-service-account.json ]; then
  echo "2) Copy the GA4/Search Console key file to this server as ./secrets/gsc-service-account.json"
  echo "   (from your Windows PC, in PowerShell:  scp C:\\Users\\Administrator\\.ads-command-center\\secrets\\gsc-service-account.json root@THIS_SERVER_IP:$(pwd)/secrets/ )"
else
  echo "2) secrets/gsc-service-account.json is present."
fi
echo "3) In Google Cloud Console add this OAuth redirect URI to your OAuth client:"
echo "     https://${DOMAIN}/api/v1/ads-connection/oauth/callback"
echo "4) DNS: an A record  ${DOMAIN}  ->  this server's IP (must resolve BEFORE the next step, or HTTPS can't be issued)."
echo "5) Then start everything:"
echo "     docker compose -f docker-compose.prod.yml --env-file .env up -d --build"
echo "6) Then run STEP 2:   ./deploy/post_deploy.sh"
echo "========================================================================================"
