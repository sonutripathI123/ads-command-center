# Production Deployment Guide (Hinglish)

> **Sabse aasan tareeka:** `docs/GO_LIVE_CHECKLIST.md` + `deploy/server_setup.sh` + `deploy/post_deploy.sh` (secrets khud generate, admin, flags, cron, smoke test). Neeche ke steps uska manual version hain.

Yeh guide app ko ek real server (VPS) pe live karne ke liye hai. Pehle **status samjho**, phir steps follow karo.

## Deploy karne se pehle jaan lo

- **P24 "Production Hardening"** ab ban chuka hai — rate limiting, security headers, AI-call retries, smoke
  test script, backup script, recovery runbook (see `docs/RUNBOOK.md`). Baaki bacha hua: formal dependency
  scanning, aur P04/P06 (Google Ads/GA4) ke external calls pe retry (abhi sirf AI calls pe hai).
- **Login throttle** (baar-baar galat password rokta hai) sirf ek server-process ki memory mein hai. Agar aap
  multiple backend workers/replicas chalate ho to yeh consistently kaam nahi karega — abhi single-instance
  deployment ke liye theek hai.
- Zyada tar feature modules (Ads & Assets, Landing Pages, Competitors, Bookings/Revenue, Campaign Builder,
  Approvals, Monitoring, Reports, Experiments, Audit Log) **"review"** status mein hain — aapne khud inko final
  approve nahi kiya hai. Deploy karna theek hai (data safe hai, koi fabricated data nahi), lekin final sign-off
  abhi baaki hai.
- Google Ads mein koi bhi **live change kabhi nahi ho sakta** — `ADS_EXECUTION_KILL_SWITCH=true` hamesha rakhna,
  chahe kuch bhi ho.

## Kya-kya banaya gaya hai deployment ke liye (is session mein)

| File | Kaam |
|---|---|
| `frontend/Dockerfile` (naya) | Next.js ko production mein chalane ke liye |
| `frontend/next.config.ts` | `output: "standalone"` add kiya (chhota, fast Docker image) |
| `frontend/.dockerignore`, `.dockerignore` (root) | Build ke time faltu files (node_modules, dev.db, .git) skip karta hai |
| `docker-compose.prod.yml` (naya) | Poora production stack: Postgres + Redis + Backend + Frontend + Caddy (HTTPS) |
| `deploy/Caddyfile` (naya) | Reverse proxy — automatic HTTPS (Let's Encrypt), aapko khud SSL certificate nahi lagana |
| `.env.production.example` (naya) | Saare env variables ek jagah (backend, GA4/GSC, Google Ads, AI, frontend) |
| `backend/Dockerfile`, `.env.example` (already thi) | Yeh pehle se P00 mein bani hui thi, use ki gayi hain |
| `backend/app/modules/p24_hardening/*` (naya) | Rate limiting, security headers, AI-call retries, smoke test script |
| `scripts/backup.sh`, `docs/RUNBOOK.md` (naya) | Automatic backup + recovery guide |

Dev wali `docker-compose.yml` (backend/.env ke saath) waisi hi hai — yeh naya `docker-compose.prod.yml` usse alag,
naya file hai, kuch delete/replace nahi hua.

## Step-by-step: server pe deploy karna

### 1. Server lo
Koi bhi VPS chalega jisme Docker chal sake — DigitalOcean, Linode, Hetzner, AWS Lightsail, ya koi bhi Australian
provider. Minimum 2 GB RAM, 2 vCPU kaafi hai shuruaat ke liye.

### 2. Domain point karo
Do subdomains banao (ya ek hi domain pe path split kar sakte ho, par subdomain simplest hai):
- `app.yourdomain.com.au` → frontend (jo aap browser mein khologe)
- (ek hi domain kaafi hai: `/api/*` apne aap backend ko jaata hai, alag `api.` subdomain NAHI banana — login cookie ki wajah se)

Dono ke DNS mein ek **A record** daalo jo aapke server ke IP address pe point kare.

### 3. Server pe Docker install karo
```bash
curl -fsSL https://get.docker.com | sh
```

### 4. Code laao
```bash
git clone https://github.com/sonutripathI123/ads-command-center.git
cd ads-command-center
```

### 5. Secrets file banao
```bash
cp .env.production.example .env
```
Ab `.env` file kholo aur har khaali value bharo:
- `APP_SECRET_KEY` — random string (`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`)
- `POSTGRES_PASSWORD` — koi strong password
- `CORS_ORIGINS` — `["https://app.yourdomain.com.au"]`
- `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` / `GOOGLE_ADS_DEVELOPER_TOKEN` — jo aapke Google Cloud
  project mein already hain
- `GOOGLE_ADS_OAUTH_REDIRECT_URI` — `https://app.yourdomain.com.au/api/v1/ads-connection/oauth/callback` (Google
  Cloud Console mein bhi yehi URL OAuth client mein add karna hoga)
- `FRONTEND_URL` — `https://app.yourdomain.com.au`
- `CREDENTIALS_ENCRYPTION_KEY` — (`python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `ANTHROPIC_API_KEY` — Claude API key
- `NEXT_PUBLIC_API_URL` — `https://app.yourdomain.com.au` (wahi domain jo APP_DOMAIN hai)

**GA4/Search Console service account file** ke liye:
```bash
mkdir -p secrets
# apni gsc-service-account.json is folder mein copy karo
```

### 6. Caddyfile mein domain daalo
Caddyfile ko haath lagane ki zaroorat nahi: wo `.env` ke `APP_DOMAIN` se domain leta hai.

### 7. Chalao
```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```
Pehli baar 2-5 minute lagega (images build ho rahi hongi, Caddy SSL certificate lega).

### 8. Database migrate + admin user banao
Migration `backend/Dockerfile` ke `CMD` mein already chalti hai container start hote hi. Admin user banane ke liye:
```bash
docker compose -f docker-compose.prod.yml exec backend python -m app.modules.p02_auth.cli create-admin \
  --email you@yourdomain.com.au --name "Your Name"
```

### 9. Check karo (smoke test)
`https://app.yourdomain.com.au` kholo — login page dikhna chahiye. Fir poora smoke test chalao (P24) — har module
ka route check karta hai:
```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -m app.modules.p24_hardening.smoke --base-url https://app.yourdomain.com.au
```

### 10. Sync/flags chalu karo
Login karke normal tareeke se: Ads Accounts connect karo (P04), Websites add karo (P03), sync chalao (P05/P06).
Feature flags (crawler, competitor research, AI) `flags_cli` se set karo:
```bash
docker compose -f docker-compose.prod.yml exec backend python -m app.shared.flags_cli set crawler.enabled on --reason "prod" --by you@yourdomain.com.au
```

## Backup

`scripts/backup.sh` (P24) roz `pg_dump` leta hai aur purane backups (14 din se zyada) khud delete kar deta hai:
```bash
./scripts/backup.sh
```
Cron mein daal do (roz raat 2 baje):
```
0 2 * * * cd /path/to/ads-command-center && ./scripts/backup.sh >> /var/log/ads-cc-backup.log 2>&1
```
Restore karna ho to `docs/RUNBOOK.md` dekho.

## Update deploy karna (baad mein code badle to)

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

## Roz ka automatic sync (Windows PC par, jab tak server deploy nahi hota)
`scripts/daily_sync.ps1` = Google Ads sync -> GA4 + Search Console sync -> monitoring check (read-only). Flags
`ads_sync.scheduled.enabled` aur `monitoring.scheduled.enabled` ON hone chahiye. Task banane ke liye **Administrator PowerShell** mein:
```
Register-ScheduledTask -TaskName AdsCommandCenter-DailySync -Action (New-ScheduledTaskAction -Execute powershell.exe -Argument '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Users\Administrator\Desktop\ads-command-center\scripts\daily_sync.ps1"') -Trigger (New-ScheduledTaskTrigger -Daily -At 7:00AM) -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable) -Force
```
Linux server par cron mein: `cd backend && .venv/bin/python -m app.modules.p05_ads_sync.cli sync && .venv/bin/python -m app.modules.p06_analytics.cli sync && .venv/bin/python -m app.modules.p18_monitoring.run`

### Agar Task Scheduler (admin) nahi mil raha — login par roz ek baar (admin nahi chahiye)
`scripts/daily_sync.ps1 -IfNotRunToday` din mein sirf ek baar chalta hai (aaj ka sync success ho chuka ho to skip). Iska shortcut
Startup folder mein hai (`shell:startup` -> `AdsCommandCenter-DailySync.lnk`), isliye PC par login karte hi (din mein pehli baar)
sync apne aap ho jaata hai. Band karna ho to wo shortcut delete kar do. Limit: sync login par hota hai, 7 baje ke time par nahi.
