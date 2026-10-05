# Go-Live Checklist — naye Linux server par (Hinglish)

**Ye guide sirf NAYE, ALAG server ke liye hai** (khaali Ubuntu). Purane shared server (82.29.197.37, jahan doosri live websites hain)
par kuch install nahi karna.

## A. Pehle ye cheezein tayyar rakho
| Cheez | Detail |
|---|---|
| **Server (VPS)** | Ubuntu 24.04, kam se kam 2 GB RAM / 2 vCPU / 30 GB disk, Sydney ya Melbourne region. Sirf is app ke liye. SSH key se login. Ports **80 aur 443** khule (firewall). |
| **Domain** | Ek hi hostname, jaise `ads.corporatecarsmelbourne.com.au`. DNS mein **A record** → server ka IP. (Alag `api.` subdomain mat banao.) |
| **Google Cloud** | Jis OAuth client se aap Ads connect karte ho, usme **Authorized redirect URI** add karo: `https://<aapka-domain>/api/v1/ads-connection/oauth/callback`. Consent screen agar **"Testing"** mode mein hai to refresh token **7 din** mein expire hota hai: use **"In production"** karo. |
| **Local `backend/.env` se ye 5 values** | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (agar hai), `ANTHROPIC_API_KEY`. Inhe chat mein kabhi mat bhejna, seedha server ki `.env` mein paste karna. |
| **GA4/Search Console key** | `C:\Users\Administrator\.ads-command-center\secrets\gsc-service-account.json` (server par copy hogi). |
| **Naya admin password** | 12+ characters, server par type karoge. |

## B. Repo mein kaun si files kaam aati hain
| File | Kaam |
|---|---|
| `docker-compose.prod.yml` | Poora stack: Postgres + Redis + Backend + Frontend + Caddy (HTTPS) |
| `backend/Dockerfile`, `frontend/Dockerfile` | Images; backend start par database migrations khud chalata hai |
| `deploy/Caddyfile` | Ek domain: `/api/*` → backend, baaki → frontend, HTTPS khud |
| `.env.production.example` | `.env` ka template (secrets script khud banata hai) |
| `deploy/server_setup.sh` | **STEP 1**: Docker install + `.env` with fresh secrets |
| `deploy/post_deploy.sh` | **STEP 2**: admin user, flags, daily-sync + backup cron, smoke test |
| `deploy/daily_sync.sh`, `scripts/backup.sh` | Roz sync / roz backup (cron mein lagte hain) |
| `docs/RUNBOOK.md` | Kuch toote to kya karna hai |

## C. Steps
**Aapke PC par**
1. Latest code GitHub par push ho (mujhe bolo, main push kar dunga).
2. GA4 key server par bhejo (server banne ke baad): PowerShell mein
   `scp C:\Users\Administrator\.ads-command-center\secrets\gsc-service-account.json root@SERVER_IP:/root/ads-command-center/secrets/`

**Server par (SSH se, root)**
```
git clone https://github.com/sonutripathI123/ads-command-center.git /root/ads-command-center
cd /root/ads-command-center
./deploy/server_setup.sh ads.corporatecarsmelbourne.com.au      # STEP 1  (apna domain)
nano .env                                                       # 5 Google/Anthropic values paste karo, save
docker compose -f docker-compose.prod.yml --env-file .env up -d --build    # pehli baar 5-10 min
./deploy/post_deploy.sh                                         # STEP 2: admin + flags + cron + smoke test
```
(Agar repo private hai to `git clone` ke liye GitHub token chahiye, ya `ads-command-center-deploy.zip` ko `scp` karke `unzip` karo.)

**Browser mein**
3. `https://<aapka-domain>` kholo, admin se login.
4. **Ads Accounts** → *Connect Google Ads* (Google login aap khud karoge) → account add karo.
5. **Websites** → `corporatecarsmelbourne.com.au` add karo (GA4 property `550393874`, Search Console site `https://corporatecarsmelbourne.com.au/`, Ads account link).
6. Header ka **Sync now** dabao (pehli baar ~90 din ka data aata hai, 1-2 minute).
7. **Business Rules** page par services/areas dekh lo (naye server par defaults se shuru hoga).

## D. Dhyan dene wali baatein (sach batata hoon)
- **Naya server khaali shuru hota hai.** Local `dev.db` ka data (users, competitors ke notes, audit history, purane reports) copy nahi hota; Google Ads / GA4 / Search Console ka data sync se wapas aa jaata hai. OAuth tokens naye encryption key se bante hain, isliye Ads dobara connect karna padega.
- **Docker image aur Postgres par ye code pehli baar chalega.** Ab tak sab tests SQLite par hue hain. Pehli baar kuch fail ho to `docker compose -f docker-compose.prod.yml logs backend --tail 80` ka output mujhe bhej dena, main theek kar dunga.
- **Live Google Ads execution band hai** (`ADS_EXECUTION_KILL_SWITCH=true`). Server par bhi waisa hi rahega.
- Backend ek hi process mein chalta hai (replicas mat badhana; login-throttle memory mein hai).
- Backup roz 17:15 UTC (`/root/ads-command-center/backups`, 14 din rakhta hai). Backup ko kabhi server ke bahar bhi copy karo.
- Roz ka sync 20:30 UTC = Melbourne mein subah 6:30-7:30.
- Update karna ho: `git pull && docker compose -f docker-compose.prod.yml --env-file .env up -d --build`.

## E. Kabhi nahi karna
- `.env`, `secrets/`, `backend/dev.db` ko git mein mat daalo (gitignored hain).
- Purane shared server (82.29.197.37) par kuch mat chalao.
- Kill switch tab tak `true` jab tak P17 ko khud live unlock karne ka faisla na karo.
