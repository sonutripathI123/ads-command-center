#!/bin/sh
# Daily refresh on the server (cron): Google Ads sync -> GA4 + Search Console sync -> monitoring check.
# All three are READ-ONLY toward Google. Installed into cron by deploy/post_deploy.sh.
cd "$(dirname "$0")/.." || exit 1
RUN="docker compose -f docker-compose.prod.yml --env-file .env exec -T backend"
echo "=== $(date -u '+%Y-%m-%d %H:%M:%S') UTC daily sync ==="
$RUN python -m app.modules.p05_ads_sync.cli sync
$RUN python -m app.modules.p06_analytics.cli sync
$RUN python -m app.modules.p18_monitoring.run
echo "=== done ==="
