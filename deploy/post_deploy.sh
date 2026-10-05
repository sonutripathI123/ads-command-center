#!/usr/bin/env bash
# STEP 2 of going live. Run on the server, from the repo root, AFTER `docker compose ... up -d --build`:
#     ./deploy/post_deploy.sh
# 1) waits until the backend answers  2) creates your admin login (you type the password)  3) switches on the same read-only
# feature flags you use locally  4) installs the daily sync + nightly backup cron jobs  5) runs the smoke test.
# It never turns on live Google Ads execution (ADS_EXECUTION_KILL_SWITCH stays true; P17 flags stay off).
set -euo pipefail
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env"
DOMAIN="$(grep -E '^APP_DOMAIN=' .env | cut -d= -f2-)"

echo ">> Waiting for the backend ..."
for i in $(seq 1 40); do
  if $COMPOSE exec -T backend python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/foundation/health',timeout=3).status==200 else 1)" 2>/dev/null; then
    echo "   backend is up."; break
  fi
  [ "$i" = 40 ] && { echo "Backend did not come up. Check:  $COMPOSE logs backend --tail 80"; exit 1; }
  sleep 3
done

echo ">> Creating the admin user (you will type the password; min 12 characters) ..."
$COMPOSE exec backend python -m app.modules.p02_auth.cli create-admin --visible

echo ">> Feature flags (read-only features only) ..."
flag() { $COMPOSE exec -T backend python -m app.shared.flags_cli set "$1" on --reason "$2" --by "go-live"; }
flag crawler.enabled "scan our own websites"
flag competitor.research.enabled "public competitor research"
flag ai.live_calls.enabled "live Claude for ads / briefs / recommendations"
flag ads_sync.scheduled.enabled "daily automatic sync (cron)"
flag monitoring.scheduled.enabled "daily monitoring check (cron)"

echo ">> Installing cron jobs (/etc/cron.d/ads-command-center) ..."
ROOT="$(pwd)"
cat > /etc/cron.d/ads-command-center <<EOF
# times are UTC: 20:30 UTC = 7:30am Melbourne (AEDT) / 6:30am (AEST)
30 20 * * * root $ROOT/deploy/daily_sync.sh >> /var/log/ads-cc-sync.log 2>&1
15 17 * * * root cd $ROOT && ./scripts/backup.sh $ROOT/backups 14 >> /var/log/ads-cc-backup.log 2>&1
EOF
chmod 644 /etc/cron.d/ads-command-center
chmod +x deploy/*.sh scripts/backup.sh

echo ">> Smoke test ..."
$COMPOSE exec -T backend python -m app.modules.p24_hardening.smoke --base-url "https://${DOMAIN}" || \
  echo "   (smoke test failed: DNS or HTTPS may still be settling - retry in a minute)"

echo
echo "Done. Open  https://${DOMAIN}  and sign in. Then:"
echo "  - Ads Accounts page: click 'Connect Google Ads' (you sign in with Google yourself), add the account"
echo "  - Websites page: add corporatecarsmelbourne.com.au (GA4 property 550393874, Search Console site)"
echo "  - Header 'Sync now'  (the first sync pulls ~90 days)"
