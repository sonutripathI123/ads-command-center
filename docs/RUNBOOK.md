# Recovery Runbook (Hinglish)

Kuch bhi galat ho jaaye to yahan dekho. Har scenario ka fix step-by-step hai.

## Backend down hai / site nahi khul raha
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend --tail 100
```
Agar `backend` container "Restarting" dikhe, zyada tar wajah galat `.env` value hoti hai (missing secret,
galat DATABASE_URL). Fix karke:
```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build backend
```

## Database corrupt ho gaya / restore karna hai
```bash
# Naya backup pehle le lo (agar possible ho) taaki current state bhi safe rahe
./scripts/backup.sh

# Restore ek purani backup se:
gunzip -c backups/ads_command_center_2026-09-29_020000.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres psql -U ads -d ads_command_center
```

## Secrets rotate karne hain (password leak ho gaya, ya key change karni hai)
1. `.env` mein naya value daalo (`APP_SECRET_KEY` badalne se **sab existing sessions logout** ho jaayengi —
   yeh theek hai, dobara login karna padega).
2. `CREDENTIALS_ENCRYPTION_KEY` **kabhi mat badlo** jab tak Google Ads connections dobara reconnect karne ko
   ready na ho — yeh key change hote hi saare stored OAuth tokens unreadable ho jaate hain (P04 ko dobara
   "Connect Google Ads" karna padega).
3. Restart: `docker compose -f docker-compose.prod.yml --env-file .env up -d`

## GA4/GTM tracking achanak toot gayi
Monitoring page (`/monitoring`) aur Conversions page (`/conversions`) pe dekho — tracking health checks (P06)
automatically bata denge kya toota hai (no key events, no GA4 data, wagera). Fix ke steps wahi hain jo GTM/GA4
setup ke waqt follow kiye the — trigger/tag check karo GTM mein, key event mark hai ya nahi GA4 mein.

## Google Ads account disconnect ho gaya
Ads Accounts page (`/ads-accounts`) → connection health red dikhega. "Reconnect" se dobara OAuth flow chalao —
koi data nahi khoya, sirf naya refresh token chahiye.

## Kill switch — confirm karna ki lock hai
```bash
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.shared.config import get_settings; print(get_settings().ads_execution_kill_switch)"
```
`True` aana chahiye hamesha — agar `.env` mein `ADS_EXECUTION_KILL_SWITCH` set nahi kiya, default hi `true` hai.

## Deploy ke baad verify karna hai sab theek hai
```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -m app.modules.p24_hardening.smoke --base-url https://api.yourdomain.com.au
```
Har route ka PASS/FAIL list milega.

## Rate limiting bahut strict lag raha hai (legit users bhi block ho rahe)
`.env` mein `RATE_LIMIT_PER_MINUTE` aur `RATE_LIMIT_WINDOW_SECONDS` set karke badha sakte ho (default 300/60s),
fir restart karo backend.
