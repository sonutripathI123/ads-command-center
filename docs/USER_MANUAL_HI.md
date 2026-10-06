# AI Google Ads Command Center — Poora User Manual (Hinglish)

Ye manual Corporate Cars Melbourne / Opal Chauffeurs ke owner ke liye hai. Isme likha hai ki app kya karta hai, har page par kya dikhta hai, har button kya karta hai, data kahan se aata hai, aur use kaise karna hai.

---

## 1. App ka main kaam

Ye app aapke Google Ads account ka **dimaag aur dashboard** hai. Ye:

1. Google Ads ka data **sirf padhta hai** (read-only) aur apne database mein rakhta hai.
2. Aapki website, GA4 (Analytics) aur Search Console ka data jodta hai.
3. Data dekh kar **galtiyan aur mauke** dhoondta hai (audit, wasted keywords, budget/bid insights).
4. **Suggestion** deta hai: kaun se negative keywords lagao, kaisa ad likho, landing page mein kya sudharo.
5. Har suggestion **aapki approval** ke baad hi aage badhti hai.
6. Google Ads mein koi live change **abhi lock hai**. App khud se kuch change nahi karta.

**Sabse zaroori baat:** app advisory hai. Approve karne se bhi Google Ads mein kuch nahi badalta. Live change ke liye alag page (`/execution`) aur kai tala (locks) kholne padte hain, jo abhi band hain.

## 2. Teen layer: data -> samajh -> action

| Layer | Kya hota hai | Kaun se pages |
|---|---|---|
| Data (source) | Google Ads, GA4, Search Console, website scan ka raw data aata hai | Websites, Ads Accounts, Conversions, Campaigns, Ad Groups, Keywords, Search Terms |
| Samajh (insight) | App data ko padh kar problems aur mauke nikalta hai | Account Audit, Keyword insights, Landing Pages, Competitors, Bookings/Revenue, Budget & Bid, Monitoring |
| Action | Suggestion banti hai, aap approve/reject karte ho | AI Recommendations, Campaign Builder, Ads & Assets, Approval Center, Experiments, Execution (locked) |

## 3. Data kahan se aata hai (ek nazar mein)

| Data | Source | Kaise aata hai | Kab update hota hai |
|---|---|---|---|
| Campaigns, Ad Groups, Keywords, Search Terms, Ads, spend/clicks/conversions | **Google Ads** | OAuth se connect, read-only GAQL queries (Ads Connection page) | Header ka `Sync now`, page ka `Sync now`, aur roz automatic daily sync |
| Traffic, events (generate_lead etc.), channels | **GA4** (Google Analytics 4) | Service account se GA4 Data API | Conversions page ka sync / header `Sync now` |
| Search queries, impressions, clicks, position (organic) | **Google Search Console** | Wahi service account | Conversions sync ke saath |
| Website pages, issues, landing page checks | **Aapki website ka scan** | App public pages crawl karta hai (flag `crawler.enabled` ON) | Jab aap `Scan` dabate ho |
| Competitor ki jaankari | **Competitor ki public website** | Research button (flag `competitor.research.enabled` ON) + aapki manual notes | Jab aap research chalate ho |
| AI likhai / action plan / interpretation | **Claude AI** | `ai.live_calls.enabled` ON hai to live Claude, warna rule-based template. Screen par label dikhta hai | Jab aap button dabate ho |
| Business rules (kaun si services, kahan serve karte ho, kya exclude) | **Aapka khud ka input** | Business Rules page | Jab aap save karo |
| Bookings aur revenue | **CSV import** (aapka khud ka) | Conversions page se import | Abhi koi data import nahi hua, isliye "not measured" dikhta hai |

Kuch bhi **banaya hua ya demo data nahi hai**. Jo number "not measured" ya khaali hai, wo sach mein measure nahi hua.

## 4. Roz ka kaam (5 minute)

1. App kholo, login karo.
2. Header mein `Sync now` dabao. Isse sab data (Google Ads + GA4 + Search Console) naya aa jaata hai. (Daily auto-sync bhi chalta hai, par PC on hona chahiye.)
3. **Overview** par dekho: spend, clicks, conversions theek hain?
4. **Monitoring & Alerts** kholo. Koi Open alert ho to padho, `Acknowledge` ya `Mark resolved` karo.
5. **Approval Center** mein pending suggestions dekho. Samajh aaye to `Approve`, warna `Reject`.

## 5. Haftawar kaam (30 minute)

1. **Account Audit** -> `Run audit`. Score aur naye issues dekho.
2. **Search Terms** -> **Negative keywords** page par `Analyze` chalao. Paisa waste karne wale terms ko accept karo.
3. **AI Recommendations** -> `Refresh from audit`. Top priority 3 kaam chuno.
4. **Budget & Bid Insights** -> `Run analysis`. Device, time, location ke findings dekho.
5. **Reports** -> weekly report generate karo, boss/team ko bhejo.

## 6. Pehli baar setup kaise hota hai (ek baar ka kaam)

1. **Ads Accounts** page: `Connect Google Ads` -> Google login -> permission do.
2. Account list se apna account add/enable karo.
3. **Websites** page: apni website add karo, `Scan` chalao.
4. **Business Rules**: services, serve karne wale areas, exclude terms bharo (isse AI ki salah sahi aati hai).
5. **Conversions**: GA4 property aur Search Console site jodo, events ko role do (`lead`, `booking`, `micro`, `ignore`).
6. Header `Sync now` dabao. Ab sab pages mein data dikhega.

---

# Page-by-page guide (har page, har button)

## Shuruaat: kaun sa page kahan hai

Sidebar sections: Overview; Sources (Websites, Ads Accounts, Conversions); Google Ads (Campaigns, Ad Groups, Keywords, Search Terms, Ads & Assets); Insights (Bookings/Revenue, Landing Pages, Competitors, AI Recommendations); Actions (Campaign Builder, Approval Center, Experiments); Operations (Monitoring & Alerts, Reports, Business Rules, Audit Log, Settings). Sidebar mein na dikhne wale pages: /audit, /execution, /budget-bid, /search-terms/negatives, /keywords/insights, /account.

# Part A — Shell, Overview, Settings, Login/Account, Websites, Ads Accounts, Conversions

Permission ka short matlab (poore manual mein same): READ = koi bhi signed-in user (viewer bhi). RECOMMEND = analyst aur upar. APPROVE = approver aur upar. ADMIN = sirf admin. EXECUTE = special per-user switch (server CLI se hi milta hai, kisi role mein nahi hota).

---

## Global Header, Sidebar aur Sync now (Shell) — har page par (Module P01, P02, data-sync)
**Ye page kya hai:** Ye koi alag page nahi hai. Ye har page ke upar (header) aur left side (sidebar) mein hamesha dikhne wala frame hai. Isse aap website/ads account chunte hain, system ki health dekhte hain, ek click mein sab data sync karte hain aur sign out karte hain. Login page par ye frame nahi dikhta.
**Data kahan se aata hai:**
- Website dropdown -> P03 Websites (`GET /api/v1/websites`) -> sirf "active" websites aati hain (archived nahi). Har page badalne par list dobara load hoti hai, isliye nayi website add karte hi dropdown mein aa jaati hai.
- Ads account dropdown -> P04 (`GET /api/v1/websites/meta` ke andar active ads accounts ki list) -> jo accounts "Ads Accounts" page par add/active hain.
- Green/red pills -> P00 Foundation `GET /api/v1/foundation/health` -> sirf jab frame pehli baar load hota hai. Ye automatic refresh nahi hota; naya status dekhne ke liye browser page reload karein.
- Sidebar ke "P03", "P18" jaise chhote tag -> P00 module registry (`/foundation/modules`).
- Naam / Sign out -> P02 `GET /api/v1/auth/me`.
- Sync now -> P05 (Google Ads sync), P06 (GA4 + Search Console sync), P18 (monitoring check). Niche detail hai.
**Screen par kya dikhta hai:**
- **Sidebar (left):** upar "PPC Command Center / AI Google Ads Specialist". Neeche 6 groups. Jo section abhi "planned" status mein hota hai uske aage module ID (jaise `P15`) chhota likha aata hai. Active page highlight hota hai. Chhoti screen par sidebar chhup jaata hai; header ka `☰` button (label "Open navigation") se khulta hai, bahar click karne par band hota hai.
- **Header (upar):** left mein 2 dropdown, right mein status pills, "Sync now" button, user ka naam aur "Sign out".
- **Red strip:** agar backend band hai to header ke neeche red message aata hai: "Can't reach the backend (...)".
- **Status pills:**
  - `Checking backend…` (grey) = abhi check ho raha hai.
  - `Backend offline` (red) = backend se jawab nahi aaya.
  - `API ok` (green) = backend aur database dono theek. Agar database error ho to `API degraded` (amber) aata hai.
  - `Live execution locked` (green) = kill switch ON hai, matlab Google Ads mein live changes blocked hain. Agar kill switch band ho to `Kill switch OFF` (red) dikhta hai. Ye switch server ki setting se control hota hai, dashboard se nahi.
- **Sync now ke dauran:** button ke left mein chhoti status line: har job ke saath `…` (chal raha), tick (ho gaya) ya error ka chhota text. Poori list ke liye mouse us text par le jaayein (tooltip).
**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Website` dropdown (default `All websites (N)`; options "Name — location") | Aap kis website ko dekh rahe hain wo chunta hai. Choice browser mein yaad rehti hai (localStorage). Agar chuni hui website baad mein hat gayi to wapas "All websites" ho jaati hai. | P03 se list. Sirf aapke browser mein save hota hai, server par nahi. Kaun-kaun se page is choice ko use karte hain, ye har page ke liye code mein check nahi kiya; Conversions page use karta hai (neeche dekhein). | Sab |
| `Ads account` dropdown (default `All ads accounts`; options "Name (123-456-7890)") | Kis Google Ads account ko dekhna hai wo chunta hai. Same tarah browser mein yaad rehta hai. | P04 ke active accounts. | Sab |
| `☰` (Open navigation) | Chhoti screen par sidebar kholta hai. | Sirf screen layout. | Sab |
| Status pills (`API ok`, `Live execution locked`) | Sirf dikhane ke liye, click nahi hote. | P00 `/foundation/health`. | Sab dekh sakte hain |
| `Sync now` | Ek click mein Google Ads + GA4 + Search Console ka data laata hai, phir alerts check chalata hai, phir page reload karta hai. Poora order neeche "Sync now kaise chalta hai" mein hai. Chalte waqt button par `Syncing…` likha aata hai aur wo disable rehta hai. | Google Ads (read-only) -> P05; GA4 + Search Console (read-only) -> P06; monitoring -> P18. Sab local database mein save hota hai. | Analyst aur upar (RECOMMEND). Viewer ko "needs analyst permission" aata hai. |
| User ka naam / email (link) | `/account` page kholta hai. Mouse rakhne par email aur role dikhta hai. | P02 `/me`. | Sab |
| `Sign out` | Session khatam karke `/login` par bhej deta hai. | P02 `POST /auth/logout` (server se session delete). | Sab |

**Sidebar mein kaun sa link kya kholta hai:**

| Group | Link | Page kya hai (short) |
|---|---|---|
| Overview | `Overview` (`/`) | Home: setup progress (neeche alag section hai). |
| Sources | `Websites` (`/websites`) | Apni websites jodna aur scan karna (P03). |
| Sources | `Ads Accounts` (`/ads-accounts`) | Google Ads se connection (P04). |
| Sources | `Conversions` (`/conversions`) | GA4, Search Console, bookings, tracking health (P06). |
| Google Ads | `Campaigns`, `Ad Groups`, `Keywords`, `Search Terms`, `Ads & Assets` | Synced Google Ads data ke tables (P05 / P08 / P09). Inka detail doosre part mein hai. |
| Insights | `Bookings / Revenue`, `Landing Pages`, `Competitors`, `AI Recommendations` | Business insights aur AI suggestions (P13, P10, P11, P14). |
| Actions | `Campaign Builder`, `Approval Center`, `Experiments` | Naye campaigns/changes banana, approve karna, tests (P15, P16, P20). |
| Operations | `Monitoring & Alerts`, `Reports`, `Business Rules`, `Audit Log`, `Settings` | Alerts, reports, business rules, audit trail, system settings (P18, P19, P21, P22, P01). |

Agar kisi section ka page abhi bana nahi hai to wahan "Not built yet" aur owning module ka naam dikhta hai.

**Sync now kaise chalta hai (step by step, code ke hisaab se):**
1. Pehle 2 list laata hai: ads accounts (`ads-sync/accounts`) aur websites (`conversions/websites`). Dono mein kuch na ho to message aata hai: "Nothing to sync yet — connect an ads account or add a website first."
2. Har ads account ke liye ek job: "Google Ads <customer id>". Har website ke liye ek job: "GA4 + Search Console (<website name>)". Saari jobs ek saath (parallel) start hoti hain.
3. Google Ads sync "incremental" hota hai: pehli baar pichhle 90 din, uske baad pichhle successful sync ke aakhri din se 3 din pehle se aaj tak (conversions kuch din baad aati rehti hain, isliye 3 din dobara khinchte hain). Isme campaigns, ad groups, keywords, search terms aur ads aate hain. GA4 + Search Console hamesha pichhle 90 din (kal tak) refresh karta hai.
4. Har job ko har 2 second mein check kiya jata hai, adhiktam 5 minute tak. 5 minute mein na ho to us job ka note "timed out" hota hai. Agar us website/account ka sync pehle se chal raha ho to ye naya start nahi karta, chalte hue run ka intezaar karta hai.
5. Sab jobs khatam hone par har ads account ke liye monitoring check (`monitoring/accounts/<id>/run`) chalta hai taaki alerts naye numbers se update ho. Ye "best effort" hai: fail ho to bhi chhupchaap aage badh jaata hai.
6. Agar kam se kam ek job "success" ya "partial" hui to message "Synced — reloading…" aata hai aur lagbhag 1 second baad poora page reload ho jaata hai taaki sab screens par naye numbers dikhein. Agar saari jobs fail huin to "Sync failed — see details." dikhta hai aur page reload nahi hota; wajah tooltip mein hoti hai.
7. Website crawl (scan) Sync now mein shamil nahi hai; wo Websites page ke "Scan website" button se alag chalta hai.
**Kaise use karein:**
1. Upar "Website" aur "Ads account" dropdown se chunein kya dekhna hai (ya dono ko "All" rehne dein).
2. Sidebar se page kholein.
3. Naya data chahiye to header ka `Sync now` dabayein.
4. Status line mein tick aane tak ruken. Page apne aap reload hoga.
5. Kaam khatam hone par `Sign out` dabayein (shared computer par zaroor).
**Dhyan rakhne ki baat:**
- `Live execution locked` green hai matlab sab safe hai: dashboard Google Ads mein live changes nahi kar sakta. Agar kabhi `Kill switch OFF` red dikhe to developer/admin ko batayein.
- Sync now sirf data padhta hai (read-only). Ye Google Ads mein koi setting, budget ya bid nahi badalta.
- Header ki pills automatic update nahi hoti; reload par hi naya status aata hai.
- Agar GA4/Search Console sync fail ho (jaise service account file set nahi) to us website ka note error dikhata hai, lekin Ads sync theek hua to bhi page reload ho jaata hai.
- Dropdown ki choice sirf aapke browser mein save hoti hai; doosre computer par dobara chunni padegi.

---

## Overview — `/` (Module P01)
**Ye page kya hai:** Ye home page hai. Yahan 3 chhote tiles aur "Getting started" ki setup list milti hai. Business numbers (spend, bookings, revenue) is page par abhi nahi aate; code ke comment ke hisaab se wo baad ke modules (P05, P13, P19) se aayenge. Page ke neeche bhi yahi likha hai.
**Data kahan se aata hai:**
- Websites aur Ads accounts ke count -> header ke dropdown wala data (P03 / P04), har page load par.
- "Modules approved" -> P00 module registry (`/foundation/modules`): kitne modules ka status `approved_frozen` hai aur kitne `review` mein hain.
- "Getting started" ke har step ke aage ka status -> usi registry se us module ka status.
**Screen par kya dikhta hai:**
- Tile `Websites in scope`: agar header mein "All websites" chuna hai to total websites; kisi ek website ko chunne par `1`.
- Tile `Ads accounts`: connected ads accounts ki ginti (ye ginti header ke Ads account dropdown se nahi badalti).
- Tile `Modules approved`: jaise `20 / 24` aur neeche "N in review". Backend band ho to `—` aur "backend offline".
- Section `Getting started`: 5 numbered steps - Add websites (P03), Connect Google Ads (P04), Connect GA4 / bookings (P06), Import Ads history (P05), Run first audit (P07). Har step ke right mein module ID aur status (jaise `approved_frozen`).
**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Add websites` (link) | `/websites` kholta hai | Sirf navigation | Sab |
| `Connect Google Ads` (link) | `/ads-accounts` kholta hai | Sirf navigation | Sab (connect karne ke liye admin chahiye) |
| `Connect GA4 / bookings` (link) | `/conversions` kholta hai | Sirf navigation | Sab |
| `Import Ads history` (link) | `/campaigns` kholta hai | Sirf navigation | Sab |
| `Run first audit` (link) | `/recommendations` kholta hai | Sirf navigation | Sab |

**Kaise use karein:**
1. Naye setup mein upar se neeche steps follow karein: pehle Websites add karein.
2. Phir Ads Accounts mein Google Ads connect karein (admin chahiye).
3. Phir Conversions mein GA4 / Search Console / bookings jodein.
4. Header ka `Sync now` dabake Ads history laayein.
5. Last step mein AI Recommendations page par audit chalayein.
**Dhyan rakhne ki baat:**
- Ye checklist khud tick nahi hoti; sirf har step ka module-status dikhati hai. Ye status "module ready hai ya nahi" batata hai, "aapne setup kiya ya nahi" nahi.
- Is page par paise ya bookings ke numbers nahi hain; wo respective pages par dekhein.
- Page par koi button/form nahi hai, sirf links hain.

---

## Settings — `/settings` (Module P01)
**Ye page kya hai:** Sirf padhne wala (read-only) page. Ye batata hai system kis environment mein chal raha hai, database theek hai ya nahi, kill switch ON hai ya nahi, aur kaun se feature flags on/off hain. Yahan se kuch badla nahi ja sakta.
**Data kahan se aata hai:**
- P00 Foundation: `GET /api/v1/foundation/health` aur `GET /api/v1/foundation/flags`. Page khulte hi ek baar load hota hai.
- Flags ki on/off state server ki default + database override se nikalti hai. Flag badalne ka koi endpoint nahi hai; sirf server ke command line tool (`app.shared.flags_cli`) se badla jaata hai.
**Screen par kya dikhta hai:**
- Section `Environment`: `Environment` (jaise development/production), `Database` (`connected` ya `error`), `Execution kill switch` (`ON — live Google Ads changes are blocked` ya `OFF`). Backend band ho to "Backend unreachable: ..." red mein.
- Section `Feature flags` (note: "Read-only. All flags default off."): table columns - `Flag` (flag ka naam, jaise `crawler.enabled`), `Module` (kis module ka flag), `State` (`on` green / `off` grey), `Why` (state kahan se aayi: default ya override).
**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| Koi button ya input nahi | Page poori tarah read-only hai | P00 health + flags | Sab dekh sakte hain |

**Kaise use karein:**
1. Sidebar mein `Settings` kholein.
2. `Execution kill switch` dekhein: `ON` ka matlab live Google Ads changes blocked hain (safe).
3. Flags table mein dekhein jo feature (jaise website scan `crawler.enabled`) on hai ya off.
4. Kisi feature ko on/off karna ho to developer/admin se server par karwayein.
**Dhyan rakhne ki baat:**
- Users aur roles Settings mein nahi hain; wo `Account` page par (admin ke liye) hain.
- Agar `crawler.enabled` off hai to Websites par scan button kaam nahi karega.
- Code ke comment ke hisaab se flags ko dashboard se edit karna baad mein (audit trail ke saath) aayega; abhi nahi hai.
- Flags ki list code mein fixed nahi dikhi, jo backend bhejta hai wahi dikhta hai.

---

## Login — `/login` (Module P02)
**Ye page kya hai:** Sign in karne ka page. Iske bina baaki koi page nahi khulta: agar browser mein session cookie nahi hai to har page aapko apne aap `/login` par bhej deta hai (aur login ke baad wapas usi page par laata hai). Is page par sidebar/header nahi dikhta.
**Data kahan se aata hai:**
- Local database ke `users` aur `sessions` tables (P02). `POST /api/v1/auth/login`.
- Login ke baad ek secure cookie (`acc_session`) browser mein set hoti hai. Ye JavaScript se padhi nahi ja sakti (HttpOnly). Session 12 ghante chalta hai.
**Screen par kya dikhta hai:** Ek chhota card: "Sign in" heading, `Email` aur `Password` fields, red error line (agar galat ho), aur `Sign in` button.
**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Email` (input) | Aapka registered email. Server isko lowercase karke match karta hai. | Users table | Public |
| `Password` (input) | Aapka password (screen par chhupa rehta hai). | Server scrypt hash se compare karta hai; plain password save nahi hota. | Public |
| `Sign in` (button, ya `Signing in…`) | Login karta hai. Sahi hone par home `/` par bhejta hai (ya URL mein `next=` ho to us page par, sirf apni website ke andar ke path par). Galat hone par error dikhata hai. | `POST /auth/login` -> session banta hai, `last_login_at` update hota hai. | Public |

**Kaise use karein:**
1. `/login` kholein (ya koi bhi page kholein, wo khud yahan le aayega).
2. Apna `Email` likhein.
3. `Password` likhein.
4. `Sign in` dabayein.
5. Error aaye to neeche "Dhyan rakhne ki baat" dekhein.
**Dhyan rakhne ki baat:**
- Galat email ya galat password dono par ek hi message aata hai: "Invalid email or password". Deactivated user bhi yahi message dekhta hai.
- 5 galat koshish ke baad us email par 15 minute ke liye "Too many failed attempts. Try again in 15 minutes." aata hai. Ye ginti server ki memory mein hoti hai, isliye server restart hone par reset ho jaati hai.
- "Forgot password" ya "Sign up" ka button nahi hai. Password reset sirf server ke command line (`cli.py` ka reset-password) se hota hai; naya user admin banata hai. Google se sign-in abhi nahi hai.
- 12 ghante baad session expire hota hai, dobara login karna padega.

---

## Account — `/account` (Module P02)
**Ye page kya hai:** Yahan aap apni profile, role aur permissions dekhte hain. Agar aap admin hain to neeche "Users" section milta hai jahan se naye users bante hain aur roles/active status badalte hain.
**Data kahan se aata hai:**
- Aapki details -> P02 `GET /auth/me`.
- Users list -> `GET /auth/users` (sirf ADMIN). Roles list -> `GET /auth/roles`.
- Badlaav -> `POST /auth/users`, `PATCH /auth/users/{id}` (sirf ADMIN). Sab local database mein save hota hai.
**Screen par kya dikhta hai:**
- Upar `Account` heading aur `Sign out` button.
- Profile card: `Name`, `Email`, `Role`, `Permissions` (jaise `read, recommend`), `Google Ads execute` (`granted` ya `not granted (default)`).
- Sirf admin ko section `Users`. Table columns: `Email`; `Role` (dropdown); `Execute` (`yes`/`no`, sirf dikhane ke liye - ye special switch hai); `Active` (button `active`/`inactive`); `Last sign-in` (date-time ya `never`).
- Table ke neeche "Add user" form aur ek note: "Google Ads execute permission can only be granted from the server CLI, not here."
**Roles aur kya kar sakte hain (code ke hisaab se):**

| Role | Permissions | Practical matlab |
|---|---|---|
| `viewer` | read | Saare pages dekh sakta hai. Sync, scan, import, edit kuch nahi kar sakta. |
| `analyst` | read, recommend | Viewer ka sab + sync chalana (Sync now, GA4/Search Console sync), website scan, landing pages refresh, monitoring check chalana. (Doosre modules mein RECOMMEND se kya-kya hota hai, wo unke apne section mein dekhein.) |
| `approver` | read, recommend, approve | Analyst ka sab + website add/edit karna, GA4 event ka "Means" role set karna, bookings CSV import karna. (Approvals wale pages mein approve karna bhi isi se.) |
| `admin` | read, recommend, approve, admin | Approver ka sab + Google Ads connect/disconnect/add/enable-disable, users banana aur roles badalna. |

`execute` (live Google Ads changes) kisi role mein nahi hai. Ye har user ke liye alag switch hai, shuru mein sab ke liye band, aur sirf server ke command line se on hota hai (typed confirmation ke saath). Dashboard ya API se on nahi ho sakta.
**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Sign out` (page ke upar) | Session khatam karke `/login` par bhejta hai | `POST /auth/logout` | Sab |
| `Role` dropdown (har user ki row mein) | Us user ka role turant badal deta hai (koi confirm nahi poochta). Message aata hai "Role updated". | `PATCH /auth/users/{id}` | Admin |
| `active` / `inactive` (Active column ka button) | User ko active/inactive karta hai. Inactive hone par uske saare sessions delete ho jaate hain, matlab wo turant sign out ho jaata hai aur login nahi kar paata. Apni hi row ke liye ye button disabled hai. | `PATCH /auth/users/{id}` | Admin |
| `email` (input, required) | Naye user ka email | `POST /auth/users` | Admin |
| `name` (input) | Naye user ka naam (optional) | Same | Admin |
| Role dropdown (form mein; default `viewer`) | Naye user ka role: viewer / analyst / approver / admin | Same | Admin |
| `password (12+ chars)` (input, required) | Naye user ka shuruaati password, kam se kam 12 characters | Server scrypt se hash karke save karta hai | Admin |
| `Add user` | User banata hai. Safal hone par "User created" aata hai aur form khaali ho jaata hai. | `POST /auth/users` | Admin |

**Kaise use karein (naya user banana):**
1. `Account` page kholein (admin se login hona zaroori).
2. `Users` section ke form mein `email` likhein aur `name` likhein.
3. Role chunein. Shuru mein kam se kam role (`viewer`) dena behtar hai.
4. `password (12+ chars)` mein kam se kam 12 characters ka password likhein.
5. `Add user` dabayein, "User created" ka message dekhein.
6. Password us vyakti ko surakshit tareeke se bhejein (chat/email mein public nahi).
**Dhyan rakhne ki baat:**
- Password ka rule: kam se kam 12 characters. Aur koi rule (capital/number) code mein nahi dikha.
- Safety rules: aap khud ko deactivate nahi kar sakte; aakhri active admin ka role ghatana ya use deactivate karna blocked hai ("Cannot remove the last active admin"). Same email do baar nahi ban sakta.
- Is page se kisi user ka password badalna, naam edit karna ya user delete karna nahi ho sakta (backend naam badalne ko support karta hai par screen par option nahi hai). Delete ka option hai hi nahi, sirf `inactive`.
- Role badalne par permissions har request par database se aati hain, isliye naya role agle request se lagu ho jaata hai (code ke hisaab se anumaan).
- Viewer/analyst/approver ko "Users" section dikhta hi nahi.

---

## Websites (list) — `/websites` (Module P03)
**Ye page kya hai:** Yahan aap apni saari websites (jaise Corporate Cars Melbourne) ki list dekhte hain aur nayi website jodte hain. Har website ko uske Google Ads account, GA4 aur Search Console se link kiya jaata hai taaki baaki saare pages us website ka data sahi jagah dikha sakein.
**Data kahan se aata hai:**
- Local database (P03 `websites` table) -> `GET /api/v1/websites` aur `GET /api/v1/websites/meta`.
- "Pages scanned" aur "Last scan" -> website scan (crawl) ke natije jo P03 local database mein rakhta hai.
- Ads account dropdown ki list -> P04 ke active accounts.
**Screen par kya dikhta hai:**
- Header mein `+ Add website` button (form khula ho to chhup jaata hai).
- Har website ka card: naam, domain, right mein "main service · city". Card ke andar: `Google Ads` (account number `123-456-7890` ya amber `not linked`), `GA4` (property ID ya `—`), `Pages scanned` (jaise `50 (7 with issues)`), `Last scan` (date · status, ya `never`).
- Agar ek bhi website nahi hai to "No websites yet" aur `+ Add your first website`.
**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `+ Add website` / `+ Add your first website` | Add website ka form kholta hai | Sirf screen | Button sab ko dikhta hai; save sirf approver+ kar sakta hai |
| Website card (poora card link hai) | Us website ka detail page `/websites/<id>` kholta hai | P03 | Sab |
| Form: `Website name *` | Dashboard mein dikhne wala naam (zaroori) | `POST /websites` | Approver+ |
| Form: `Domain *` | Website ka address, jaise `https://corporatecarsmelbourne.com.au`. `https://`, `www.` ya aakhri `/` likhna zaroori nahi; system khud `www.` hata kar domain save karta hai. Galat domain par error aata hai. Ek domain do baar nahi jud sakta. Baad mein Edit mein ye field badal nahi sakte. | Same | Approver+ |
| Form: `Main service` | Free text (suggestions: Chauffeur, Corporate, Airport transfer, Wedding, Events / formals, Cruise transfer, Tours, Limousine) | Same | Approver+ |
| Form: `City / area` | Shehar/ilaka, jaise Melbourne | Same | Approver+ |
| Form: `Google Ads account` | Is website ko kaun sa ads account jodna hai (`— not linked —` bhi chun sakte hain). List sirf unhi accounts ki hai jo Ads Accounts page par active hain. | Same. Is link se Ad landing pages aur Conversions ke ads-vs-GA4 checks chalte hain. | Approver+ |
| Form: `Time zone` | 6 Australian time zones (Melbourne default, Sydney, Brisbane, Adelaide, Perth, Hobart) | Same | Approver+ |
| Form: `GA4 property ID` | Sirf digits. GA4 mein Admin -> Property details mein milta hai. Optional. Letters daalne par error aata hai. | Same. Conversions sync isi ID se GA4 padhta hai. | Approver+ |
| Form: `Search Console property` | Search Console ka address, jaise `https://corporatecarsmelbourne.com.au/`. Optional. | Same. Conversions sync isi se organic searches laata hai. | Approver+ |
| Form: `Notes` | Apne liye free notes | Same | Approver+ |
| `Save` (ya `Saving…`) | Website banata hai aur seedha uske detail page par le jaata hai | `POST /websites` | Approver+ |
| `Cancel` | Form band karta hai, kuch save nahi hota | - | Sab |

**Kaise use karein (nayi website jodna):**
1. Pehle `Ads Accounts` page par Google Ads connect aur account add kar lein (taaki dropdown mein dikhe).
2. `Websites` mein `+ Add website` dabayein.
3. `Website name` aur `Domain` bharein. Main service aur City bhi bharein.
4. `Google Ads account` chunein, aur agar hai to `GA4 property ID` aur `Search Console property` daalein.
5. `Save` dabayein; detail page khulega.
6. Wahan `Scan website` chalayein.
**Dhyan rakhne ki baat:**
- Website add/edit karne ke liye approver ya admin role chahiye. Analyst/viewer ko "Requires 'approve' permission" jaisa error milega.
- Website ko "archive" karne ki capability backend mein hai (status archived hone par wo list aur header dropdown se ghaayab ho jaati hai), lekin screen par archive ka button nahi hai. Code mein sirf API se possible hai.
- Ads account link karne se pehle account "active" hona chahiye, warna "Unknown or inactive Google Ads account" error aata hai.
- GA4/Search Console ID dene se kuch apne aap jud nahi jaata; asli sync Conversions page se hota hai aur Google ke service account ko un properties ka access dena padta hai.

---

## Website Detail — `/websites/<id>` (Module P03)
**Ye page kya hai:** Ek website ka poora health-check page. Yahan aap website ko scan (crawl) karte hain, har page ki problems dekhte hain, aur dekhte hain ki aapke Google Ads ads kin pages par ja rahe hain aur wo pages theek hain ya toot chuke hain.
**Data kahan se aata hai:**
- Website scan -> P03 ka apna crawler aapki website ke public pages padhta hai (robots.txt maanta hai). Natije local database mein save.
- "Ad landing pages" -> Google Ads se synced ads ka local data (P05, pichhle 90 din ke ads ke final URLs) ko scanned pages se milaya jaata hai. Ye live Google se nahi aata; isliye pehle Ads data sync (header ka `Sync now`) hona chahiye.
- Service mention check -> P21 Business Rules ki "services" list.
**Screen par kya dikhta hai:**
- Header: website ka naam, dropdown `Pages to scan`, button `Scan website`, button `Edit`.
- Line ke neeche: `← All websites` link, domain link, Google Ads ID, GA4 ID, aur last scan ka time (status aur source: sitemap ya link crawl).
- Amber banner agar scan band hai: "Website scanning is switched off (feature flag crawler.enabled). Ask your admin to enable it."
- 4 tiles: `Pages scanned`, `Pages with issues`, `Ad landing pages`, `Landing pages with problems` (broken ya not scanned).
- 3 tabs: `Issues`, `All pages`, `Ad landing pages`.

**Tab `Issues`:** Problems ki list, jis problem wale pages zyada hon wo upar. Har problem par click karke un pages ke links dekhein. Pehle scan se pehle "Not scanned yet" likha hota hai. Problems ka matlab:

| Issue (screen par text) | Kab aata hai | Kyun zaroori hai |
|---|---|---|
| Page returns an error status | Page ne error diya (404, 500 jaise) ya khula hi nahi. Is page par baaki checks nahi chalte. | Ad is page par bheje to paisa barbaad. |
| Page is set to noindex | Page par Google ko "mujhe list mat karo" ka tag hai | Organic search mein nahi aayega |
| Missing `<title>` | Page ka title nahi | Search aur quality ke liye zaroori |
| Missing meta description | Chhota description tag nahi | Google result ka text kamzor |
| No H1 heading | Page par mukhya heading nahi | Page ka topic saaf nahi |
| More than one H1 | Ek se zyada mukhya heading | Structure gadbad |
| Very little text (< 200 words) | 200 se kam shabd | Ad landing page kamzor lag sakta hai. JavaScript se bane pages bhi yahan kam text wale dikhte hain, kyunki crawler JavaScript nahi chalata. |
| No booking / quote / call button found | Book / quote / call / enquire wala koi button/link nahi mila | Visitor ko action lene ka raasta nahi |
| No enquiry form and no phone number | Na form, na phone number | Customer sampark nahi kar sakta |
| Not set up for mobile (no viewport tag) | Mobile ke liye viewport tag nahi | Phone par kharab dikhega |
| Slow response (> 3 s) | Server ne 3 second se zyada liye | Slow page se customers bhaag jaate hain |
| No service you offer is mentioned | Page ke title/headings/text mein Business Rules ki koi service nahi mili | Ad aur page ka message match nahi karta |

**Tab `All pages`:** table, har scanned page ki ek row. Columns: `Page` (path; agar status 200 nahi to code laal mein), `Title / H1`, `Words` (shabdon ki ginti), `Book/quote` (tick = book/quote/call button mila, cross = nahi), `Form` (form hai), `Phone` (phone number ya tel link hai), `Services found` (page par mile services, pehle 4), `Speed` (jawab dene ka time; 3 s se zyada laal), `Issues` (us page ki problems ya `none`).

**Tab `Ad landing pages`:** upar text: "Final URLs of this site's ads (last 90 days, from the linked Google Ads account)" aur `Refresh` button. Table columns: `Landing page` (ad ka final URL aur page title), `Status`, `Ads` (is URL par kitne ads jaate hain), `Used by` (campaign › ad group, pehle 3), `Page issues`. Status ka matlab: `OK` (page scan hua aur theek), `Broken` (page error deta hai), `Not scanned` (is site ka page hai par scan mein nahi aaya; scan badhao ya dobara scan karo), `Other domain` (ad kisi aur website par ja raha hai). Sorting: broken pehle, phir not scanned, other domain, ok. Agar website ke saath ads account link nahi hai to "Link a Google Ads account (Edit) to see ad landing pages." aata hai. Agar ads nahi mile to "No ads found — sync the account on the Campaigns page, then scan."
**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Pages to scan` dropdown (`up to 25 / 50 / 100 / 200 pages`; default 50) | Ek scan mein kitne pages tak dekhne hain. (Backend 300 tak maanta hai, par screen par 200 tak.) | Scan request ke saath jaata hai | Sab dekh sakte hain; scan RECOMMEND se |
| `Scan website` (running mein `Scanning… N`) | Scan background mein shuru karta hai. Page har 2.5 second mein progress dekhta hai. Khatam hone par message "Scan success/partial/failed: N page(s)." Agar us site ka scan pehle se chal raha ho to naya shuru nahi hota, chalte wale ko hi dikhata hai. Jab tak flag off ho ye button disabled rehta hai. | `POST /websites/{id}/crawl` -> crawler -> pages local DB mein. Scan ke baad landing page mapping apne aap refresh hoti hai. | Analyst aur upar (RECOMMEND), aur flag `crawler.enabled` on ho |
| `Edit` | Website ka form kholta hai (domain ke alawa sab badal sakte hain: naam, service, city, ads account, time zone, GA4, Search Console, notes) | `PATCH /websites/{id}` | Approver+ |
| Form `Save` / `Cancel` | Badlaav save karta hai / band karta hai | Same | Approver+ / Sab |
| Tabs `Issues`, `All pages`, `Ad landing pages` | Section badalte hain | Local DB | Sab |
| Issue ke naam par click (expand) | Us problem wale pages ke links dikhata hai (naye tab mein khulte hain) | Local DB | Sab |
| `Refresh` (landing pages tab) | Ads ke final URLs ko scanned pages se dobara milata hai (naya scan nahi chalata) | `POST /websites/{id}/landing-pages/refresh` | Analyst+ |
| `← All websites`, domain link | List par wapas / asli website naye tab mein | Navigation | Sab |

**Kaise use karein (website scan aur check):**
1. `Websites` se website ka card kholein.
2. `Pages to scan` chunein (pehli baar 50 theek hai) aur `Scan website` dabayein.
3. Button par `Scanning… N` dikhega; page khula rakhna zaroori nahi, scan server par chalta rehta hai.
4. Khatam hone par `Issues` tab dekhein: sabse upar wali problem sabse zyada pages par hai.
5. `Ad landing pages` tab mein `Broken` aur `Not scanned` wali rows pehle theek karein (broken page par ad nahi chalna chahiye).
6. Pages sahi karne ke baad dobara `Scan website` chalayein.
**Dhyan rakhne ki baat:**
- Scan polite hai: `robots.txt` maanta hai, sirf usi website ke HTML pages dekhta hai, pehle sitemap se URLs leta hai (na ho to links follow karta hai), do requests ke beech 0.5 second ruka rehta hai, har page ko 15 second tak deta hai. JavaScript nahi chalata, isliye JS-only pages patle dikh sakte hain.
- Feature flag `crawler.enabled` shuru mein off hota hai. MODULE.md ke hisaab se ise 2026-09-28 ko on kiya gaya tha; abhi live state `Settings` page ya is page ke amber banner se pata chalegi. Flag admin server par command line se badalta hai.
- Scan status: `success` (sab theek), `partial` (kuch errors ke saath), `failed` (ek bhi page theek nahi mila). Agar scan 30 minute se zyada "running" rahe to use "failed (interrupted)" maan liya jaata hai.
- Scan sirf padhta hai; aapki website mein kuch nahi badalta aur Google Ads mein bhi kuch nahi badalta.
- Scan dobara chalane par pehle se maujood pages (same URL) update hote hain. Jo pages ab nahi milte unka delete hona code mein clear nahi hai.

---

## Ads Accounts — `/ads-accounts` (Module P04)
**Ye page kya hai:** Yahan aap Google Ads ko dashboard se jodte hain. Ek Google login connect hota hai, uske neeche ke ads accounts dhoondhe jaate hain, aur jo chahiye wo dashboard mein add kiye jaate hain. Ye connection poori tarah read-only hai: dashboard Google Ads se sirf data padh sakta hai, kuch badal nahi sakta.
**Data kahan se aata hai:**
- Google Ads (Google OAuth + Google Ads API, sirf SELECT-type reads) -> P04. Naam, currency, time zone aur "manager" ya nahi, jaisi details discover karte waqt Google se aati hain.
- Connections aur added accounts local database mein (`connections`, `ads_accounts`). Refresh token encrypt hokar save hota hai aur kabhi screen par nahi aata.
- Setup ke ticks -> server ki config (OAuth client ID/secret aur developer token set hain ya nahi).
**Screen par kya dikhta hai:**
- Header mein `Connect Google Ads` button.
- Top par message banner (hara/laal): connect hone par "Google account connected. Now find and add your ads accounts below." ya Google se laaya hua error.
- Card `Setup`: do checks (tick/cross): Google OAuth client, Google Ads developer token. Cross ho to saath mein "add to backend/.env" likha aata hai. Neeche: API version, "read-only", redirect URI.
- Card `Google connections`: har connected Google login ka email, status (`active` hara, baaki laal) aur koi `last_error`. Revoked connection list mein nahi dikhte.
- Card `Accounts this Google login can read` (Find accounts dabane ke baad hi): table columns - `Account`, `Customer ID` (xxx-xxx-xxxx), `Currency · TZ`, `Type` (`manager` / `direct` / `via <manager ID>`), aur action.
- Card `Accounts in this dashboard`: added accounts ki table: `Account`, `Customer ID`, `Currency · TZ`, `Type` (yahan `active` ya `disabled`), aur Enable/Disable button. Neeche note: "Read-only access. This dashboard cannot change anything in Google Ads."
**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Connect Google Ads` | Google ke consent screen par le jaata hai. Wahan aap access dete hain, phir wapas isi page par aate hain. Agar Setup mein cross hai to ye button disabled (halka) hota hai. Scopes: Google Ads (adwords), email. | `GET /ads-connection/oauth/start`. Refresh token encrypt hokar `connections` mein. State 10 minute valid, same admin aur same browser ke liye. | Admin |
| `Test` (`Checking…`) | Connection ab bhi chal raha hai ya nahi check karta. Safal par "Connection is working." Fail par red error. | `POST /connections/{id}/check` -> Google se accessible accounts ki list padhta hai | Admin |
| `Find accounts` (`Searching…`) | Is Google login se jitne ads accounts padhe ja sakte hain (manager ke neeche ke bhi) unki list laata hai | `GET /connections/{id}/discover` -> Google Ads read | Admin |
| `Add` (discover table mein) | Us account ko dashboard mein jodta hai. Pehle ek read-query se verify karta hai. Safal par "<naam> added." aur row mein `added` aa jaata hai. Manager accounts par ye button nahi hota ("manager — add its accounts" likha aata hai); unke andar ke accounts add karein. | `POST /ads-connection/accounts` -> `ads_accounts` table (manager se mila ho to uska login ID bhi save) | Admin |
| `Disconnect` | Pehle confirm poochta hai ("Disconnect this Google account? Its ads accounts will be disabled."). Haan par: Google par grant revoke karne ki koshish, saved token delete, connection `revoked`, aur uske saare ads accounts `disabled`. | `POST /connections/{id}/disconnect` | Admin |
| `Disable` / `Enable` (accounts table mein) | Account ko dashboard mein band/chalu karta hai. Disabled account Sync now aur dropdowns/website link list se hat jaata hai (kyunki wo sirf active accounts lete hain). Google Ads mein koi badlaav nahi hota. | `PATCH /ads-connection/accounts/{id}` | Admin |

**Kaise use karein (pehli baar connect karna):**
1. Admin se login karein aur `Ads Accounts` kholein.
2. `Setup` card mein dono tick hone chahiye. Cross ho to developer se `backend/.env` mein values daalne ko kahein.
3. `Connect Google Ads` dabayein, sahi Google account chunein aur access allow karein.
4. Wapas aane par `Find accounts` dabayein.
5. Jo accounts chahiye unke saamne `Add` dabayein (manager/MCC ke andar ke accounts bhi aate hain).
6. `Accounts in this dashboard` mein status `active` dekhein, phir header ka `Sync now` chalayein.
**Dhyan rakhne ki baat:**
- Read-only guarantee: code mein koi mutate/edit call nahi hai, search sirf SELECT hota hai. Isliye dashboard se ads, budget ya bids nahi badal sakte; live changes ke liye alag kill switch aur execute permission ka system hai.
- Sirf admin ye sab kar sakta hai. Doosre roles page dekh sakte hain par button dabane par permission error aayega.
- Disconnect ke baad token delete ho jaata hai. Us connection ke accounts ko `Enable` karne par bhi data tabhi aayega jab dobara `Connect Google Ads` karein (ye code padh kar anumaan hai, alag se test nahi kiya). Pehle se synced data hatane ka code disconnect mein nahi dikha.
- Manager (MCC) account khud add nahi hota; uske bacche accounts add hote hain.
- Agar "Test" fail ho, wajah (jaise revoked grant, developer token missing, permission nahi) red message mein dikhti hai.

---

## Conversions & Analytics — `/conversions` (Module P06)
**Ye page kya hai:** Yahan aap dekhte hain ki website par kitne log aaye (GA4), free Google search se kaun aaya (Search Console), aur kitni asli bookings aayi (CSV import). Ye page tracking ki galtiyan bhi pakadta hai (jaise form submit track nahi ho raha). Teen alag kism ke numbers alag rakhe jaate hain: observed, attributed, confirmed (neeche dekhein).
**Data kahan se aata hai:**
- GA4 Data API (read-only, service account) -> P06 -> sirf jab aap `Sync GA4 & Search Console` dabate hain ya header ka `Sync now`. Traffic channel-wise aur events din-wise save hote hain.
- Google Search Console (read-only, service account) -> P06 -> usi sync mein. Din-wise query, clicks, impressions, position.
- Bookings -> aapki CSV file (upload ke waqt) -> local database. Driver App se live connection abhi nahi bana (MODULE.md mein pending).
- Tracking health ke ads-vs-GA4 checks -> Google Ads ka synced data (P05) local database se.
- Page kholne par Google ko seedha call nahi jaata; sab local database se dikhta hai.
**Teen kism ke numbers:**
- **Observed (dekha gaya):** GA4 aur Search Console ke numbers: visits, key events, searches. Ye is page par dikhte hain.
- **Attributed (Google Ads ne apne naam kiye):** Google Ads ke conversions. Ye Ads pages (P05) par hote hain; is page par sirf tracking-health message mein tulna ke liye aate hain.
- **Confirmed (pakke):** bookings CSV ki real jobs aur revenue. Sabse bharosemand number.
**Screen par kya dikhta hai:**
- Header: `Website` dropdown (sirf tab dikhta hai jab 1 se zyada website hon), date range buttons `7d`, `30d`, `90d`, aur `Sync GA4 & Search Console`.
- Line: domain, GA4 ID (ya "not linked"), Search Console linked/not linked, aur last sync ka time aur status.
- Agar koi website nahi: "Add a website with its GA4 property on the Websites page first."
- 3 tab-buttons: `Google Analytics (GA4)`, `Search Console`, `Bookings`. Har tab par laal "N problem(s)" aata hai agar us tab ki critical ya warning health issue ho.
- Har tab ke upar us tab ki tracking health list (neeche detail).

**Tab `Google Analytics (GA4)`:**
- Tiles: `Visits (sessions)` (kul visits), `Engaged visits` (note mein %: jo 10 second+ ruke ya 2+ pages dekhe), `Conversions (key events)` (GA4 mein key event mark kiye hue kaam; 0 hone par laal aur "nothing is being recorded").
- Table `Where visitors come from`: `Channel` (Paid Search = aapke Google Ads, Organic Search = free Google, Direct, Social...), `Visits`, `Engaged`, `Conversions`.
- Table `What visitors did (GA4 events)`: `Event` (GA4 event ka naam aur chhota matlab, jaise page_view = page khula), `Count` (kitni baar), `Key?` (tick = GA4 mein key event hai), `Means` (aap batate hain ye event kya hai).
- `Means` dropdown ke options: `— not set —`, `Lead (enquiry / quote / call)`, `Booking`, `Micro step`, `Ignore`. Jab tak aap set na karein, system ka suggestion option ke aage `(suggested)` likh kar dikhata hai. Suggestion naam se banta hai: purchase/booking_complete/payment jaise naam = booking; form_submit/generate_lead/quote/enquiry/call jaise = lead; form_start/click/scroll/download = micro step; page_view/session_start/first_visit/user_engagement = ignore; baaki = micro step.

**Tab `Search Console`:**
- Tiles: `Clicks from Google search` (free visits), `Times shown in Google` (impressions), `Click rate` (clicks / impressions), `Average position` (1-10 = pehla page; 10 se upar laal).
- Table `Searches that show your site`: `Search` (kya type kiya gaya), `Clicks`, `Shown`, `Click rate`, `Avg position` (10 se upar amber = page 2 ya neeche). Clicks ke hisaab se sabse upar ki 50 searches dikhti hain. Average position tile top queries ka impression-weighted average hai.

**Tab `Bookings`:**
- Tiles: `Confirmed bookings` (cancel/void/refund chhodkar), `Revenue` (AUD), `From Google Ads` (ginti aur revenue).
- "Google Ads" wali booking tab maani jaati hai jab: CSV mein `gclid` ho, ya `utm_source` = google aur `utm_medium` = cpc/ppc/paid ho, ya `channel` mein "google ads"/"adwords" likha ho.
- `Upload bookings CSV` ke baad result line: "N new · N updated · N skipped", errors (pehle 3) aur "ignored columns".
- Table `Channel`, `Bookings`, `Revenue` (channel-wise, revenue ke hisaab se).
- CSV ke accepted columns: **zaroori** - booking id (`booking_id` / `id` / `booking` / `booking_ref` / `reference` / `ref` / `job_id`), date booked (`booked_on` / `booking_date` / `created_at` / `created` / `date_booked` / `date`), amount (`amount` / `total` / `price` / `fare` / `revenue` / `value`). **Optional** - pickup date (`service_date` / `pickup_date` / `trip_date` / `job_date`), `status` / `booking_status`, `service_type` / `service` / `type`, `website` / `site` / `domain` / `brand`, `channel` / `source_channel` / `how_heard` / `lead_source`, `gclid`, `utm_source`, `utm_medium`, `utm_campaign`. Header ke spaces underscore ban jaate hain aur capital/small farq nahi padta. Dates: `2026-09-01`, `1/9/2026`, `1/9/26`, `01-09-2026` (din pehle). Amount mein `$` aur commas hat jaate hain. Naam, email, phone wale columns padhe hi nahi jaate, kabhi save nahi hote, aur "ignored columns" mein dikh jaate hain.

**Tracking health issues (red/amber/grey cards, critical pehle):**

| Title (screen par) | Severity | Kab aata hai | Matlab / kya karein |
|---|---|---|---|
| GA4 not linked | warning | Website par GA4 property ID nahi | Websites page par Edit karke GA4 ID daalein |
| No GA4 data yet | warning | GA4 linked hai par is range mein visits 0 | Sync chalayein; phir bhi khaali ho to service account ko GA4 property par Viewer access dein |
| GA4 data only starts on <date> | info | GA4 ka data range ke shuru se 6 din se zyada baad shuru hua | Us tareekh se pehle ke numbers ki tulna na karein |
| GA4 records no conversions (key events) | critical | 50+ visits par 0 key events | GA4 mein apna enquiry/booking event "Mark as key event" karein, warna pata nahi chalega kaun sa traffic leads deta hai |
| Form starts are tracked, but not form submissions | critical | `form_start` event hai par koi submit/lead event nahi | Form ke thank-you step par `generate_lead` (ya form_submit) event lagwayein |
| No GA4 event is marked as a lead or booking here | warning | Events hain par kisi ko aapne `Lead`/`Booking` set nahi kiya | `Means` column se sahi event ko Lead/Booking set karein |
| Far fewer GA4 paid sessions than Google Ads clicks | warning | Ads account linked hai, 30+ ad clicks, aur GA4 Paid Search visits un clicks ke 60% se kam | Har landing page par GA4 tag, auto-tagging, consent banner, aur ads ka dusre domain par jaana check karein |
| Google Ads counts conversions that GA4 doesn't | warning | Google Ads mein conversions hain par GA4 mein 0 key events | Google Ads ke conversion actions (Tools -> Conversions) dekhein, shayad wo page view ya call hain, asli lead nahi |
| Search Console not linked | info | Website par Search Console property nahi | Websites page par daalein |
| No bookings imported | info | Is range mein koi booking nahi | Bookings CSV upload karein |

Critical tracking issues Monitoring & Alerts (P18) ko bhi alert ke roop mein jaate hain (P18 MODULE.md ke hisaab se).
**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Website` dropdown | Kaun si website dekhni hai. Shuru mein header ke website selector wali website khulti hai (nahi to pehli). | `GET /conversions/websites` | Sab |
| `7d` / `30d` / `90d` | Dikhane ki avadhi: kal tak ke itne din. Sirf display badalta hai, naya data nahi laata. | `GET /websites/{id}/overview?days=` local DB | Sab |
| `Sync GA4 & Search Console` (`Syncing…`) | Pichhle 90 din (kal tak) ka GA4 traffic, GA4 events aur Search Console data Google se laakar us avadhi ka purana data replace karta hai. Har 2 second mein progress dekhta hai; khatam par "Sync success/partial/failed ..." message aur numbers refresh. Chalte waqt disabled. | `POST /websites/{id}/sync` -> Google (read-only) -> local DB | Analyst+ |
| Tab buttons (GA4 / Search Console / Bookings) | Section badalte hain | Local DB | Sab |
| `Means` dropdown (har event ki row mein) | Event ka role save karta hai: Lead, Booking, Micro step ya Ignore. Turant save hota hai. `— not set —` chunne se kuch nahi hota (role hata nahi sakte). | `PUT /websites/{id}/mappings` | Approver+ |
| `Upload bookings CSV` (file chooser, `.csv`) | File chunte hi import chalta hai (alag "submit" button nahi). Naye bookings bante hain, wahi booking ID dobara aaye to update hoti hai. | `POST /conversions/bookings/import` (max 5,000,000 characters). Har row ki website: CSV ke `website` column ke domain se, nahi mila to abhi chuni hui website. | Approver+ |
| Health card | Sirf padhne ke liye | Local DB | Sab |

**Kaise use karein (pehli baar data lana):**
1. `Websites` par us website ka `GA4 property ID` aur `Search Console property` daalein. Server ke service account ko un properties par access chahiye (developer ka kaam).
2. `Conversions` kholein, `Website` chunein.
3. `Sync GA4 & Search Console` dabayein aur "Sync success" ka intezaar karein.
4. `Google Analytics (GA4)` tab par `Means` column mein enquiry/booking wale event ko `Lead` ya `Booking` set karein (approver chahiye).
5. Laal/amber health cards padhein aur unke hisaab se GA4/website tracking theek karwayein.
6. `Bookings` tab par apna bookings CSV `Upload bookings CSV` se daalein aur "N new · N updated" result dekhein.
**Dhyan rakhne ki baat:**
- Sync ke liye website par kam se kam ek: GA4 ID ya Search Console property honi chahiye, warna error aata hai. Agar server par service account ki file set nahi hai to error "GOOGLE_SERVICE_ACCOUNT_FILE is not set in backend/.env" aata hai.
- Sync status `partial` ka matlab kuch hissa aaya, kuch fail; message mein wajah hoti hai.
- Date range buttons naya data nahi khinchte. Naya data sirf Sync se aata hai.
- Bookings: cancelled, canceled, void, refunded status wali rows ginti/revenue mein nahi judti. Agar `status` column hi nahi hai to sab "confirmed" maani jaati hain.
- Is page par attributed (Google Ads conversion) alag tile nahi hai; Ads ke numbers Google Ads pages par dekhein.
- Mapping (`Means`) is page par sirf health check "No GA4 event is marked as a lead or booking" ko asar karti hai; doosre modules (reports/funnel) is mapping ko kaise use karte hain, wo yahan code mein check nahi kiya.

# Part B — Ads data, Keywords, Audit, Recommendations, Business Rules

## Permissions ka quick guide (is part ke liye)
- **READ** = koi bhi signed-in user (viewer bhi) page dekh sakta hai.
- **RECOMMEND** = analyst aur usse upar: `Sync now`, `Run analysis`, `Run audit`, `Refresh from latest audit`, `Generate plan`, audit issue ka `Dismiss` / `Restore`.
- **APPROVE** = approver aur usse upar: negative keywords `Accept` / `Reject`, recommendation Accept / Reject / Mark done, Business Rules `Save rules` / `Restore`.
- Frontend mein buttons permission ke hisaab se chhupte nahi hain. Agar aapke paas permission nahi hai to button dabane par red error message aata hai.

## Ads data pages ka common top bar (Campaigns, Ad Groups, Keywords, Search Terms, Negative keyword suggestions, Keyword insights)
Ye sab pages ek hi "frame" (`AdsDataFrame`) mein khulte hain, isliye upar ka bar sab par same hai:
- **Account picker (dropdown):** sirf tab dikhta hai jab 1 se zyada Google Ads account connected ho. Aapka chuna hua account aur date range browser mein yaad rehta hai (isi computer ke browser mein).
- **`7d` / `30d` / `90d` buttons:** table aur tiles kitne din ka data dikhayein. Default `30d`. Ye sirf screen ka filter hai, Google se naya data nahi mangta.
- **`Sync now`:** Google Ads se latest data local database mein laata hai. Chalte waqt button par "Syncing…" likha aata hai aur disabled rehta hai. Khatam hone par page apne aap refresh ho jaata hai.
- **Last sync line:** account ka naam, customer ID (xxx-xxx-xxxx), "last sync 5 min ago (success)". Status success / partial / failed / running mein se ek hota hai. "partial" ka matlab kuch steps chale, kuch fail hue. Agar koi step fail hua to red text mein error dikhta hai.
- Agar koi account connected nahi: message "No Google Ads account connected" aur `Ads Accounts` page ka link.
- Agar account hai par kabhi sync nahi hua: "No data yet. Click Sync now to import the last 90 days."

**Sync kaise kaam karta hai (MODULE.md + code):**
- Pehli baar: pichhle 90 din. Uske baad incremental: last synced din se 3 din pehle se aaj tak (taaki der se aaye conversions pakad mein aa jayein). Dobara chalane se data double nahi hota.
- Steps: campaigns, ad groups, keywords, search terms, ads. Ek step fail ho to baaki chalte hain (run "partial" hota hai).
- Ek account par ek hi sync ek time par chalta hai. 30 minute se zyada "running" rahe to "failed" mark ho jaata hai.
- Ye sync **read-only** hai: Google Ads se sirf padhta hai, Google Ads mein kuch change nahi karta.
- Automatic scheduled ads-sync MODULE.md ke hisaab se abhi built nahi hai (command line + Windows Task Scheduler se chal sakta hai). Code mein koi aur automatic ads-sync nahi mila. Isliye `Sync now` dabana padta hai.

**Metrics ka matlab (Google Ads ke daily numbers ka jod):**

| Naam | Matlab |
|---|---|
| Spend / Cost | Chuni hui period mein Google ko diya gaya paisa (account ki currency mein, jaise AUD) |
| Clicks | Kitni baar logon ne ad par click kiya |
| Impr. (Impressions) | Aapka ad kitni baar dikha |
| CTR | Clicks / Impressions. Kitne % logon ne dekh kar click kiya |
| Avg CPC | Cost / Clicks. Ek click ka average daam |
| Conv. (Conversions) | Google Ads ke hisaab se kitne enquiry/booking-type actions hue (decimal ho sakta hai, jaise 2.5) |
| Cost / conv. | Cost / Conversions. Ek conversion ka average kharcha |
| Conv. rate (sirf Campaigns ke tile mein) | Conversions / Clicks |

- Agar divide karne wala number 0 hai (jaise 0 clicks) to Avg CPC / CTR wagairah "—" dikhta hai.

**Status ke matlab:**
- `Enabled` (hara gol): chal raha hai.
- `Paused`: pause kiya hua hai.
- `Removed`: Google Ads mein delete ho chuka hai. Code mein: jo cheez Google ki "non-removed" list mein ab nahi aati, use yahan REMOVED mark kar diya jaata hai.
- `Campaign paused` (Ad Groups page): ad group khud enabled ho sakta hai par uski campaign paused hai, isliye wo chal nahi sakta. Isi tarah `Campaign removed` = uski campaign delete ho gayi.
- Ad group ka "Status" asal mein "effective status" hai: ad group ka apna status AUR campaign ka status dono dekh kar nikalta hai.

---

## Campaigns — `/campaigns` (Module P05)
**Ye page kya hai:** Aapke Google Ads account ki saari campaigns ka performance ek jagah. Upar total tiles, uske neeche daily spend chart, aur phir campaign-wise table.

**Data kahan se aata hai:**
- Google Ads -> P05 ads_sync -> local database. `Sync now` dabane par update hota hai (pehle 90 din, phir incremental).
- Page sirf local database padhta hai. Page kholne se Google ko call nahi jaati.

**Screen par kya dikhta hai:**
- Peela warning banner: "All campaigns in this account are paused — no ads are running right now." Ye tab aata hai jab list mein jitni campaigns dikh rahi hain, un sab ka status Enabled nahi hai.
- 5 tiles (chuni hui period ke total): `Spend`, `Clicks` (neeche CTR), `Avg CPC`, `Conversions` (neeche Conv. rate), `Cost / conversion`. Ye totals campaign-level daily data ka jod hain.
- `Daily spend` bar chart: har din ka kharcha. Bar par mouse le jaane par us din ka Spend, clicks aur conversions dikhte hain.
- Table "Campaigns · last N days", default sort Cost (bada se chhota). Columns:
  - `Campaign` = naam.
  - `Status` = Enabled / Paused / Removed.
  - `Type` = campaign ka type (jaise Search, Performance Max).
  - `Budget/day` = campaign ka daily budget.
  - `Cost`, `Clicks`, `Impr.`, `CTR`, `Avg CPC`, `Conv.`, `Cost / conv.` = upar wali metrics table.
- Table ke neeche "N rows · click a column to sort". Page ke neeche note: conversions Google Ads ke hisaab se hain, confirmed bookings nahi.

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| Account dropdown | Dusra Google Ads account chunta hai | Local database (accounts list) | Sab (READ) |
| `7d` / `30d` / `90d` | Period badalta hai (tiles, chart, table sab) | Local database se dobara padhta hai | Sab (READ) |
| `Sync now` | Google Ads se naya data laata hai (background mein) | Google Ads (read-only) -> local database | Analyst aur upar (RECOMMEND) |
| `Show removed` (checkbox) | Delete ho chuki campaigns bhi dikhata hai. Band ho to wo removed campaigns chhupti hain jinka us period mein 0 impressions aur 0 cost tha; jisne paisa kharch kiya wo removed hone par bhi dikhti rehti hai | Local database | Sab (READ) |
| Column heading (Campaign, Status, Cost, ...) | Us column se sort. Dobara click par ulta order (up/down arrow dikhta hai) | Sirf screen par | Sab (READ) |

**Kaise use karein:**
1. Upar se account (agar ek se zyada ho) aur `30d` ya `90d` chuniye.
2. Last sync line dekhiye. Purani ho to `Sync now` dabaiye aur "Syncing…" khatam hone ka intezaar kijiye.
3. Tiles dekhiye: Spend aur Cost / conversion kitna hai.
4. Daily spend chart mein achanak spike ya zero-spend din dhundhiye.
5. Table ko `Cost / conv.` ya `Conv.` par sort karke sabse mehngi ya sabse achhi campaigns pehchaniye.

**Dhyan rakhne ki baat:**
- Ye page sirf dekhne ke liye hai. Campaign pause/enable, budget badalna yahan se nahi hota.
- Data utna hi taaza hai jitna last sync. Last sync line zaroor dekhein.
- Conversions Google Ads ke count hain, confirmed bookings nahi.
- Peela banner aaye to check karein campaigns waqai pause hain ya sync purana hai.
- Performance Max campaigns sirf campaign level par dikhti hain (unke keywords/search terms nahi aate).

---

## Ad Groups — `/ad-groups` (Module P05)
**Ye page kya hai:** Har campaign ke andar ke ad groups ka performance.

**Data kahan se aata hai:**
- Google Ads -> P05 ads_sync -> local database, `Sync now` se.

**Screen par kya dikhta hai:**
- Ek table "Ad groups · last N days", default sort Cost. Columns: `Ad group`; `Campaign` (agar campaign delete ho gayi to "(removed campaign)"); `Status` (effective status: Enabled / Paused / Removed / Campaign paused / Campaign removed); phir `Cost`, `Clicks`, `Impr.`, `CTR`, `Avg CPC`, `Conv.`, `Cost / conv.`.

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| Account dropdown, `7d`/`30d`/`90d`, `Sync now` | Top bar jaisa (upar dekhein) | Local database / Google Ads | READ / RECOMMEND (Sync now) |
| `Show removed` (checkbox) | Removed ad groups dikhata hai. Band ho to jo removed hain aur us period mein bina impression-bina cost ke the wo chhup jaate hain | Local database | Sab |
| `All campaigns` dropdown (aria-label "Filter by campaign") | Sirf ek campaign ke ad groups dikhata hai. List mein campaigns ke naam aate hain | Local database | Sab |
| Column heading | Sort | Sirf screen | Sab |

**Kaise use karein:**
1. Top bar mein period chuniye.
2. `All campaigns` dropdown se ek campaign chuniye.
3. `Cost` ya `Conv.` se sort kijiye.
4. Jin ad groups ka Status "Campaign paused" hai unhe samjhiye: wo band campaign ki wajah se nahi chal rahe, unhe alag se fix karne ki zarurat nahi.

**Dhyan rakhne ki baat:**
- Sirf padhne ka page hai, kuch edit nahi hota.
- "Status" column ad group ka apna status nahi, effective status hai.
- Campaign dropdown mein wahi campaigns aate hain jo Campaigns page ki list mein dikhti hain (idle removed campaigns nahi).

---

## Keywords — `/keywords` (Module P05)
**Ye page kya hai:** Aapke saare keywords, unka match type, Quality Score aur performance.

**Data kahan se aata hai:**
- Google Ads (keyword_view) -> P05 -> local database, `Sync now` se.

**Screen par kya dikhta hai:**
- Table "Keywords · last N days", default sort Cost. Columns:
  - `Keyword` = keyword ka text.
  - `Match` = Broad / Phrase / Exact (kitna sakht match).
  - `QS` = Quality Score 1 se 10 (Google ki rating; khali ho to "—"). Kam QS = mehnga click.
  - `Ad group` = keyword kis ad group mein hai.
  - `Status` = Enabled / Paused / Removed.
  - `Cost`, `Clicks`, `Impr.`, `CTR`, `Avg CPC`, `Conv.`, `Cost / conv.`.

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| Top bar (account, `7d`/`30d`/`90d`, `Sync now`) | Upar dekhein | Local database / Google Ads | READ / RECOMMEND |
| `Keyword insights →` (link) | `/keywords/insights` page kholta hai | - | Sab |
| `Only with impressions` (checkbox, shuru mein ON) | ON: sirf wo keywords jinke us period mein kam se kam 1 impression aaya. OFF: sab keywords, bina impression walon ke saath | Screen par filter (data wahi) | Sab |
| `All campaigns` dropdown | Ek campaign ke keywords | Local database | Sab |
| Column heading | Sort | Sirf screen | Sab |

**Kaise use karein:**
1. Period chuniye (jaise `90d`).
2. `Cost` par sort rakhiye: sabse zyada kharch wale keywords upar.
3. `Conv.` 0 aur Cost zyada wale keywords note kijiye.
4. Zyada gehrai se dekhna ho to `Keyword insights →` kholiye.

**Dhyan rakhne ki baat:**
- Is page par `Show removed` toggle nahi hai (wo sirf Campaigns aur Ad Groups par hai). Removed keywords bhi list mein aa sakte hain, Status column se pehchaniye.
- Keyword ka Status sirf uska apna status hai; "Campaign paused" jaisa label yahan nahi dikhta.
- Quality Score Google se sync hota hai; naye keyword ka QS khali ho sakta hai.
- Koi edit/pause yahan se nahi hota.

---

## Search Terms — `/search-terms` (Module P05)
**Ye page kya hai:** Logon ne Google par asal mein kya type kiya aur aapka ad dikha/click hua. Isse pata chalta hai paisa kin searches par ja raha hai.

**Data kahan se aata hai:**
- Google Ads (search_term_view) -> P05 -> local database. Ek search term agar kai keywords se match hua ho to uske numbers jod diye jaate hain.

**Screen par kya dikhta hai:**
- Upar line: "Spend on search terms with 0 conversions: $X" (jahan conversions 0 hain wo kharcha) aur negative keyword suggestions ka link.
- Table "Search terms · last N days", default sort Cost. Columns:
  - `Search term` = user ne jo likha.
  - `Matched keyword` = aapka kaun sa keyword (aur match type) isse trigger hua.
  - `Campaign` = kis campaign mein.
  - `Added?` = Google ke hisaab se is term ka haal: "—" (kuch nahi hua), Added (keyword bana liya gaya), Excluded (negative laga hua). Exact values Google ke status se title-case mein aate hain.
  - `Cost`, `Clicks`, `Impr.`, `CTR`, `Avg CPC`, `Conv.`, `Cost / conv.`.
- Maximum 2000 rows (cost ke hisaab se upar wali) screen par aati hain.

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| Top bar (account, `7d`/`30d`/`90d`, `Sync now`) | Upar dekhein | Local database / Google Ads | READ / RECOMMEND |
| `Negative keyword suggestions →` (link) | `/search-terms/negatives` kholta hai | - | Sab |
| Text box "Filter, e.g. cheap" + `Filter` button | Search term mein wo shabd dhundhta hai (kahin bhi, chhote-bade akshar ka farak nahi). Enter bhi chalta hai. Box khali karke `Filter` dabane se filter hat jaata hai | Local database (server par filter) | Sab |
| "negative keyword suggestions" (upar wali line ke andar link) | Negatives page par le jaata hai | - | Sab |
| Column heading | Sort | Sirf screen | Sab |

**Kaise use karein:**
1. Period `30d` ya `90d` rakhiye.
2. Upar "Spend on search terms with 0 conversions" dekhiye: itna paisa bina result ke gaya.
3. Table ko `Cost` se sort rakhiye aur upar ke terms padhiye.
4. Kisi shabd ke saare terms dekhne ke liye (jaise "cheap" ya "jobs") box mein likh kar `Filter` dabaiye.
5. Bekaar terms mile to `Negative keyword suggestions →` par jaakar analysis chalaiye.

**Dhyan rakhne ki baat:**
- Ye page khud negative keyword add nahi karta.
- "0 conversions wala kharcha" us period ka hai; naye terms mein conversions der se aa sakte hain.
- Performance Max campaigns ke search terms yahan nahi aate (MODULE.md known limit).
- Data 2000 rows tak hi dikhta hai.

---

## Negative keyword suggestions — `/search-terms/negatives` (Module P08)
**Ye page kya hai:** Software aapke search terms ko aapke Business Rules se milakar batata hai kaun se shabd negative keyword banne chahiye. Aap review karke Accept ya Reject karte hain, phir accepted list ko Google Ads mein khud paste karte hain.

**Data kahan se aata hai:**
- Search terms: Google Ads -> P05 (local database).
- Rules (services, areas, excluded terms, thresholds): P21 Business Rules page.
- Analysis P08 ka fixed (deterministic) logic hai, Claude AI nahi. "Unrecognised" searches ke liye AI abhi nahi hai (MODULE.md: P14 ke saath aayega).
- Suggestions aur aapke Accept/Reject faisle local database mein save hote hain.

**Screen par kya dikhta hai:**
- Upar card: "Analyse the last N days of search terms" (N = top bar ka 7/30/90). "Nothing is changed in Google Ads."
- `Run analysis` ke baad result line: kitne search terms dekhe, kitne negative suggestions mile, "high-confidence wasted spend" (sirf 80% ya usse upar wali suggestions ka kharcha), kitne naye keyword ideas mile (Insights link). Neeche chhote chips mein intent ki ginti:
  - `Service + area` = aapki service + aapka area (achhi search).
  - `Service only` = service hai, area nahi.
  - `Area only` = area hai, service nahi.
  - `Excluded words` = aapki "never want" list ka shabd.
  - `Wrong location` = aisi jagah jo aap serve nahi karte.
  - `Competitor` = competitor ka naam.
  - `Your brand` = aapka apna brand.
  - `Unrecognised` = kuch bhi pehchana nahi gaya.
- 4 status tabs: `To review` (naye suggestions), `Accepted`, `Rejected`, `No longer seen` (pichhli analysis mein mile the, ab naye data mein nahi mile).
- Table columns:
  - checkbox (select);
  - `Negative keyword`: Phrase match ho to "quotes" mein, Exact ho to [brackets] mein, neeche "Phrase" ya "Exact" likha;
  - `Where`: "All campaigns" ya ek campaign ka naam;
  - `Why`: karan + `examples` link jo 5 tak example searches kholta hai;
  - `Wasted`: in searches par gaya kharcha;
  - `Clicks`, `Conv.`;
  - `Searches`: kitne alag search terms is suggestion se jude;
  - `Confidence`.
- Neeche total: "N suggestions · total wasted $X" aur chetavani ki accepted negatives Google Ads mein apne aap nahi jaate.

**Confidence % ka matlab (analysis.py / MODULE.md):**
- **95%:** search mein aapki "Searches you never want" list ka shabd hai (Phrase, all campaigns). 60% tak gir jaata hai agar wahi shabd aisi searches mein bhi hai jinme aapki service ka shabd bhi hai (block karne se achhi searches bhi ruk sakti hain). 50% tak gir jaata hai agar us shabd par conversion aa chuka hai.
- **85%:** search mein aisi jagah ka naam hai jo aap serve nahi karte aur aapka koi area nahi hai (Phrase, all campaigns).
- **50-60%:** mehngi search jis par conversion nahi aaya, jo Business Rules ke "min spend" aur "min clicks" paar kar chuki hai aur clearly relevant nahi hai (Exact, sirf us campaign mein). 60% agar bilkul unrecognised, 50% agar competitor / sirf-area jaisi low-value.
- **40%:** ek shabd jo kam se kam 3 bekaar (0 conversion) searches mein aaya, kul kharcha min spend ka 2 guna ya zyada, aur wo aapki service/area/brand ka shabd nahi.
- Rang: hara = 80% ya zyada, peela = 50% se 79%, dhundhla = 50% se kam.
- Jo search aapki service+area ya brand wali hai, use negative suggest nahi kiya jaata. Jo term Google mein pehle se negative hai wo bhi nahi.

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| Top bar (account, `7d`/`30d`/`90d`, `Sync now`) | Upar common top bar dekhein. Analysis isi `7d/30d/90d` ke data par chalti hai | Local database / Google Ads | READ / RECOMMEND (Sync now) |
| `Run analysis` | Chuni hui period ke search terms ko rules se jaanch kar suggestions banata/update karta hai. Chalte waqt "Analysing…". Purane Accept/Reject faisle bache rehte hain; jo "To review" items naye data mein nahi mile wo "No longer seen" ban jaate hain | P05 search terms + P21 rules -> local database. Google Ads mein kuch nahi jaata | Analyst aur upar (RECOMMEND) |
| `Business Rules` (link) | Rules page kholta hai | - | Sab |
| `see insights` (link, analysis ke baad) | Keyword insights page | - | Sab |
| Tabs `To review` / `Accepted` / `Rejected` / `No longer seen` | Status ke hisaab se list badalta hai | Local database | Sab |
| `Confidence` dropdown: `All`, `≥ 50%`, `≥ 80%`, `≥ 90%` | Sirf itni ya zyada confidence wali suggestions dikhata hai | Local database | Sab |
| Header checkbox ("Select all") | Dikh rahi sabhi rows select/unselect | Screen | Sab |
| Row checkbox | Ek suggestion select karta hai | Screen | Sab |
| `examples` / `hide` | Us suggestion ke example search terms kholta/band karta hai | Screen | Sab |
| `Accept (N)` (To review aur Rejected / No longer seen tab par) | Selected suggestions ko Accepted karta hai. N = select ki hui ginti | Local database (status + aapka email + samay) | Approver aur upar (APPROVE) |
| `Reject` (To review aur Accepted tab par) | Selected ko Rejected karta hai | Local database | APPROVE |
| `Back to review` (Accepted, Rejected, No longer seen tab par) | Selected ko wapas "To review" bhejta hai | Local database | APPROVE |
| `Copy for Google Ads` (sirf Accepted tab) | Saare accepted negatives clipboard par copy karta hai, ek line mein ek: Phrase = "text", Exact = [text]. Message batata hai kitne copy hue; Google Ads mein Keywords -> Negative keywords mein paste karein | Local database (accepted list) | Sab (READ) |
| `Download CSV` (sirf Accepted tab) | `negative-keywords-<account>.csv` file download karta hai (Google Ads Editor ke liye). Columns: Campaign, Keyword, Criterion Type (Negative Phrase / Negative Exact), Level, Cost, Clicks, Conversions, Reason | Local database (accepted list) | Sab (READ) |

**Kaise use karein:**
1. Pehle `Sync now` se data taaza karein, aur `Business Rules` page par services/areas/excluded words theek rakhein.
2. Top bar mein `90d` (ya `30d`) chuniye aur `Run analysis` dabaiye.
3. `To review` tab mein `Confidence` ko `≥ 80%` par rakhiye. `Why` aur `examples` padhiye.
4. Jo suggestions sahi lagein unke checkbox tick karke `Accept (N)`; galat lagein to `Reject`.
5. `Accepted` tab kholiye. `Copy for Google Ads` dabaiye aur Google Ads ke Negative keywords mein paste kijiye (ya `Download CSV` ko Google Ads Editor mein import kijiye).
6. Agar Approval Center se guzarna hai to Approvals page par `Sync queue` dabaiye (wahan accepted negatives ek "Add N negative keyword(s)" request ban kar aate hain).

**Dhyan rakhne ki baat:**
- Kuch bhi Google Ads mein apne aap nahi jaata. Accept sirf aapka internal faisla hai; Google mein aapko khud paste/import karna hai.
- "Phrase" negative us shabd wali har future search ko rokta hai. Jin suggestions ke Why mein likha ho ki "some of these searches also mention your services", unhe dhyan se dekhein, achhi bookings bhi ruk sakti hain.
- Copy/CSV mein hamesha saare Accepted aate hain; confidence filter export par asar nahi karta.
- Business Rules badalne ke baad `Run analysis` dobara chalana padta hai, tabhi naye rules lagte hain.
- Accept/Reject ke liye approver permission chahiye; analyst analysis chala sakta hai par faisla nahi le sakta.
- Confidence % software ka andaza hai, guarantee nahi. Hamesha khud check karein.

---

## Keyword insights — `/keywords/insights` (Module P08)
**Ye page kya hai:** Aapke keywords ka health-check: kaun paisa kha raha hai, kaun kamaa raha hai, kahan Quality Score kharab hai, kahan duplicates hain aur kaun se naye keywords add karne layak hain.

**Data kahan se aata hai:**
- Keywords aur search terms: Google Ads -> P05 (local database).
- Thresholds (min spend, min clicks, target cost per conversion) aur service/area words: P21 Business Rules.
- Ye page har baar kholne par live calculate hota hai (alag "Analyze" button nahi hai, kuch save nahi hota). Calculation top bar ke `7d/30d/90d` par chalti hai.

**Screen par kya dikhta hai:**
- Peela warning: "No campaign is currently enabled, so 'idle' and 'duplicate' checks are empty." (jab koi campaign enabled nahi).
- 6 sections (isi order mein), har ek mein ginti (N) aur table: `Keyword` (naye ideas mein `Search term`), `Match`, `Ad group`, `Why`, `Cost`, `Clicks`, `Conv.`, `Cost / conv.`. Pehle 25 rows; zyada hon to `Show all N` / `Show less`.
  1. `Keywords spending without conversions` (wasters): 0 conversions, kharcha min spend se zyada aur clicks min clicks se zyada. Sujhav: pause karein, bid kam karein ya match type kasein.
  2. `Keywords that convert` (winners): jin par conversion aaya, sabse sasta cost per conversion pehle. Agar cost/conv. aapke target se upar hai to Why mein likha aata hai "converts, but above your target of $X per conversion".
  3. `New keyword ideas` (expansion): aisi searches jin par conversion aaya, jo abhi keyword nahi hain, Google mein add/exclude nahi hui aur negative-type nahi hain. Why mein likha hota hai kitni baar convert hui.
  4. `Low Quality Score (≤ 4)`: QS 4 ya kam aur impressions aaye. Kam QS = zyada CPC; ad relevance aur landing page sudharein.
  5. `Duplicate keywords (same campaign)`: ek hi campaign ke kai ad groups mein same keyword aur same match type; sirf enabled keywords aur enabled campaigns. Apne aap se compete karte hain.
  6. `Enabled keywords with no impressions` (idle): enabled keyword, enabled campaign, par is period mein 0 impressions.
- Jis section mein kuch nahi, wahan "None" ke saath khushi ka emoji likha aata hai.

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| Top bar (account, `7d`/`30d`/`90d`, `Sync now`) | Upar common top bar dekhein. Period badalne par insights dobara calculate hote hain | Local database / Google Ads | READ / RECOMMEND (Sync now) |
| `Show all N` / `Show less` (har section mein, 25 se zyada rows hon to) | Poori list kholta/band karta hai | Screen | Sab |

**Kaise use karein:**
1. `Sync now` se data taaza rakhein, phir `90d` chuniye.
2. `Keywords spending without conversions` dekhiye: upar wale sabse zyada paisa jala rahe hain.
3. `Keywords that convert` mein dekhiye kaun achha chal raha hai; unka budget protect karein.
4. `New keyword ideas` se naye keywords soch kar Google Ads mein khud add karein.
5. `Low Quality Score` aur `Duplicate keywords` ko saaf karne ke liye ad ya structure sudharein.

**Dhyan rakhne ki baat:**
- Is page par koi confidence % nahi hai (wo Negatives page par hai).
- Page sirf sujhav deta hai, Google Ads mein kuch change nahi karta.
- "Idle" aur "Duplicate" sirf chalti hui (enabled) campaigns dekhte hain, warna paused campaigns se list bhar jaati.
- Wasters ki limit Business Rules ke "Min spend / Min clicks" se judi hai; Rules badlein to list badal jaayegi.
- Wasters/winners ka data keyword-level hai; ek hi page par saare sections ek saath hain, alag tab nahi.

---

## Account audit — `/audit` (Module P07)
**Ye page kya hai:** Ek click mein poore Google Ads account ki jaanch. Result: 0 se 100 ka Health score aur priority ke hisaab se issues, har ek ke saath saboot, wajah aur kya karna hai.

**Data kahan se aata hai:**
- Google Ads data (campaigns, ad groups, keywords, search terms, ads, totals): P05 local database. **Audit khud Google se naya data nahi mangta**, isliye pehle Campaigns page par `Sync now` karein.
- Search term ki value: P08 classifier. Rules: P21 Business Rules.
- Tracking health aur organic search queries: P06 (GA4 / Search Console), sirf us account ke liye jiske saath website linked hai.
- Landing pages aur website pages: P03 website scan.
- Agar ek source fail ho (analytics ya website) to audit rukta nahi; "Some data unavailable: ..." likh kar baaki jaanch poori karta hai.
- Har run local database mein save hota hai.

**Screen par kya dikhta hai:**
- Agar audit kabhi nahi hua: "No audit yet. Click Run audit — it checks tracking, bidding, keywords, search terms, ads, landing pages and organic search. Nothing is changed in Google Ads."
- Health score card: `NN/100` aur label: 85 ya zyada = `Good`, 60 se 84 = `Needs work`, 60 se kam = `Poor`.
- 3 tiles: `Critical`, `Warning`, `Info` (kitne issues mile). Saath mein "Last N days · run <date time> by <email>".
- Category buttons (chhote): `All (n)` aur jitni categories mein issues hain: `Conversion tracking`, `Account`, `Bidding`, `Keywords`, `Search terms`, `Ads`, `Landing pages`, `Organic search`.
- Issues ki numbered list. Har issue ek card: severity badge, title, `observation` (sirf naape hue facts), category. Click karne par card khulta hai (Critical wale shuru se khule hote hain):
  - Evidence table (naam: value, jaise Cost, Clicks, Target).
  - `Why it matters` = reasoning (software ki samajh).
  - `What to do` = proposed action.
  - Neeche line: `Expected impact`, `confidence NN%` (software ko is finding par kitna bharosa hai), `risk of the change` (low / medium / high: ye badlav karne ka risk, issue ka nahi).
  - Agar dismiss kiya hua: "dismissed by <email> — note".
- Order: pehle Critical, phir Warning, phir Info; barabar severity mein zyada confidence upar.

**Health score kaise banta hai (checks.py):** Score = 100 − (15 x Critical) − (5 x Warning) − (1 x Info), kam se kam 0.

**Kya-kya check hota hai (MODULE.md):**
- Account: saari campaigns paused; campaign ne paisa kharch kiya par 0 conversions; bahut kam conversion rate.
- Tracking (P06): koi key event nahi, form submit missing, Ads aur GA4 ke conversions mein farak, paid sessions kam, mapping nahi, GA4 nahi.
- Bidding: kam conversion data par smart bidding; cost per conversion target se upar (Business Rules ke target ke 1.5 guna se zyada).
- Search terms: excluded ya wrong-location searches par kharcha; bekaar (non-converting) kharche ka bada hissa.
- Keywords: broad match bina conversion ke; low Quality Score; active campaigns mein duplicates; bahut bade ad groups (100 se zyada keywords = warning).
- Ads: enabled ad group bina ad ke; RSA mein 8 se kam headlines ya 3 se kam descriptions.
- Landing pages: broken, doosre domain par, kamzor (CTA/form/phone nahi, slow, patla content), ya account se koi website linked nahi.
- Organic: aapke brand ki search page 1 par nahi.

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| Account dropdown ("Ads account") | Account badalta hai (1 se zyada account hon to dikhta hai) | Local database | Sab (READ) |
| `Period` dropdown: `last 30 days`, `last 60 days`, `last 90 days`, `last 180 days` | Audit kitne din ke data par chalega (default 90). Agle run par lagu hota hai | - | Chunna sab; run ke liye RECOMMEND |
| `Run audit` / `Run audit again` | Naya audit chalata hai, naya score aur issues banata hai, naya run save karta hai. Chalte waqt "Auditing…" | P05, P08, P21, P03, P06 (sab local) -> local database. Google Ads mein kuch nahi badalta | Analyst aur upar (RECOMMEND) |
| Category buttons (`All`, `Conversion tracking`, ...) | Issues ko category ke hisaab se filter karta hai | Screen | Sab |
| Issue row (click) | Card kholta/band karta hai | Screen | Sab |
| `Open details →` (kuch issues mein) | Us issue se jude dashboard page par le jaata hai | - | Sab |
| `Dismiss` | Issue ko "dismissed" karta hai. Ek popup poochta hai "Why dismiss this? (optional — e.g. 'intentional')"; note likh sakte hain | Local database (aapka email aur note) | Analyst aur upar (RECOMMEND) |
| `Restore` (dismissed issue par) | Issue ko wapas open karta hai | Local database | RECOMMEND |
| `show N dismissed` (checkbox, sirf jab dismissed issues ho) | Dismissed issues bhi list mein dikhata hai (halke rang mein) | Local database | Sab |

**Kaise use karein:**
1. Pehle Campaigns page par `Sync now` kar lein taaki audit ko taaza data mile.
2. `/audit` kholiye, `Period` (jaise `last 90 days`) chuniye aur `Run audit` dabaiye.
3. Score aur Critical ginti dekhiye.
4. Critical aur Warning issues kholiye: `observation`, `Why it matters`, `What to do` padhiye.
5. Jo issue jaanbujh kar hai (jaise campaign abhi pause rakhi hai) use `Dismiss` karke note likhiye.
6. Issue theek karne ke baad (Google Ads ya website mein) `Run audit again` chalaiye.
7. Recommendations page par jaakar `Refresh from latest audit` dabayein taaki issues recommendations ban jaayein.

**Dhyan rakhne ki baat:**
- Audit sirf padhta hai. Fix aapko Google Ads ya website mein khud karna hai.
- Dismiss karne se issue list se chhup jaata hai, par score aur Critical/Warning/Info ginti mein wo ab bhi gina jaata hai (code mein score saare issues par banta hai, dismissed par bhi). Score tab sudharta hai jab problem sach mein theek ho.
- Dismiss yaad rehta hai (account + issue ke hisaab se), isliye naye runs mein bhi dismissed hi dikhega.
- History: backend mein pichhle runs ki list maujood hai, par is page par history ka koi table ya button nahi hai. Sirf sabse latest run dikhta hai.
- Score aapke data ki sync aur website scan ki freshness par nirbhar hai. Purana data = purana score.

---

## AI Recommendations — `/recommendations` (Module P14)
**Ye page kya hai:** Audit ke issues ko ek priority list (kya pehle karna hai) mein badalta hai. Aap har item ko Accept, Reject ya Done kar sakte hain. Upar "Action plan" mein 30 din ka plan bhi banta hai.

**Data kahan se aata hai:**
- Recommendations ka source: P07 Account audit ka latest run. `Refresh from latest audit` dabane par hi aate hain.
- Action plan: P14 ke ai.py se, live Claude ya rule-based template (neeche dekhein). Plan ke liye last 90 din ke totals (P05), services/areas/target cost per conversion (P21) aur top 25 open recommendations use hote hain.
- Aapke faisle aur har plan local database mein save hote hain.

**Screen par kya dikhta hai:**
- `Action plan` card: ek line batati hai plan kaun likh raha hai:
  - Live: "Written by Claude (<model>) from your audit evidence."
  - Off: "AI is off — a rule-based plan is shown. To turn on Claude: add ANTHROPIC_API_KEY to backend/.env and run ... ai.live_calls.enabled on ..."
  - Live tab hota hai jab **dono** cheezein hon: feature flag `ai.live_calls.enabled` ON aur backend/.env mein ANTHROPIC_API_KEY. (Ye technical setting hai, developer se karwayein.)
- Plan ke andar: summary; "top actions" (numbered, har ek mein title, owner chip, `effort: ...`, kyun, steps); `Week 1` se `Week 4` ke 4 box (focus aur tasks); "Measure: ..." aur caveats. Aakhri line mein `Claude <model>` ya `Rule-based`, samay aur kisne banaya, aur "Forecasts are never guaranteed."
  - Rule-based plan mein Week 1 = Fix measurement, Week 2 = Stop waste, Week 3 = Structure, keywords and ads, Week 4 = Landing pages, then relaunch. Top 5 recommendations hi actions banti hain.
- 4 tabs: `To do` (proposed), `In progress` (accepted), `Done`, `Rejected`.
- Recommendation list priority ke hisaab se (`P` ke baad number; bada = pehle). Priority = 300 (critical) / 200 (warning) / 100 (info) + confidence x 100 − risk penalty (medium 20, high 50).
- Har item mein severity badge, title, observation. Agar item Google Ads ke andar badlav maangta hai to chip `changes Google Ads` dikhta hai (categories: account, bidding, keywords, search terms, ads). Tracking, landing pages, organic website/GA4 ke fix hain, unpe ye chip nahi aata.
- Card kholne par: evidence, `Why`, `What to do`, `Impact`, `confidence`, `risk`, aur aakhri decision kisne liya.

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| Account dropdown ("Ads account") | Account badalta hai (1 se zyada hon to) | Local database | Sab (READ) |
| `Open audit` | `/audit` page kholta hai | - | Sab |
| `Refresh from latest audit` | Latest audit ke issues ko recommendations mein daalta/update karta hai. Message: "N findings from the latest audit · X new · Y no longer reported." Jo "proposed" item audit mein ab nahi mila wo list se hat jaata hai (superseded). Aapke Accept/Reject faisle bache rehte hain. Audit kabhi nahi hua to error: "Run an account audit first (Audit page)" | P07 audit (local) -> local database | Analyst aur upar (RECOMMEND) |
| `Generate plan` / `Regenerate plan` | Naya Action plan banata hai ("Claude is writing…" ya "Building…"). Kam se kam 1 open (To do ya In progress) recommendation chahiye, warna error | Live ho to Anthropic Claude API; warna rule-based template. Dono local database mein save | Analyst aur upar (RECOMMEND) |
| Tabs `To do` / `In progress` / `Done` / `Rejected` | Status ke hisaab se list | Local database | Sab |
| Recommendation row (click) | Card kholta/band karta hai | Screen | Sab |
| `Open details →` | Us issue ke detail page par jaata hai | - | Sab |
| `Accept — I'll do it` (To do tab) | Status "accepted" (In progress tab mein jaata hai). Aapka email aur samay save | Local database | Approver aur upar (APPROVE) |
| `Reject` (To do tab) | Status "rejected" | Local database | APPROVE |
| `Mark done` (In progress tab) | Status "done". Result "marked done manually" save hota hai, matlab aapne khud kaam kar liya | Local database | APPROVE |
| `Back to To do` (In progress tab) | Wapas "proposed" | Local database | APPROVE |
| `Reopen` (Done ya Rejected tab) | Done se wapas "accepted"; Rejected se wapas "proposed" | Local database | APPROVE |

**Status ka matlab:**
- `proposed` = To do, abhi faisla nahi.
- `accepted` = In progress, aapne haan kaha.
- `done` = kaam ho gaya (manual).
- `rejected` = nahi karna.
- `superseded` (kisi tab mein nahi dikhta) = audit ne ye issue ab report nahi kiya.

**Kaise use karein:**
1. Pehle `/audit` par `Run audit`.
2. Yahan aakar `Refresh from latest audit` dabaiye.
3. `To do` tab mein upar se neeche padhiye (sabse bada P number pehle).
4. Har item kholiye, `What to do` padhiye; karna ho to `Accept — I'll do it`, nahi to `Reject`.
5. Kaam hone ke baad `In progress` tab mein `Mark done`.
6. Upar `Generate plan` dabaiye aur 30 din ka plan dekhiye.
7. Jo accepted items par "changes Google Ads" chip hai unhe Approvals page par `Sync queue` dabakar approval queue mein bhejiye.

**Approval Center se kaise judta hai (p16 code):**
- Jab Approvals page par koi `Sync queue` dabata hai (RECOMMEND permission), tab wo recommendations jinka status "accepted" hai aur jinke saath "changes Google Ads" chip hai, wahan approval request ban kar aati hain. "proposed" ya "done" items nahi jaate.
- Page par likha hai ki jab automatic changes aayenge (P16/P17) tab approval ke bina Google Ads mein kuch nahi bheja jayega. Is page se koi change Google Ads mein nahi jaata.

**Dhyan rakhne ki baat:**
- Accept/Reject/Done sirf aapka internal faisla hai. Google Ads mein kuch bhi apne aap nahi hota.
- "AI is off" ho tab bhi plan banta hai, par wo rule-based hota hai (Claude nahi). Dono ke label alag dikhte hain (upar header line aur plan ke neeche "Claude <model>" ya "Rule-based").
- Agar Claude call fail ho jaaye to "Plan failed: ..." dikhta hai; template par automatic fallback code mein nahi mila.
- Plan ki forecast ki koi guarantee nahi hoti (page par bhi likha hai).
- Plan sirf top 25 open recommendations par based hota hai.
- MODULE.md ke hisaab se live Claude plan abhi tak asli API key ke saath test nahi hua (checklist mein khula hai).
- Accept/Reject/Done ke liye approver permission chahiye; analyst sirf Refresh aur Generate plan kar sakta hai.

---

## Business Rules — `/business-rules` (Module P21)
**Ye page kya hai:** Aapke business ke facts ek jagah: kaun si services, kaun se areas serve karte hain, kaun se nahi, kaun se shabd nahi chahiye, competitors, brand names aur kuch limits. Baaki modules inhe padhkar faisla lete hain.

**Data kahan se aata hai:**
- Ye page khud kahin se data nahi laata. Aap type karte hain, `Save rules` par local database mein versioned document ban jaata hai (kisne, kab, kya badla).
- Jab tak aap kabhi Save nahi karte, page upar likhta hai "Using built-in chauffeur defaults — edit and save to make them yours." (built-in chauffeur lists: services, Melbourne ke areas, door ke shehar, excluded words wagairah).
- Save ke baad upar: "Version N · saved <date> by <email>".

**Screen par kya dikhta hai:**
- 6 bade text box, har ek mein ek line = ek item (title ke saath item ki ginti):
  - `Services you offer`: in shabdon wali searches relevant maani jaati hain (jaise airport transfer, wedding car).
  - `Areas you serve`: suburbs, cities, airports, venues.
  - `Searches you never want`: in shabdon wali koi bhi search negative-keyword suggestion ban jaati hai (jaise jobs, cheap, uber).
  - `Places you don't serve`: ye naam aaye (aur aapka koi area na ho) to search negative suggest hoti hai.
  - `Competitor names`: competitor ki searches pehchani jaati hain (apne aap negative nahi hoti).
  - `Your brand names`: aapke apne brand ki searches, hamesha high value maani jaati hain.
- `Thresholds` section:
  - `Min spend before suggesting a negative ($)` (0 se 10,000; default 20).
  - `Min clicks before suggesting a negative` (1 se 1000; default 5).
  - `Target cost per conversion ($, optional)` (khali chhod sakte hain).
  - `What changed? (saved with this version)`: ek chhota note, jaise "added Geelong, removed 'bus'".
- `Version history`: har version (v1, v2...) ke saath samay, kisne save kiya, note, aur `Restore`.

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Save rules` | Sab boxes aur thresholds save karta hai. Bina badlav ke save karo to naya version nahi banta ("No changes to save."). Safal par: "Saved as version N. Re-run keyword analysis to use the new rules." | Local database (global scope, naya version) | Approver aur upar (APPROVE) |
| 6 text boxes (services, areas, ...) | Ek line = ek item. Save par sab lowercase, extra space hata kar, duplicate hata kar save hote hain | Screen draft | Dekhna sab (READ), save APPROVE |
| `Min spend ...`, `Min clicks ...`, `Target cost per conversion ...` | Number boxes | Screen draft | Dekhna sab, save APPROVE |
| `What changed? (saved with this version)` | Version ka note | Local database (version ke saath) | Save APPROVE |
| `Restore` (har purane version ke saamne; current version par nahi) | Confirm popup ke baad us purane version ke rules ko **naye version** ki tarah save karta hai (history kabhi nahi mitti) | Local database | Approver aur upar (APPROVE) |

**Scope (global vs account):**
- Backend mein 2 scope hain: `global` (poore business ke liye) aur `account:<id>` (ek Google Ads account ke liye alag rules; jo account-scope save ho wo us account ke liye global ko replace kar deta hai).
- Is page par scope chunne ka koi dropdown ya button nahi hai. Ye page hamesha global scope hi dikhata aur save karta hai. Account-level rules sirf backend/API se ban sakte hain, screen se nahi.
- Modules jab kisi account ke liye rules maangte hain to pehle us account ke rules dekhte hain, na mile to global, wo bhi na ho to built-in defaults.

**Defaults:**
- Page par "Defaults" naam ka koi button nahi hai (backend mein `/defaults` route hai, par screen use nahi karti). Built-in defaults tab dikhte hain jab kabhi save nahi hua.
- Page par rules ka `notes` field edit karne ka box bhi nahi hai; sirf version note (`What changed?`) hai.

**Kaun se module ye rules use karte hain (code se):**
- P08 Keyword intel (Negatives aur Insights): services, areas, places you don't serve, excluded terms, competitors, brand, min spend/clicks, target cost per conversion.
- P07 Account audit: min spend (kam se kam 20 ke saath), target cost per conversion, search-term classification.
- P03 Website intel: services aur areas.
- P09 Ad creative: services, areas, competitors, brand.
- P12 Budget & bids: places you don't serve aur target cost per conversion.
- P14 Recommendations (AI plan): services, areas, target cost per conversion.
- P15 Campaign builder: areas, excluded terms, places you don't serve.
- P11 Competitor intel: rules import karta hai, par kaun sa field kaise use hota hai, code mein clear nahi hai.

**Kaise use karein:**
1. `/business-rules` kholiye.
2. `Services you offer` aur `Areas you serve` mein apni asli services aur areas ek-ek line mein likhiye.
3. `Searches you never want` aur `Places you don't serve` mein wo shabd daaliye jinse aap bekaar clicks nahi chahte.
4. `Your brand names` mein apna brand likhiye (jaise "opal chauffeurs"), `Competitor names` mein competitors.
5. Thresholds set kijiye (jaise min spend 20, min clicks 5, aur apna asli target cost per conversion).
6. `What changed?` mein ek chhota note likh kar `Save rules` dabaiye.
7. Keyword pages par jaakar `Run analysis` dobara chalaiye (aur zarurat ho to audit bhi) taaki naye rules lagein.

**Dhyan rakhne ki baat:**
- Save aur Restore ke liye approver permission chahiye. Viewer/analyst ko page dikhega par save par error aayega.
- Rules save karne se purani suggestions apne aap nahi badalti; naya `Run analysis` / `Run audit` zaroori hai.
- "Searches you never want" mein bahut common shabd mat daaliye (jaise "car"), warna achhi searches bhi negative suggest hongi. Built-in list mein "free", "cheap", "bus", "train", "used" jaise shabd pehle se hain jo kabhi relevant search bhi pakad sakte hain; ek baar list padh kar apne hisaab se tune karein.
- Lists auto-normalise hoti hain (lowercase, trim, duplicate hataana), isliye save ke baad text thoda badla hua dikh sakta hai.
- Purana version `Restore` karna asal mein naya version banata hai; history safe rehti hai.
- Competitor names se sirf pehchaan hoti hai, apne aap negative nahi lagte.

## Ads & Assets — `/ads-assets` (Module P09)
**Ye page kya hai:** Yahan aap apne maujooda Responsive Search Ads (RSA) ka check-up karte ho, aur naye ads ka draft likhwate ho (Claude AI se ya template se). Har line Google ke rules ke against check hoti hai. Yahan se kuch bhi Google Ads mein publish nahi hota; sirf draft banta hai aur approved drafts ki CSV file export hoti hai.
**Data kahan se aata hai:**
- Maujooda ads, ad groups, keywords, cost, CTR -> Google Ads -> P05 (Ads Sync) ka local database -> jab account "Campaigns" page par sync hota hai tab update hota hai. Ye page khud Google Ads se live nahi padhta; analysis pichhle 90 din ka hota hai.
- Ad likhne ke rules, areas/locations, competitor names, brand words -> P21 Business Rules (local database).
- Naya ad copy -> Claude AI (sirf jab flag `ai.live_calls.enabled` on ho aur API key set ho), warna fixed template. Dono case mein copy ke baad checks automatic chalte hain.
- Drafts aur unke checks -> local database; har approve/reject ka record audit log mein jaata hai.

**Screen par kya dikhta hai:**
- Upar: agar 1 se zyada Ads account hon to account dropdown. Neeche teen tabs: `Existing ads`, `✍ Write new ads`, `Drafts`.
- `Existing ads` tab: table "Responsive search ads (weakest first)" (sabse kamzor ad pehle). Columns: `Ad group` (neeche campaign ka naam), `Status` (enabled/paused), `Headlines` (kitni headlines, maximum 15), `Descr.` (kitni descriptions, maximum 4), `Cost (90d)` (pichhle 90 din ka kharcha), `CTR` (click-through rate = clicks / impressions), `Strength*` (hamara apna 0-100 estimate, Google ka Ad Strength nahi), `Problems` (pehle 2 problems, baaki "+N"). Row par click karo to saari headlines (H1, H2...) aur descriptions (D1...) character count ke saath aur final URL khulta hai. Neeche note: Strength hamara estimate hai kyunki read-only access mein Google ki apni rating nahi milti.
- `✍ Write new ads` tab: form (neeche table mein). Upar ek line batati hai ki AI on hai ya off: AI on = "Claude writes 15 headlines and 4 descriptions..."; AI off = "AI is off — a template ad is generated from your keywords."
- `Drafts` tab: har draft ka ek card. Card header mein: ad group ka naam, campaign, label (`Claude <model>` agar AI ne likha, ya `template`), strength number (85+ hara, 60-84 peela, 60 se kam laal), status (`draft` / `approved` / `rejected`). Andar: 15 headline boxes (H1-H15, limit 30), 4 description boxes (D1-D4, limit 90), 2 path boxes (P1-P2, limit 15), har box ke saath live character counter jaise `27/30` (limit paar karte hi laal). Right side par "Preview" (kaise dikhega) aur AI ke `Notes`. Ad-level problems (jaise "too few headlines") card ke upar list mein dikhti hain.
- Checks ke do level: **Error (laal)** = Google reject karega ya rule toot raha hai. **Warning (peela)** = review karo. Errors: headline 30 se lamba, description 90 se lamba, path 15 se lamba ya letters/numbers/hyphen ke alawa kuch, headline mein `!`, repeated punctuation, phone number, emoji, 4+ letter wala ALL-CAPS word, competitor ka naam (P21 list se), khali line, 3 se kam ya 15 se zyada headlines, 2 se kam ya 4 se zyada descriptions, duplicate headlines. Warnings: bina proof ke claims (#1, best, cheapest, guarantee, top rated/award, free ya % off, price) jab tak wo "Approved USPs" mein na likhe hon; 8 se kam headlines; 4 se kam descriptions; main keyword kisi headline mein nahi; call to action (Book / Get a quote / Call) nahi; koi area (jaise Melbourne) nahi.
- Strength score ka formula: headlines (50 point tak) + descriptions (20 point tak) + 30 base, har error ka -10, har ad-level warning ka -4.

**Buttons aur controls:**
| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Ads account` dropdown (sirf jab 1 se zyada account) | Konsa Google Ads account dekhna hai | Local database ke active accounts | Koi bhi signed-in user (READ) |
| Tabs `Existing ads` / `✍ Write new ads` / `Drafts` | Section badalta hai | Sirf screen | Koi bhi signed-in user |
| Existing ads table ki row (click) | Us ad ki saari headlines/descriptions kholta/band karta hai | Local database (P05) | READ |
| `Start from an existing ad group (optional)` dropdown | Ad group chunne par naam, campaign, landing page aur top 10 keywords form mein apne aap bhar jaate hain. Default `— new ad group —` | Local database (P05 ad groups + keywords, 90 din) | READ |
| `Ad group name *` | Zaroori naam (khali ho to `Generate ad` band) | Draft mein jaata hai | RECOMMEND |
| `Campaign` | Campaign ka naam (CSV mein jaata hai) | Draft | RECOMMEND |
| `Landing page (final URL)` | Ad kis page par le jaayega | Draft aur CSV | RECOMMEND |
| `Main keywords (one per line)` | Ad copy in keywords ke aas-paas likha jaata hai (max 50) | AI/template ko input | RECOMMEND |
| `Approved USPs / claims (one per line — only these may be claimed)` | Sirf yahi claims ad mein allowed hain; inke bahar ke claims par warning aati hai (max 20 lines) | AI/template ko input + claim check | RECOMMEND |
| `Generate ad` | Naya draft banata hai, checks chalata hai, phir `Drafts` tab par bhej deta hai ("Draft created — review it below."). Button text `Claude is writing…` ya `Generating…` ho jaata hai | POST /creatives/accounts/{id}/drafts -> Claude ya template -> local database | RECOMMEND (analyst aur upar) |
| `Use Claude (≈ $0.05–0.15)` checkbox (sirf jab AI live ho) | Tick = Claude likhega (har baar approx $0.05-0.15 ka kharcha). Untick = template | `use_ai` flag | RECOMMEND |
| `Download approved (CSV)` | Sirf `approved` drafts ki CSV download hoti hai (`rsa-drafts-<id>.csv`) | GET /creatives/accounts/{id}/drafts/export, local database | READ |
| Headline / description / path boxes (H1.., D1.., P1..) | Text edit karo; counter live badalta hai. Sirf `draft` status mein edit hota hai | Screen (save tak local) | RECOMMEND save ke liye |
| `Save & re-check` | Edit ko save karta hai aur saare checks dobara chalata hai. Tabhi enabled jab kuch badla ho | PATCH /creatives/drafts/{id} | RECOMMEND |
| `Approve` | Draft ko `approved` karta hai. Band rehta hai jab unsaved edits hon ya koi laal error ho (hover par "Fix red errors first"). Server bhi errors par mana kar deta hai: "Fix the errors (red) before approving" | PATCH status=approved; audit log mein record | APPROVE (approver aur upar). Analyst ko "Approving an ad needs the approve permission" milta hai |
| `Reject` | Draft ko `rejected` mark karta hai (card dhundhla ho jaata hai) | PATCH status=rejected; audit log | RECOMMEND |
| `Back to draft` (approved/rejected card par) | Status wapas `draft` karta hai taaki edit ho sake | PATCH status=draft | RECOMMEND |

**Kaise use karein:**
1. `Existing ads` tab kholo aur sabse upar wale (kamzor) ads ke `Problems` padho.
2. `✍ Write new ads` par jao. `Start from an existing ad group` se ad group chuno; keywords aur URL khud bhar jaayenge.
3. `Approved USPs / claims` mein sirf wo baatein likho jo sach hain aur aap prove kar sakte ho (jaise "Fixed price airport transfers").
4. `Generate ad` dabao (AI chahiye to `Use Claude` tick rakho).
5. `Drafts` tab mein laal errors theek karo aur `Save & re-check` dabao; peele warnings padh kar faisla lo.
6. Approver user `Approve` dabaye. Phir `Download approved (CSV)` karo aur Google Ads Editor mein import karo (ads Paused ke roop mein aate hain).

**Dhyan rakhne ki baat:**
- Yahan se Google Ads mein kuch publish nahi hota. CSV mein Status hamesha `Paused` hota hai.
- `Strength` hamara estimate hai, Google ki Ad Strength nahi.
- Agar "No responsive search ads found" dikhe to pehle Campaigns page par account sync karo.
- `Approve` ko errors rokte hain, warnings nahi. Warnings ko aap review karke chhod sakte ho.
- Competitor ka naam ad mein likha ho to wo error hai (trademark risk); naam P21 Business Rules se aate hain.
- AI fail ho to error aata hai (ai_failed); AI off ho to template hi banta hai. Model ka naam draft card par `Claude <model>` mein dikhta hai.

## Landing Pages — `/landing-pages` (Module P10)
**Ye page kya hai:** Ye un saare pages ko check karta hai jahan aapke ads click ke baad log pahunchte hain, aur dekhta hai ki click booking mein kyun badal raha hai ya nahi. Har page ko 0-100 score milta hai, sabse kharab page pehle. Phir aap developer ke liye "implementation brief" likhwa sakte ho.
**Data kahan se aata hai:**
- Landing URLs -> Google Ads ads ke final URLs -> P05 local database (pichhle 90 din, removed ads chhod kar, sabse zyada kharche wale pehle, maximum 25 URLs, aapke kisi bhi domain ke).
- Page ka content -> aapki live website, "Check landing pages" dabane par fetch hota hai (robots.txt maana jaata hai, 1 second ka gap, 20 second timeout). Flag `crawler.enabled` on hona chahiye.
- Tracking ki problems -> P06 (GA4/conversions) ke critical tracking issues, sirf Websites mein jude domains ke liye. Jo domain Websites mein add nahi, wahan "tracking not verified".
- Brief -> Claude AI (flag `ai.live_calls.enabled` + key) ya template; findings se likha jaata hai.
- Result aur history -> local database.

**Screen par kya dikhta hai:**
- Upar description line: kitne URLs hain, aur kya check hota hai. Agar fetching off ho to line mein `crawler.enabled` ka zikr aata hai.
- "Checked <date> by <user>" line.
- Har page ka card (band hota hai; click par khulta hai): bada `score` (80+ hara, 50-79 peela, 50 se kam laal), URL, aur chhoti line: ads ki sankhya, cost, clicks, conversions (90 din), HTTP status code, aur response time (seconds). Saath mein badges: kitne `critical` / `warning` / `info` findings.
- Khulne par: `Ad groups`, phir findings category ke hisaab se: Tracking, Search match (intent), Call to action (cta), Booking form (form), Trust, Mobile, Speed, Technical. Har finding mein severity, title, detail, `Fix:` (kya karna hai) aur evidence (key-value proof).
- Score ka rule: critical -20, warning -8, info -2; page load na ho to 0.
- Neeche "Implementation brief": summary, priority changes (owner: developer/content/owner, effort: small/medium/large, why, how), copy suggestions (H1, Sub-headline, Primary CTA, Secondary CTA, Trust line), Booking form, Tracking, "How to check it's done", notes. Label dikhata hai `Claude <model>` ya `Template (AI off)`.

**Buttons aur controls:**
| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Ads account` dropdown (1 se zyada account par) | Account badalta hai | Local database | READ |
| `Check run` dropdown (jab 1 se zyada run ho) | `Latest check` ya purani run (tareekh aur avg score ke saath) dikhata hai | Local database history (GET /landing-pages/accounts/{id}?run=) | READ |
| `Check landing pages` | Saare URLs live fetch karke naya check run banata hai. Button band agar page fetching flag off hai. Chalte waqt text `Checking pages…` | POST /check -> aapki websites padhta hai -> local database | RECOMMEND (analyst aur upar) |
| Page card header (click) | Card khol/band karta hai aur us page ka pichhla brief load karta hai | Local database | READ |
| `Write implementation brief` / `Rewrite brief` | Findings se brief likhta hai (Claude ya template). Pehli baar "Write...", brief hone par "Rewrite brief". Text `Claude is writing…` ya `Building…` | POST /checks/{id}/brief (AI maangta hai; AI off ho to template) -> local database | RECOMMEND |
| `Download .md` | Brief ko Markdown file (`landing-brief-<id>.md`) ke roop mein download karta hai | GET /briefs/{id}/markdown | READ |
| Link `sync Google Ads` (jab koi landing page nahi mile) | `/ads-accounts` page kholta hai | Sirf navigation | READ |

**Kaise use karein:**
1. `Check landing pages` dabao aur kuch second intezaar karo.
2. Sabse upar wale (kam score) page ka card kholo.
3. Critical findings pehle padho; har ek mein `Fix:` likha hai.
4. `Write implementation brief` dabao.
5. `Download .md` se file lo aur apne web developer ko bhej do.
6. Fix ke baad dobara `Check landing pages` chalao aur `Check run` dropdown se purani run se compare karo.

**Dhyan rakhne ki baat:**
- Pages bina JavaScript chalaye padhe jaate hain, isliye JS widgets se aaya content (jaise kuch forms ya reviews) miss ho sakta hai.
- Speed ka matlab hamare server se naapa gaya response time hai, poora PageSpeed/Core Web Vitals test nahi. Poori tasveer ke liye Google PageSpeed Insights use karo.
- Brief ke copy suggestions mein jahan proof nahi hota wahan `[brackets]` mein placeholder aata hai (jaise `[your Google rating]`); wo aapko khud sahi value se bharna hai. AI se banawati facts nahi likhwaye jaate.
- Is page se website ya Google Ads mein kuch change nahi hota.
- Agar "No ads with landing pages found" aaye to pehle Google Ads sync karo.

## Competitors — `/competitors` (Module P11)
**Ye page kya hai:** Yahan aap apne competitors ki sirf **public** jaankari ikatthi karte ho: unki website kya kehti hai, aapne Google mein kya dekha, aur aapke apne account mein unke naam par kitni searches aayi. Phir aap apni website se compare karke gaps dekhte ho aur ek alag "Interpretation" banwa sakte ho.
**Data kahan se aata hai:**
- Competitor ki website -> unki public site -> "Research website" dabane par (flag `competitor.research.enabled` on hona chahiye; robots.txt maana jaata hai; sitemap se homepage aur service/location pages pehle; maximum 12 pages; 1.5 second gap).
- "I saw them in Google" observations -> aap khud haath se likhte ho. Google result pages kabhi scrape nahi hote.
- "Searches for <name> in your own account" -> aapke apne Google Ads account ke search terms (P05, pichhle 12 mahine) jinme competitor ka brand naam hai.
- "Your side" (aapke pages) -> P03 Website Intelligence ke scan kiye pages (linked websites).
- Interpretation -> Claude (flag `ai.live_calls.enabled` + key) ya rule-based template; local database mein save hota hai.

**Screen par kya dikhta hai:**
- Upar note: sirf public information; kisi ke Google Ads budgets/keywords/results bahar se nahi dikhte aur ye page unka dava nahi karta.
- Agar research flag off ho to peela box (owner ko command se on karna padta hai). Manual observations phir bhi kaam karte hain.
- Har competitor ka card: naam, domain link, "Website read <date> · N pages" (ya "Website not researched yet"), notes. Research ke baad do box: `Their website says` (homepage heading, description, CTAs, Prices shown, Trust signals) aur `Page themes` (airport, corporate, wedding, formal, cruise, limo, tours, events, hourly - kitne pages).
- "Searches for <name> in your own account (12 months)": kitne search terms, impressions, clicks, kharcha, conversions, aur top 5 terms.
- `Your observations`: tareekh ke saath list (jaise: Searched "..." -> sponsored ad #2 - "text").
- `Coverage — you vs them`: tabs `services` / `locations`. Table mein `Term`, `You`, aur har researched competitor ka column. Cell: `—` = nahi, `mentioned (N)` = N pages mein zikr, `N pages ★` = N dedicated pages (URL, title ya main heading mein). `gap` badge (peeli row) = competitor ka dedicated page hai aur aapka nahi. Upar `Gaps:` aur `Only you:` (jo sirf aapke paas hai) lines. Ye sirf padhe gaye pages par based hai.
- `Interpretation`: peela note "Interpretation, not fact" (label: `Written by Claude (<model>)` ya `Rule-based (AI off)`, kitni observations, kab). Phir summary, Opportunities (channel ke saath), har competitor ki positioning/strengths/weaknesses, "Messages to test", caveats. `[brackets]` mein evidence keys (jaise `obs:12`, `gap:airport`, `demand:<naam>`) un facts ki taraf ishara karte hain jinse baat nikali gayi; jo reference exist nahi karta use system hata deta hai aur caveats mein ginta hai.

**Buttons aur controls:**
| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Ads account` dropdown | Account badalta hai | Local database | READ |
| `Add competitor` | Add form kholta hai | Sirf screen | Form kholna sabke liye, save RECOMMEND |
| Form: `Name`, `Website`, `Other brand words people search (comma separated)`, `Notes` | Competitor ki details. `Add` tabhi enabled jab Name aur Website bhare ho | POST /competitors/accounts/{id}/competitors -> local database. Agar wahi website pehle archive hui thi to wapas active ho jaati hai aur purani observations bhi laut aati hain | RECOMMEND |
| `Add` / `Cancel` (form) | Save / band | Local database | RECOMMEND / koi bhi |
| `Research website` / `Re-read website` | Competitor ki public site padhta hai (flag off ho to button band, tooltip "Website research is switched off"). Text `Reading website…`. Purani research history ban jaati hai, sirf latest compare hoti hai | POST /competitors/{id}/research -> competitor ki site -> local database | RECOMMEND |
| `Archive` | Competitor ko list se hata deta hai (data delete nahi hota) | PATCH status=archived | RECOMMEND |
| Observations ka `Add` / `Close` | Observation form kholta/band karta hai | Sirf screen | Save RECOMMEND |
| Radio `I saw them in Google` / `Note` | Observation ka type: serp ya note | Form | RECOMMEND |
| `What you searched` (zaroori, serp) | Aapne Google par kya search kiya | Observation | RECOMMEND |
| `Where` dropdown | `Sponsored ad` / `Normal result` / `Maps` | Observation | RECOMMEND |
| `Position (optional)` | 1-50 ka number | Observation | RECOMMEND |
| `What their ad/result said (optional)` (serp) ya `Note` (zaroori, note) | Free text (max 2000 chars) | Observation | RECOMMEND |
| `Save observation` | Observation save karta hai (serp mein query chahiye, note mein text) | POST /competitors/{id}/observations -> local database (aaj ki tareekh) | RECOMMEND |
| `delete` (observation ke saath) | Wo observation delete karta hai | DELETE /observations/{id} | RECOMMEND |
| Tabs `services` / `locations` | Coverage table badalta hai | Screen | READ |
| `Interpret findings` | Saare data se nayi interpretation banata hai. Competitor na ho to band. Text `Claude is thinking…` (AI on) ya `Building…` | POST /accounts/{id}/analyze -> Claude ya rule-based -> local database | RECOMMEND |
| Competitor ka domain link | Competitor ki site naye tab mein kholta hai | Bahari link | READ |

**Kaise use karein:**
1. `Add competitor` dabao, Name aur Website (jaise `example.com.au`) bharo, `Add`.
2. Card par `Research website` dabao (agar flag on hai). Result message mein dikhega kitne pages padhe.
3. Khud Google par apni main searches karo, aur card mein `Add` -> `I saw them in Google` se jo dikha wo `Save observation` karo.
4. `Coverage — you vs them` mein `gap` wali rows dekho: wahan competitor ka dedicated page hai aur aapka nahi.
5. Ab upar `Interpret findings` dabao.
6. Interpretation padho, lekin yaad rakho ye rai hai, tathya nahi; `[evidence]` keys se asli facts check karo.

**Dhyan rakhne ki baat:**
- Ye page kabhi competitor ka private Google Ads data (budget, bids, keywords, results) nahi dikhata. Ye bahar se ho hi nahi sakta.
- Google result pages scrape nahi hote; "Google mein dekha" wala data sirf aapka haath se likha hua hota hai.
- UI mein sirf `Archive` button hai; restore ka alag button nahi. Code ke hisaab se archived competitor ko wapas lane ke liye wahi website dobara `Add competitor` se add karo (wo restore ho jaata hai aur purani observations wapas aati hain).
- Research flag `competitor.research.enabled` off ho to sirf manual observations chalte hain. Flag on karna owner ka kaam hai (page par command likhi hoti hai).
- Coverage sirf padhe gaye pages par based hai, isliye kam pages padhe to gaps galat bhi dikh sakte hain.
- Interpretation AI off hone par rule-based hoti hai, jo kam gehri hoti hai.

## Bookings / Revenue — `/bookings-revenue` (Module P13)
**Ye page kya hai:** Ye ek website ke liye dikhata hai ki ad ka impression kaise click, visit, lead, booking aur revenue banta hai, har step par kitna kharcha aur pichhle period se kitna badlav hua, aur funnel kahan se "leak" ho raha hai. Ye page sirf padhta hai; kuch change nahi karta.
**Data kahan se aata hai:**
- Ad impressions, clicks, kharcha, campaigns -> Google Ads -> P05 local database (website se jude Ads account ke through).
- Paid visits aur leads -> GA4 -> P06 Analytics.
- Bookings aur revenue -> imported bookings (P06; `Conversions` page se import hote hain), sirf wo jinke paas gclid ya utm google/cpc hai.
- Ye page apni taraf se kuch sync nahi karta; P05/P06 ke sync hone par hi naya data dikhta hai.

**Screen par kya dikhta hai:**
- Line: "How ad clicks turn into bookings for <website>, <tareekh> -> <tareekh> (compared with <pichhla period>)". Pichhla period utne hi din ka, theek pehle wala hota hai. Jo step measure nahi ho sakta wo zero nahi, "not measured" likhta hai.
- Chhe stage cards: `Ad impressions` (Google Ads), `Ad clicks` (Google Ads), `Paid visits` (GA4 Paid Search aur Cross-network sessions), `Leads` (GA4 lead events x paid visits ka hissa; hamesha `est.` = andaza; card ka label `Leads` hai, spec mein "Leads (estimate)"), `Bookings from Google Ads`, `Revenue from Google Ads` (dono bookings jinke paas gclid ya utm google cpc ho). Har card par: "X% of previous step" (pichhle measured step ka rate), "$X each" (kharcha / us step ki ginti), "+/-N% vs before" (pichhle period se badlav), aur chhoti line mein source.
- `not measured` ka matlab data hi nahi hai (jaise GA4 nahi, ya koi lead event nahi). `0` ka matlab measure hua aur sach mein zero tha. Dono alag hain.
- Leads kaise andaza hote hain: GA4 ke wo events jinki role `lead` hai (confirm kiye ya naam se pehchane gaye) ki ginti, multiplied by paid visits / total visits. Agar koi lead event hi nahi to leads "not measured".
- `Where the funnel leaks`: bottleneck list (critical/warning/info). Har ek mein title, detail, `Do:` aur kabhi `Open →` link (Websites, Conversions, Ads & Assets, Landing Pages, Search terms). Examples: no Google Ads account linked, no GA4 data, no lead event, no bookings imported, no booking attributed to Google Ads, low click-through rate (3% se kam, kam se kam 500 impressions par), 60% se kam clicks GA4 visits ban rahe (kam se kam 30 clicks), low visit-to-lead rate (3% se kam, 50+ visits), kam leads bookings bane (15% se kam, 10+ leads), revenue kharche se kam (kam se kam $100 kharche par), GA4 events ke roles confirm nahi, aur "GA4 data starts on <date>" (jab GA4 period ke beech mein shuru hua). Ye benchmarks sirf flag karne ke liye hain, targets nahi.
- Table `Campaigns (as reported by Google Ads)`: `Campaign` (status ke saath), `Cost`, `Clicks`, `Conv.` (Google Ads ke apne conversions), `Cost/conv.`, `Value/cost` (Google ka reported ROAS = conversion value / cost). Booking revenue campaign-wise abhi nahi aata (per-booking data pending change request).
- Table `Booking quality by channel`: `Channel`, `Bookings`, `Revenue`, `Avg. value`. Neeche "Lead events counted: ..." line. Agar bookings import nahi hui to link `import bookings` (`/conversions`).

**Buttons aur controls:**
| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Website` dropdown (1 se zyada site par) | Konsi website ka funnel dekhna hai | GET /funnel/websites (P03 websites) | Koi bhi signed-in user (READ) |
| `Period` dropdown | `Last 30 days` / `Last 90 days` / `Custom` | Screen; data GET /funnel/websites/{id}?date_from&date_to se aata hai | READ |
| `From` aur `To` date boxes (sirf `Custom` mein) | Apna date range. From, To se pehle ya barabar honi chahiye; maximum 2 saal | Same | READ |
| Bottleneck ka `Open →` link | Related page kholta hai | Navigation | READ |
| Link `import bookings` | `/conversions` page kholta hai | Navigation | READ |

**Kaise use karein:**
1. Website chuno (agar ek hi hai to apne aap chun li jaati hai).
2. `Period` mein `Last 30 days` rakho, ya badi tasveer ke liye `Last 90 days`.
3. Chhe cards left se right padho: kahan "not measured" hai aur kahan rate kam hai.
4. `Where the funnel leaks` mein critical items pehle theek karo; `Open →` se seedha wahan jao.
5. `Campaigns` aur `Booking quality by channel` se dekho kaunsa campaign/channel paisa laa raha hai.

**Dhyan rakhne ki baat:**
- `Leads` hamesha andaza (`est.`) hai. Asli leads ki ginti nahi.
- "not measured" ko zero mat samjho; matlab setup adhura hai (GA4, lead event, ya bookings import).
- `Bookings from Google Ads` aur `Revenue` tabhi aate hain jab bookings import hui hon aur unme gclid ya utm google/cpc ho. Module notes ke hisaab se kabhi 0 bookings import thi aur Driver App link pending tha; aaj ki sthiti code se pata nahi chalti.
- Campaign ke `Conv.` aur `Value/cost` Google Ads ke apne numbers hain, aapki booking revenue se match nahi bhi kar sakte.
- Agar GA4 period ke beech shuru hua ho to clicks se visits ka rate compare nahi hota (info bottleneck dikhta hai); period GA4 ki shuruaat ke baad ka chuno.
- Is page par koi button data nahi badalta; sab sirf dekhne ke liye hai.

## Budget & Bid Insights — `/budget-bid` (Module P12)
**Ye page kya hai:** Ye batata hai ki kaunsa device, din, din ka samay aur jagah se booking aa rahi hai aur kahan sirf paisa ja raha hai, aur har campaign budget ya ad rank se limit ho raha hai ya nahi. Ye sirf salah deta hai; Google Ads mein kuch change nahi karta. Ye page sidebar section mein nahi hai; Monitoring page ke link se aate hain.
**Data kahan se aata hai:**
- Sab kuch seedha Google Ads se, jab aap `Run analysis` dabate ho (P04 ke through GAQL SELECT, sirf padhna): device, day-of-week, hour, location (suburb/postcode/city), campaign budget/bidding/impression share.
- Snapshot local database mein save hota hai (har account ke pichhle 10 runs). Page kholne par latest snapshot dikhta hai; naya data tabhi aata hai jab aap `Run analysis` chalate ho.
- Target cost per conversion aur "not served" jagahein -> P21 Business Rules.

**Screen par kya dikhta hai:**
- Summary line: tareekh range, kitna kharcha, clicks, conversions, average cost per conversion, aur analysis ka samay.
- `What stands out`: findings ki list. Har finding mein severity (`warning`/`info`), title, dimension aur `low`/`medium confidence`, observation, evidence (numbers), aur `Do:` (proposed action). Confidence sirf `low` ya `medium` hota hai, kyunki thode conversions mein zyadatar farq sirf chance hota hai. Agar kuch nahi hai to "Nothing stands out beyond normal variation."
- Statistical guard: "no conversions" wali baat tabhi kahi jaati hai jab us segment par account ke average hisaab se kam se kam 3 conversions expected hon (warna zero sirf bad-luck ho sakta hai); evidence mein "Conversions expected at the account average" dikhaya jaata hai. Cost-per-conversion par kuch kehne ke liye kam se kam 3 conversions chahiye. Segments par minimum clicks bhi chahiye (device/din/samay 30, location 15). Agar account mein koi conversion hi nahi to kuch conclude nahi hota, aur salah milti hai ki pehle tracking theek karo.
- Tables: `By device`, `By day of week`, `By time of day` (Late night 12am-6am, Morning 6am-12pm, Afternoon 12pm-6pm, Evening 6pm-12am), `Top places (by spend)` (top 15). Columns: `Segment`, `Spend`, `Clicks`, `Conv.`, `Cost / conv.` ("—" jab conversion 0), aur ek chhoti bar jo kharche ka hissa dikhati hai.
- `Campaign budget & ad rank` table: `Campaign`, `Status`, `Daily budget`, `Spend`, `Conv.`, `Impr. share` (aapke ads kitne mauke par dikhe, search impression share), `Lost: budget` (budget kam hone se kitne mauke chhute), `Lost: ad rank` (quality ya bid kam hone se kitne chhute), `Bidding` (strategy).
- Findings ke thresholds (analysis.py): budget se 15% se zyada loss, ad rank se 40% se zyada loss, campaign par $150 ya zyada kharcha bina conversion, "Maximize clicks" bidding ka flag. Victoria ke andar ki jagahon ko kam saboot par cut karne ki salah nahi di jaati; Australia ke bahar ya P21 mein "not served" likhi jagahein facts ke roop mein flag hoti hain.

**Buttons aur controls:**
| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Ads account` dropdown (1 se zyada account par) | Account badalta hai, us account ka latest snapshot dikhta hai | GET /budget-bid/accounts/{id}/latest (local database) | READ |
| `Period` dropdown | `Last 30 days` / `60` / `90` / `180 days`. Ye sirf agle `Run analysis` ke liye hai (screen par pehle se dikha snapshot nahi badalta) | Screen | READ |
| `Run analysis` | Google Ads se live padhta hai (kuch second), findings banata hai, snapshot save karta hai. Text `Reading Google Ads…`. Success par "Analysis updated from Google Ads." Fail par saaf error aata hai aur fail ka record rakha jaata hai | POST /budget-bid/accounts/{id}/run -> Google Ads (SELECT only) -> local database | RECOMMEND (analyst aur upar). Viewer sirf pichhla snapshot dekh sakta hai |
| Link `Monitoring` | Monitoring page kholta hai | Navigation | READ |
| Link `Negative keywords` | `/search-terms/negatives` kholta hai | Navigation | READ |

**Kaise use karein:**
1. Monitoring page se `Budget & Bid Insights` ka link kholo.
2. `Period` mein `Last 90 days` (ya zyada data ke liye `Last 180 days`) chuno.
3. `Run analysis` dabao aur intezaar karo.
4. `What stands out` mein har finding ka `confidence` aur evidence padho, phir `Do:` dekho.
5. Tables se tasdeeq karo (kya mobile sasta hai, kaunsa din bekaar, kaunsa campaign budget ya rank se ruk raha hai).
6. Koi bhi badlav (bid adjustment, schedule, location exclusion) aap Google Ads mein khud karoge; ye page ye nahi karta.

**Dhyan rakhne ki baat:**
- Sirf salah. Google Ads mein koi change nahi hota (module mein test hai ki har query sirf SELECT hai).
- Thode conversions ho to zyadatar farq chance hota hai; isliye har finding par confidence likha hai (`low` ya `medium`).
- Page kholne par jo dikhta hai wo pichhli baar ka snapshot hai; taaza data ke liye `Run analysis`.
- `Lost: budget` zyada ho to budget badhane par vichar karo, lekin sirf tab jab campaign acceptable cost par convert karta ho. `Lost: ad rank` zyada ho to problem quality/bids ki hai, budget ki nahi.
- Ad group/keyword level aur audience segments abhi is page par nahi hain.

## Campaign Builder — `/campaign-builder` (Module P15)
**Ye page kya hai:** Ye aapke maujooda keywords (aksar ek hi bada ad group) ko service ke theme (airport, wedding, corporate...) ke hisaab se alag ad groups mein baant kar ek naye Search campaign ka **draft** banata hai. Har ad group ko landing page, ads (P09 ke through) aur negative keywords milte hain. Ant mein Google Ads Editor ke liye CSV export hoti hai. Google Ads mein kuch create nahi hota.
**Data kahan se aata hai:**
- Keywords (pichhle 90 din) aur ad groups -> Google Ads -> P05 local database.
- Negatives -> rental brands (europcar, hertz, avis...) aur P08 ke unwanted keywords ("rental + driver" jaisi searches rakhi jaati hain), plus P21 ke excluded terms/not-served places aur P08 ke accepted negatives.
- Landing page suggestion -> P03 ke scan kiye gaye aapke website pages (URL mein theme ka shabd, title/H1, CTA, form/phone se points; slow/patle pages par points kat'te hain).
- Tracking issues aur bidding -> P06 (jab tak critical tracking issue ho, Maximize Clicks + max CPC; warna Maximize Conversions).
- Ads -> P09 Ad & Creative (Claude ya template). Draft local database mein.

**Screen par kya dikhta hai:**
- Upar `Campaign draft` dropdown (jab drafts hon): `#id naam (status)`. Latest draft apne aap khulta hai.
- `+ Build a new campaign draft` button (form khulta hai).
- Draft ka header: naam, status (`draft` / `approved`), "N keywords in · N ad groups · N negatives".
- `Settings`: Status "Paused (always)"; Networks "Google Search only (no partners, no Display)"; Bidding (strategy aur wajah); `Budget` (editable, AUD/day); Locations (pehli 8).
- `Launch checklist`: ✓ pass, ✗ fail, ☐ manual. Items: tracking (conversion tracking asli enquiries record karti hai), landing pages (har ad group ka URL hai), ads (har ad group ka approved ad hai), keywords (har group mein keywords), negatives, budget set, aur do manual: location option ("Presence: people in or regularly in your targeted locations" Google Ads Editor mein) aur primary conversion (sirf asli enquiry event Primary).
- `Approved USPs for the ads (one per line — Claude only claims these)` box (draft hone par).
- Ad group cards: naam (editable), theme, `Landing page` (match score /100 aur wajah, editable), `Keywords (N + M low-volume held back)` chips (Exact = `[keyword]`, Phrase = `"keyword"`; hover par clicks/conv/cost), har ad group mein maximum 30 keywords, baaki "reserve" mein. Neeche ad ka status, strength, headlines.
- `Not assigned to a theme (N)`: jo keywords kisi theme mein nahi baithe; jo aap move karoge wahi jaayenge, baaki chhod diye jaate hain.
- `Campaign negative keywords (N)`: fold-out list, har ek ke saath wajah.
- Match type: jis keyword par conversion aayi wo EXACT, baaki PHRASE.

**Buttons aur controls:**
| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Campaign draft` dropdown | Doosra draft kholta hai | GET /campaign-builder/drafts/{id} | READ |
| `+ Build a new campaign draft` | Build form kholta hai | Screen | Form kholna sabke liye, build RECOMMEND |
| `Source ad groups (none = all)` checkboxes | Konse ad groups ke keywords reorganise karne hain (kuch na chuno = sab) | Local database (P05) | RECOMMEND |
| `Campaign name` | Naye campaign ka naam (default `Search \| Restructured (draft)`) | Draft | RECOMMEND |
| `Daily budget (AUD)` | Roz ka budget (default 20; allowed 1 se 10,000) | Draft settings | RECOMMEND |
| `Max CPC (AUD)` | Maximum cost-per-click (default 3.25; allowed 0.1 se 100). Sirf tab asar karta hai jab bidding Maximize clicks ho | Draft settings | RECOMMEND |
| Theme buttons (Airport, Weddings & Formals, Cruise, Limousine, Tours & Hourly, Events, Corporate & Executive, Chauffeur (general)) | Sirf chune hue themes bante hain (kuch na chuno = sab) | Draft | RECOMMEND |
| `Build draft` | Draft banata hai (text `Building…`); naam khali ho to band | POST /campaign-builder/accounts/{id}/drafts -> local database | RECOMMEND |
| `Cancel` (build form) | Form band | Screen | Koi bhi |
| `Approve draft` | Draft ko `approved` karta hai. Checklist mein tracking ke alawa koi ✗ ho to mana ("Not ready: ..."). Tracking fail ho tab bhi approve ho jaata hai (campaign paused rehta hai) | PATCH op=status approved; approved_by save hota hai | APPROVE (approver aur upar) |
| `Download for Google Ads Editor` (sirf approved) | CSV (`campaign-draft-<id>.csv`): campaign, negatives, ad groups, keywords, ads, sab Paused | GET /drafts/{id}/export | READ (approved draft par) |
| `Back to draft` (approved par) | Edit ke liye wapas draft | PATCH op=status draft | RECOMMEND |
| `Archive` | Confirm box ke baad draft archive | PATCH op=status archived | RECOMMEND |
| `Budget` box | Daily budget badalta hai (box se bahar click karne par save) | PATCH op=settings | RECOMMEND |
| Ad group naam box | Naam rename (bahar click par save) | PATCH op=rename_group | RECOMMEND |
| `Landing page` box | URL badalta hai (bahar click par save) | PATCH op=set_url | RECOMMEND |
| Keyword chip ka `↪` dropdown | Keyword dusre theme ya `unassigned` mein bhejta hai | PATCH op=move_keyword | RECOMMEND |
| Keyword chip ka `×` | Keyword group se hata deta hai | PATCH op=remove_keyword | RECOMMEND |
| `✍ Write ads for this ad group` | Us ad group ke liye P09 se ad likhwata hai (top 15 keywords + USP box ke claims). Text `Claude is writing…`. AI off ho to template | POST /drafts/{id}/ad-groups/{key}/write-ads -> P09 (Claude ya template) | RECOMMEND |
| `Write again` | Ad dobara likhta hai | Same | RECOMMEND |
| Link `Review / approve on Ads & Assets` | `/ads-assets` kholta hai; wahan ad ko approve karna hai | Navigation | READ |
| `▸ Campaign negative keywords (N)` | Negatives ki list kholta/band karta hai | Screen | READ |
| `add a negative, e.g. bus` + `Add` | Naya negative (lowercase, PHRASE) jodta hai | PATCH op=add_negative | RECOMMEND |
| Negative ke saath `×` | Negative hata deta hai | PATCH op=remove_negative | RECOMMEND |

**Kaise use karein:**
1. `+ Build a new campaign draft` dabao. `Source ad groups` mein wo ad group tick karo jiske keywords reorganise karne hain.
2. `Campaign name`, `Daily budget (AUD)`, `Max CPC (AUD)` bharo, `Build draft` dabao.
3. Ad groups dekho: keywords `↪` se sahi theme mein bhejo ya `×` se hata do; `Landing page` check karo; `Not assigned to a theme` mein se kaam ke keywords move karo; negatives dekho.
4. `Approved USPs for the ads` mein sachche claims likho, phir har ad group par `✍ Write ads for this ad group`.
5. `Ads & Assets` -> `Drafts` mein jaakar har ad `Approve` karo (approver chahiye), wapas aakar checklist dekho.
6. Jab saare ✗ (tracking chhod kar) ✓ ho jaayein, `Approve draft` dabao, phir `Download for Google Ads Editor`.
7. Google Ads Editor mein CSV import karo, aur manual checklist items (location option, primary conversion) wahan khud set karo.

**Dhyan rakhne ki baat:**
- Ye sirf draft hai. Google Ads mein kuch create ya publish nahi hota; Editor ki import file sab kuch Paused rakhti hai.
- Settings fixed hain: Status hamesha Paused, Networks sirf Google Search (partners aur Display nahi). Bidding automatic chuni jaati hai (tracking critical hone par Maximize clicks).
- Approve ke baad draft locked hota hai (edit boxes band); edit ke liye `Back to draft`. Export sirf approved draft ka hota hai.
- Tracking fail ho tab bhi approve ho jaata hai; campaign paused hai, tab tak enable mat karo jab tak tracking pass na ho.
- Ads ka approval `Ads & Assets` page par hota hai; yahan sirf likhwate ho.
- `Max CPC` build form mein set hota hai; draft ban jaane ke baad screen par uska alag edit box nahi hai (code mein sirf Budget box hai).

# Part D — Approval, Execution, Experiments, Monitoring, Reports, Audit Log

Permission ki quick yaad (sab pages par same): `READ` = koi bhi signed-in user (viewer bhi), `RECOMMEND` = analyst aur upar, `APPROVE` = approver aur upar, `ADMIN` = sirf admin, `EXECUTE` = alag per-user switch jo sirf server CLI se lagta hai.

---

## Approval Center — `/approvals` (Module P16)
**Ye page kya hai:** Yahan Google Ads ke saare proposed changes ek hi queue mein aate hain. Har change ke saath before/after, evidence, risk aur impact dikhta hai, aur approver Approve / Reject / Withdraw ka faisla likhta hai. **Approve karne se Google Ads mein kuch bhi change nahi hota** — sirf aapka decision record hota hai.

**Data kahan se aata hai:**
- Local database (`approvals` aur `approval_events` tables) -> P16 -> jab "Sync queue" dabate hain ya koi module (jaise P20 Experiments) seedha request bhejta hai.
- "Sync queue" ye modules se items kheenchta hai:
  - P14 Recommendations -> woh recommendations jo "accepted" hain aur jinko approval chahiye (bidding, keywords, ads, account-level, search terms).
  - P08 Keyword/Search terms -> accepted negative keywords jo abhi kisi request mein nahi hain (sab ek hi batch request mein, title jaise "Add 5 negative keyword(s)").
  - P09 Ads & Assets -> approved RSA ad drafts (change type `create_rsa`).
  - P15 Campaign Builder -> approved campaign drafts (change type `create_campaign`, hamesha PAUSED).
- Account list P05 (Ads sync) se aati hai. Is page par Google Ads se kuch live nahi padha jaata.
- Har decision P22 Audit Log mein bhi likha jaata hai.

**Screen par kya dikhta hai:**
- Upar header mein: link "Send approved changes to Google Ads →", account dropdown (sirf tab dikhta hai jab 1 se zyada account ho), aur `Sync queue` button.
- Ek chhota explain text jo batata hai ki "Sync queue" kya collect karta hai.
- Status tabs: `Pending`, `Approved`, `Executed`, `Rejected`, `Withdrawn`. Tab ke aage bracket mein count aata hai (jaise `Pending (3)`), sirf tab jab count 0 se zyada ho.
- Har request ek card hai. Card band hota hai; click karne par khulta hai. Card ki header line mein:
  - Chhota source tag: Negative keywords (P08), Ad copy (P09), Recommendation (P14), Campaign builder (P15), Experiment (P20).
  - Title, change type, kab aur kisne request ki.
  - Laal tag `high impact` (agar change bada hai) aur `risk low / medium / high` ka rang-wala tag.
- Card khulne par:
  - `Before` aur `After (proposed)` — do box: abhi kya hai aur kya hone wala hai.
  - Evidence — key/value list (jaise negative keyword ke saath "AUD kitna waste hua, kitne clicks").
  - `Decision note` aur `Execution` result (agar pehle se hain).
  - Decision box (sirf Pending aur Approved status mein).
  - History — har event (requested, approved, rejected, withdrawn, executed) ka time, kisne kiya, aur note.
- Khaali hone par: "Nothing waiting. Approve something in another module, then click "Sync queue"." ya "Nothing here."
- Agar koi account connected nahi: "Connect and sync a Google Ads account first."

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Ads account` dropdown | Kaun sa Google Ads account dekhna hai chunta hai (1 se zyada account hon tab dikhta hai) | `GET /api/v1/approvals/accounts` (P05 ki account list + har status ka count) | Koi bhi signed-in user (READ) |
| `Sync queue` | P14/P08/P09/P15 se naye approved/accepted items queue mein laata hai. Jis open request ka source ab approved nahi raha (P09/P14/P15), use khud "withdrawn" kar deta hai. Message: "N new request(s) · M withdrawn because the source is no longer approved." | `POST /accounts/{id}/sync` -> sirf local database mein rows. Google Ads ko kuch nahi bhejta. Dobara dabane se duplicate nahi banta | Analyst aur upar (RECOMMEND) |
| `Send approved changes to Google Ads →` (link) | `/execution` page kholta hai | Sirf navigation | Koi bhi signed-in user |
| Tabs `Pending` / `Approved` / `Executed` / `Rejected` / `Withdrawn` | Us status ki requests dikhata hai | `GET /accounts/{id}?status=...` | Koi bhi signed-in user |
| Card header (click) | Card kholta/band karta hai aur us request ki full history load karta hai | `GET /api/v1/approvals/{id}` | Koi bhi signed-in user |
| `Note` box | Aapka reason/comment (max 2000 characters). Reject ke liye zaroori. High-impact request apni hi ho to approve ke liye bhi zaroori | Decision ke saath bheja jaata hai; history aur audit log mein save | Jo decision le sakta hai |
| Confirmation box ("High-impact change — type **APPROVE** to confirm") | Sirf high-impact pending request par dikhta hai. Exact `APPROVE` likhna padta hai | Decision ke saath `confirm` field mein jaata hai | Approver aur upar |
| `Approve` | Request ko "approved" karta hai. Google Ads nahi badalta | `POST /{id}/decision` (approve) -> status badalta hai, history + audit log | Approver aur upar (APPROVE) |
| `Reject` | Request "rejected" karta hai. Note zaroori ("Please give a reason when rejecting") | `POST /{id}/decision` (reject) | Approver aur upar (APPROVE) |
| `Withdraw` | Request wapas leta hai ("withdrawn"). Pending aur Approved dono par chalta hai | `POST /{id}/decision` (withdraw) | Analyst aur upar (RECOMMEND) |

**Kaise use karein:**
1. Pehle dusre pages par kaam accept/approve karein: negative keyword accept (Search terms), ad draft approve (Ads & Assets), campaign draft approve (Campaign Builder), ya recommendation accept (Recommendations).
2. `/approvals` kholein, upar account chunein, `Sync queue` dabayein. Message mein dekhein kitni nayi requests aayi.
3. `Pending` tab mein card par click karke kholein. `Before` aur `After (proposed)`, Evidence, risk aur `high impact` tag dhyan se padhein.
4. Note likhein (agar chahein). High-impact ho to `APPROVE` type karein.
5. `Approve` ya `Reject` dabayein. Upar aaye message se confirm karein.
6. Approved change Google Ads tak bhejna ho to `Approved` tab dekhein, phir "Send approved changes to Google Ads →" link se `/execution` par jayein (wahan abhi sab locked hai).

**Dhyan rakhne ki baat:**
- **Approve = sirf record.** Isse Google Ads mein kuch nahi badalta. Card ke neeche bhi yahi likha aata hai. (Us line mein "P17 is not built" likha hai — ye line purani hai; P17 module ab maujood hai, par default mein locked hai. Execution page dekhein.)
- High-impact change types: create_campaign, bidding_change, enable_campaigns, budget_change_major, structure_change. In par `APPROVE` type karna padta hai.
- Self-approval rule: agar aapne hi high-impact request banayi aur aap hi approve kar rahe hain, to Note zaroori hai (warna "Approving your own high-impact request needs a note explaining why"). Standard (chhote) changes par ye rule code mein nahi hai.
- Approve/Reject sirf `pending` par chalte hain; Withdraw `pending` aur `approved` par. Rejected, withdrawn ya executed request ko dobara decide nahi kar sakte.
- Source module mein kuch "un-approve" karne par P09/P14/P15 wali open request khud withdraw ho jaati hai (history mein "system" likha aata hai). P08 negatives batch kabhi auto-withdraw nahi hota.
- Viewer ko Sync queue, Approve, Reject, Withdraw ka permission nahi hota; error message aayega.

---

## Google Ads Execution — `/execution` (Module P17)
**Ye page kya hai:** Yahan wo changes dikhte hain jo Approval Center mein "approved" ho chuke hain. Aap inhe pehle Google se "validate" kara sakte hain (kuch change nahi hota), aur saare guards khule hon to live "Execute" ya "Roll back" kar sakte hain. **Aaj (default) sab kuch locked hai** — live change nahi ho sakta.

**Data kahan se aata hai:**
- Approved changes: P16 (approvals) se, sirf `approved` status wali.
- Plan banane ke liye: P05 (synced campaigns) aur P09 (approved ad drafts) ka data; Google ko jaane wala exact request local code banata hai.
- Validate / Execute / Roll back: P17 seedha Google Ads API ko call karta hai (project mein ye akela code hai jo Google Ads mein likhta hai). Credentials P04 se.
- Lock status: environment setting `ADS_EXECUTION_KILL_SWITCH` aur feature flag `ads.execution.enabled`.
- Har action local `executions` table aur P22 Audit Log mein save hota hai.
- Ye page sidebar mein nahi hai; `/approvals` ke link se ya seedha URL se khulta hai.

**Screen par kya dikhta hai:**
- Lock banner (upar):
  - Hara: "Locked: nothing here can change Google Ads (kill switch is on / execution flag is off). Validate is still safe — it changes nothing."
  - Laal: "LIVE execution is ON — Execute will change Google Ads." (tab jab dono guards khule hon)
- Explain text: sirf Approval Center ke approved changes yahan aate hain; supported types (`add_negative_keywords`, `create_rsa`).
- Approved changes ki list. Har card mein title, change type, risk. Agar change execute nahi ho sakta to peela text "Cannot be executed here: <reason>".
  - "Executable" ka matlab: code ne us change ka exact Google request bana liya. Supported types: negative keywords (campaign-level; account-level negatives har non-removed campaign par lagte hain; max 500 operations) aur RSA ad (hamesha PAUSED banta hai; 3-15 headlines, 2-4 descriptions chahiye; approval ke baad draft badla ho ya ad group Google se linked na ho to blocked).
  - Supported nahi: `create_campaign` (Google Ads Editor export use karein), bidding/budget/enable changes (haath se karein), experiments ka `start_experiment`. Inke card par "can't be executed automatically yet — apply it by hand in Google Ads." aata hai.
  - Har operation ka collapsible (`details`) — click karke Google ko jaane wala sample JSON dekh sakte hain.
- `History` section: har validate/execute/rollback ki line: time, `#approval id`, change type, mode, status (validated, executed, failed, unknown, rolled_back...), error, kisne kiya.
- Khaali: "No approved changes waiting."

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Ads account` dropdown | Account badalta hai (1 se zyada ho tab dikhta hai) | `GET /api/v1/execution/accounts` | Koi bhi signed-in user |
| Operation summary (collapsible) | Google ko jaane wala sample request dikhata hai | Local plan, kuch bhejta nahi | Koi bhi signed-in user |
| `Validate with Google (changes nothing)` | Google se us exact request ko `validateOnly` mode mein check karwata hai; Google kuch apply nahi karta. Success: "Google accepted this request (nothing was changed)." | `POST /approvals/{id}/validate` -> Google Ads API (validate only) -> `executions` table + audit log. Execute ke liye zaroori fresh validation yahi banati hai | Sirf `EXECUTE` permission wala user (role ke alawa alag se `set-execute` chahiye) |
| `type EXECUTE` box | Yahan exact `EXECUTE` likhna padta hai. Page locked ho to box disabled rehta hai | Sirf browser mein; button ke saath `confirm` bheja jaata hai | EXECUTE permission wala user |
| `Execute live` | Approved change Google Ads par LIVE lagata hai. Locked ho ya box mein `EXECUTE` na ho to disabled. Success par message "Executed." | `POST /approvals/{id}/execute` -> Google Ads API (live) -> P16 request `executed` ho jaati hai; execution row + audit log | Sirf EXECUTE permission, aur saare guards khule hon |
| `Roll back` | History ki executed line ke saath dikhta hai (sirf jab live execution allowed ho). Click par browser prompt "Type ROLLBACK to remove what this created" aata hai; `ROLLBACK` likhne par jo Google ne banaya tha use remove karta hai | `POST /executions/{id}/rollback` -> Google Ads API (remove) | Sirf EXECUTE permission, aur guards khule hon |

**Kaise use karein:**
1. Pehle `/approvals` par change approve karein (`Approved` tab mein dikhna chahiye).
2. `/execution` kholein, account chunein. Upar ka banner padhein — abhi "Locked" hoga.
3. Card mein check karein ki "Cannot be executed here" nahi likha. Details kholkar dekhein Google ko kya jaayega.
4. `Validate with Google (changes nothing)` dabayein (EXECUTE permission ho to). Google ka jawab History mein `validated` ya `failed` dikhega.
5. Live karne ke liye server par operator ko neeche wali 3 cheezein karni hongi. Phir `type EXECUTE` box mein `EXECUTE` likhein aur `Execute live` dabayein. Usi exact change ki validation pichhle 24 ghante mein hui ho.
6. Galti ho jaye to History ki executed line par `Roll back` dabayein, prompt mein `ROLLBACK` likhein.

**Live change ke liye saari shartein (sab ek saath):**
- Environment: `ADS_EXECUTION_KILL_SWITCH=false` (default `true`, yaani locked) aur server restart.
- Feature flag `ads.execution.enabled` ON — sirf server CLI se: `python -m app.modules.p17_ads_execution.cli enable --reason "..."` (terminal mein phrase `ENABLE LIVE EXECUTION` type karna padta hai). Status ke liye `... cli status`.
- Aapke user par `execute` permission: `python -m app.modules.p02_auth.cli set-execute EMAIL on` (sirf yahi raasta hai).
- Request abhi bhi `approved` ho.
- Usi exact plan ki successful `Validate` pichhle 24 ghante mein.
- Typed confirmation `EXECUTE` (rollback ke liye `ROLLBACK`).

**Dhyan rakhne ki baat:**
- Aaj sab locked hai (kill switch default ON). Page par koi button ya API se ise on nahi kiya ja sakta; sirf server par operator.
- `Validate` bhi EXECUTE permission maangta hai, jabki page dekhna sab ke liye khula hai.
- Ek approval sirf ek baar execute hoti hai; double click ya do tab se dobara nahi jaati. Agar Google se jawab hi na aaye to status `unknown` — change laga ho bhi sakta hai; pehle Google Ads mein haath se check karein. Code khud dobara nahi bhejta.
- Google ne reject kiya to status `failed` aur theek karke dobara try kar sakte hain. RSA ad hamesha PAUSED banta hai; use Google Ads mein khud enable karna hoga.
- Module notes ke mutabiq ye abhi asli Google Ads account par verify nahi hua — hamesha pehle Validate karein.
- Execute permission global hai (account-wise nahi). Roll back sirf ek baar chalta hai aur sirf wahi hata'ta hai jo us execution ne banaya tha.

---

## Experiments — `/experiments` (Module P20)
**Ye page kya hai:** Ek baar mein ek change test karne ki jagah — A/B (do campaigns/ad groups/ads same dates mein) ya Before/After (ek hi cheez ka pehle aur baad). Result synced Google Ads data se nikalta hai, saath mein limitations bhi likhi aati hain. Ye page Google Ads mein kuch change nahi karta.

**Data kahan se aata hai:**
- Google Ads synced data (P05): campaigns, ad groups, ads ke impressions, clicks, cost, conversions.
- Experiments aur results local database (`experiments` table) mein save hote hain (P20).
- `Submit for approval` P16 mein request banata hai (change type `start_experiment`).
- Conversion tracking ki critical problems P06 se (limitations ke liye), agar is account se website linked ho.
- Result tab banta hai jab aap `Preview results` / `Update results` / `Complete experiment` dabate hain (apne aap nahi).

**Screen par kya dikhta hai:**
- Header mein account dropdown (1 se zyada ho to) aur `New experiment` button.
- Left list: sab experiments (naam, A/B ya Before/after, status).
- Right detail: naam, type, entity, test dates, baseline dates, minimum clicks; Hypothesis, Change, Control/Variant; status tag (`draft`, `pending approval`, `running`, `completed`, `cancelled`).
- Results (jab hon):
  - Verdict banner: "Variant is better (statistically significant)", "Control is better (statistically significant)", "No significant difference yet", "Variant looks better (directional ...)", "Control looks better (directional ...)", "Not enough data to decide".
  - Control aur Variant ke box: period, impressions, clicks, cost, conversions.
  - Table columns: `Metric` (CTR, Conversion rate, Avg. CPC, Cost / conversion), `Control`, `Variant`, `Change` (percent lift; hara = behtar, laal = kharab; CPC aur cost/conv mein kam = behtar), `p-value` (chhota matlab farq pakka hai; 0.05 se neeche = significant), `Test` (two-proportion z-test ya directional).
  - `Limitations` list aur "Computed <date> from synced Google Ads data. Significant = p < 0.05."

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Ads account` dropdown | Account badalta hai | `GET /api/v1/experiments/accounts` | Koi bhi signed-in user |
| `New experiment` | Create form kholta hai | Sirf UI | Form dekhna sab ke liye; save RECOMMEND |
| Form: `Name` | Experiment ka naam (zaroori, max 255) | Save par `POST /accounts/{id}` | Analyst aur upar |
| Form: `Type` — `A/B (same dates)` / `Before / after` | Test ka tareeka | Same | Analyst aur upar |
| Form: `Hypothesis` | Aapka andaza, jaise "Fixed-price airport headlines will lift CTR" | Same | Analyst aur upar |
| Form: `What changes` | Kya badla ja raha hai (text) | Same; approval request mein "change" ban kar jaata hai | Analyst aur upar |
| Form: `Compare` | campaigns / ad groups / ads mein se chunta hai | Entity list `GET /accounts/{id}/entities` (pichhle 90 din ke clicks ke hisaab se sorted) | Analyst aur upar |
| Form: `Primary metric` | CTR, Conversion rate (in par significance test hota hai); Avg. CPC, Cost / conversion ("directional" likha aata hai, test nahi) | Same | Analyst aur upar |
| Form: `Control` (A/B) ya `Campaign / ad group / ad that changed` (Before/after) | Control entity chunta hai (naam ke saath status aur clicks/90d) | Synced P05 data | Analyst aur upar |
| Form: `Variant` (sirf A/B) | Variant entity; control se alag honi chahiye | Synced P05 data | Analyst aur upar |
| Form: `Baseline from` / `Baseline to` (sirf Before/after) | Pehle ka period; test period shuru hone se pehle khatam hona chahiye | Same | Analyst aur upar |
| Form: `Test from` / `Test to` | Test ki tareekhein | Same | Analyst aur upar |
| Form: `Minimum clicks per side` | Kam se kam clicks (10 se 100000; default 100), jinke bina verdict nahi aata | Same | Analyst aur upar |
| `Save draft` | Draft save karta hai (naam aur control zaroori, warna disabled) | `POST /accounts/{id}` -> local database | Analyst aur upar (RECOMMEND) |
| Form ka `Cancel` | Form band karta hai | Sirf UI | Koi bhi |
| Left list ke items | Experiment chunte hain | Local | Koi bhi signed-in user |
| `Submit for approval` (draft par) | Approval Center mein "Run experiment '<naam>'" request banata hai; status `pending approval`. Message: "Sent to the Approval Center." | `POST /{id}/submit` -> P16 | Analyst aur upar |
| `Preview results` (draft par) | Abhi tak ke data se result dikhata hai (save nahi hota). Test period shuru na hua ho to error "The test period has not started yet" | `POST /{id}/analyze` -> P05 data + stats | Analyst aur upar |
| `Start` (pending approval par) | Experiment ko `running` karta hai, par tabhi jab approval "approved" ho. Approval rejected/withdrawn ho to experiment wapas draft ho jata hai | `POST /{id}/start` -> P16 ka status padhta hai | Analyst aur upar |
| `Update results` (running par) | Result dobara nikalta hai aur save karta hai. Message: "Results updated." | `POST /{id}/analyze` | Analyst aur upar |
| `Conclusion` box | Aapne kya seekha / aage kya karenge (max 4000) | `complete` ke saath | Analyst aur upar |
| `Complete experiment` | Last baar result nikalkar save karta hai, conclusion likhta hai, status `completed`. Conclusion khaali ho to disabled | `POST /{id}/complete` | Analyst aur upar |
| `Cancel experiment` | Completed/cancelled ke alawa kisi bhi status par experiment `cancelled` karta hai | `POST /{id}/cancel` | Analyst aur upar |
| Approval Center link | `/approvals` kholta hai (pending approval par "Approval: <status>" ke saath) | Navigation | Koi bhi |

**Kaise use karein:**
1. `New experiment` dabayein. Naam, Type, Hypothesis, What changes bharein.
2. `Compare` aur `Primary metric` chunein, phir Control (aur A/B mein Variant) chunein. Before/after mein baseline dates daalein. Test dates aur minimum clicks tay karein.
3. `Save draft` dabayein. Chahein to `Preview results` se dekh lein.
4. `Submit for approval` dabayein, phir `/approvals` mein approver se approve karwayein (P20 seedha request bhejta hai, "Sync queue" ki zaroorat nahi).
5. Approve hone ke baad experiment par wapas aakar `Start` dabayein. Jo asli change test karna hai (naya ad, budget split) wo aap Google Ads mein alag se karte hain; ye page wo nahi karta.
6. Beech mein `Update results` se progress dekhein. Test khatam hone par `Conclusion` likhkar `Complete experiment` dabayein.

**Dhyan rakhne ki baat:**
- Ye page Google Ads mein kuch nahi badalta. "Approval" sirf experiment chalane ka record hai; `start_experiment` P17 se execute nahi hota.
- Verdict tabhi aata hai jab dono side par minimum clicks pure hon, warna "Not enough data to decide".
- Avg. CPC aur Cost / conversion par significance test nahi hota — sirf "directional" (lagta hai behtar/kharab).
- Before/after mein alag dates compare hote hain, isliye seasonality, competitors aur dusre badlaav bhi asar daalte hain (limitation mein yahi likha aata hai). Ise "evidence" samjhein, "proof" nahi.
- GA4/conversion tracking mein critical problem ho to conversion wale numbers par bharosa na karein (limitation mein aayega). Account se website linked na ho to bhi limitation aati hai.
- Sirf `draft` experiment edit ho sakta hai (backend mein edit hai, par is page par edit ka button nahi hai). `Start` button test ke dates nahi jaanchta, sirf approval jaanchta hai.

---

## Monitoring & Alerts — `/monitoring` (Module P18)
**Ye page kya hai:** Ye har Google Ads account ke last 7 din ko uske pichhle 28 din ke average hafte se compare karke batata hai ki kuch gadbad to nahi: spend achanak badha ya ruka, conversions gire, CPC/CTR badla, naye search terms budget kha rahe hain, ya tracking toota. Har problem ke liye ek hi alert banta hai, aur problem hatne par alert khud band ho jata hai.

**Data kahan se aata hai:**
- Google Ads synced daily data aur search terms: P05.
- Tracking problems: P06 (tracking health), us website ke liye jo is Ads account se linked ho.
- Alerts aur runs local database mein (`alerts`, `monitor_checks`).
- Checks tab chalte hain jab aap `Run checks now` dabate hain, ya (agar on ho) Windows scheduled task se roz. Scheduled run tabhi chalta hai jab flag `monitoring.scheduled.enabled` on ho; off ho to page par likha aata hai "Automatic daily checks are off — they need the flag `monitoring.scheduled.enabled` and a Windows scheduled task." Scheduled run se pehle Google Ads sync (P05) chalana chahiye taaki numbers taaza hon.
- Ye page sirf padhta hai; Google Ads mein kuch change nahi karta.

**Screen par kya dikhta hai:**
- Header: link "Budget & bid insights →" (`/budget-bid`), account dropdown, `Run checks now`.
- Explain text: kaun si cheezein compare hoti hain.
- Tabs `Open` (isme "acknowledged" bhi aate hain) aur `Resolved`.
- Alert cards (critical pehle, phir warning, phir info):
  - Severity tag: `critical` (laal, turant dekhein), `warning` (peela, dhyan dein), `info` (grey, jaankari).
  - Title, detail, evidence (jaise "Last 7 days" aur "Weekly avg (28 days before)" ke spend/clicks/conversions), "Do:" line (kya karna hai), "First seen ... · seen N×" (kitni baar check mein mila), resolved ho to kab aur kisne.
  - Link `Open →` (relevant page par), tag "acknowledged by <email>".
- `Recent checks` section: pichhle 10 runs — time, trigger (manual/scheduled), status, aur "N issue(s), N new, N cleared" ya error.
- Khaali: "All clear — no open alerts." / "No checks run yet. Click "Run checks now"." / "No resolved alerts yet."

**Checks (code, kab fire hota hai):**

| Code | Kab fire hota hai | Severity |
|---|---|---|
| `spend_spike` | Last 7 din ka spend usual weekly average ka 1.5 guna ya zyada (aur kam se kam AUD 50) | warning; 2.5 guna par critical |
| `spend_stopped` | Usual weekly spend kam se kam AUD 50 tha, par last 7 din mein zero | warning |
| `conversion_drop` | Usual weekly conversions kam se kam 3 the aur ab aadhe ya kam | warning; zero hone par critical |
| `cpc_change` | Average CPC 30% ya zyada upar/neeche (dono side kam se kam 30 clicks) | warning (badhe), info (ghate) |
| `ctr_drop` | CTR 30% ya zyada gira (dono side kam se kam 1000 impressions) | warning |
| `no_recent_data` | Pichhle 3 din mein koi impressions nahi (campaigns paused ya data sync nahi hua) | info |
| `search_term_shift` | Is hafte pehli baar dikhe search terms spend ka 30% ya zyada kha gaye (kam se kam AUD 20) | warning |
| `tracking:<code>` | Linked website ki har critical tracking-health problem (P06) | critical |

"Last 7 days" ka matlab kal tak ke 7 poore din (aaj ka adhoora din shamil nahi).

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Budget & bid insights →` (link) | `/budget-bid` page kholta hai | Navigation | Koi bhi signed-in user |
| `Ads account` dropdown | Account badalta hai (1 se zyada ho to) | `GET /api/v1/monitoring/accounts` | Koi bhi signed-in user |
| `Run checks now` | Sab checks abhi chalata hai. Message: "Checked: N issue(s) found · N new · N cleared." | `POST /accounts/{id}/run` -> P05 + P06 data padhta hai, alerts update/auto-resolve karta hai, run record likhta hai | Analyst aur upar (RECOMMEND) |
| Tab `Open` / `Resolved` | Chalu (open + acknowledged) ya band alerts dikhata hai | `GET /accounts/{id}` (resolved ke liye `?status=resolved`) | Koi bhi signed-in user |
| `Open →` (alert par link) | Us problem se jude page par le jata hai (Campaigns, Conversions, Keywords, Ads & Assets, Search Terms, Ads Accounts) | Navigation | Koi bhi |
| `Acknowledge` | Dikhata hai ki aapne dekh liya. Alert list mein bana rehta hai, "acknowledged by" likha aata hai. Sirf open alert par | `POST /alerts/{id}/status` | Analyst aur upar |
| `Mark resolved` | Haath se resolved kar deta hai (open aur acknowledged dono par) | `POST /alerts/{id}/status` | Analyst aur upar |

**Kaise use karein:**
1. Pehle Google Ads sync kar lein (Ads Accounts page) taaki data taaza ho.
2. `/monitoring` par account chunein aur `Run checks now` dabayein.
3. `Open` tab mein alerts padhein — pehle `critical`. "Do:" line aur evidence dekhein.
4. `Open →` se related page par jaakar problem theek karein.
5. Dekh liya to `Acknowledge` karein. Theek ho gaya to dobara `Run checks now` dabayein — alert khud "resolved" ho jayega (resolved by "auto"). Chahein to `Mark resolved` se haath se bhi band kar sakte hain.
6. `Recent checks` mein dekhein ki last run kab hua aur fail to nahi hua.

**Dhyan rakhne ki baat:**
- Alerts tabhi update hote hain jab check chale. Roz ke automatic check ke liye flag aur Windows scheduled task alag se lagana padta hai.
- `Mark resolved` ke baad agar problem abhi bhi hai, to agla check naya alert khol dega.
- Thresholds jaan-bujhkar conservative hain, isliye alerts kam aate hain. Chhote accounts (kam spend/clicks) par kai checks fire hi nahi hote.
- `conversion_drop` aur `tracking:` alerts saath aa sakte hain — pehle tracking check karein, tag toota ho to conversions bhi girte hain.
- Change-impact monitoring (executed change ke baad asar) abhi bani nahi hai.
- Ye page Google Ads mein kuch nahi badalta.

---

## Reports — `/reports` (Module P19)
**Ye page kya hai:** Google Ads account ya website ka daily, weekly, monthly ya custom-date report banane ki jagah. Har report ek snapshot ki tarah save hota hai (baad mein data badle to bhi report nahi badalta), aur use CSV ya printable page (PDF) mein le sakte hain.

**Data kahan se aata hai:**
- Report naya kuch calculate nahi karta; ye dusre modules ka data jodta hai (last sync tak ka):
  - Google Ads account report: KPIs, campaigns, search terms P05 se; linked website ka funnel P13 se; open recommendations P14 se; approval decisions P16 se; open alerts P18 se.
  - Website report: GA4 sessions/channels, Search Console top queries, bookings aur tracking issues P06 (website overview) se; funnel P13 se.
- Snapshot local database (`report_runs`) mein save hota hai.
- Isliye report banane se pehle Google Ads aur GA4 sync kar lein.

**Screen par kya dikhta hai:**
- `New report` form (neeche controls).
- Note: "Sync Google Ads and GA4 first for up-to-date numbers. Each report is saved as a snapshot, so it won't change later."
- Left list: saved reports (title, period label, kab bana). Khaali: "No reports yet."
- Right: selected report ka title, do links, aur report ka preview (iframe).
- Report ke sections:
  - Account report: headline (jaise "Spend AUD ... (+x% vs previous period)", clicks aur conversions, cost per conversion); `Key figures` (Metric, This period, Previous, Change — Impressions, Clicks, Cost, Conversions, Conv. value, CTR, Avg. CPC, Cost/conv.); `Campaigns` (top 20 jinme spend ya clicks hain: Status, Clicks, Cost, Conv., Cost/conv.); `Top search terms by cost` (top 15); `Funnel — <website>` (Stage, Value, Rate, Cost per, Source; estimate ho to likha aata hai); `Open recommendations` (top 10); `Approval decisions` (is period ke); `Open alerts`.
  - Website report: headline (GA4 sessions/engaged/key events; Search Console clicks/impressions; bookings aur revenue); `GA4 traffic by channel`; `Search Console — top queries` (top 15, avg position ke saath); `Bookings` (channel-wise count aur revenue AUD); `Tracking & data issues` (sirf critical/warning); `Funnel`.
  - Last mein notes: "Figures come from the last data sync ... Nothing in this report was changed in Google Ads." GA4 data baad ki date se shuru ho to uska note bhi aata hai.
- "Previous" ka matlab: pichhla barabar ka period (monthly ke liye pichhla poora mahina).

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Report on` — `Google Ads account` / `Website` | Report kis cheez ka hoga | `GET /api/v1/reports/options` (accounts aur websites ki list) | Koi bhi signed-in user |
| `Which` | Kaun sa account ya website | Same options list | Koi bhi signed-in user |
| `Period` — `Daily (yesterday)`, `Weekly (last 7 days)`, `Monthly (last full month)`, `Custom dates` | Time range. Weekly = kal tak ke 7 din; Monthly = pichhla poora calendar month | Same | Koi bhi signed-in user |
| `From` / `To` (sirf Custom par) | Apni tareekhein; From, To se pehle ho aur 2 saal se zyada nahi | Report ke saath bheje jaate hain | Koi bhi signed-in user |
| `Generate report` | Report banata hai aur list mein sab se upar jodta hai. Message: "<title> ready." | `POST /api/v1/reports/runs` -> dusre modules ka data padhkar snapshot save | Koi bhi signed-in user (viewer bhi — ye sirf padhta hai) |
| Left list ke items | Saved report chunna | `GET /runs` (latest 50) | Koi bhi signed-in user |
| `Download CSV` | CSV file `report-<id>.csv` download karta hai (har section ek block) | `GET /runs/{id}/csv` | Koi bhi signed-in user |
| `Open printable / Save as PDF` | Naye tab mein saaf printable page kholta hai; wahan "Print / Save as PDF" button se browser mein PDF ban jata hai | `GET /runs/{id}/html` | Koi bhi signed-in user |
| Preview iframe | Report ka HTML isi screen par dikhata hai | `GET /runs/{id}/html` | Koi bhi signed-in user |

**Kaise use karein:**
1. Pehle Google Ads aur GA4 sync kar lein (nahi to numbers purane honge).
2. `/reports` par `Report on` chunein (account ya website), phir `Which`.
3. `Period` chunein. Custom ho to `From` aur `To` bharein.
4. `Generate report` dabayein. Report left list mein aur preview mein khul jayegi.
5. CSV chahiye to `Download CSV`; PDF chahiye to `Open printable / Save as PDF` dabayein aur naye tab mein "Print / Save as PDF" chunein.

**Dhyan rakhne ki baat:**
- Report ek snapshot hai. Baad mein data sync hone se purani report nahi badalti; naya data chahiye to naya report banayein.
- Reports mein sirf wahi dikhta hai jo dusre modules ke paas pehle se hai — koi naya calculation ya AI ka andaza nahi.
- Page par report delete karne ka button nahi hai. List mein sirf latest 50 dikhte hain.
- Website report mein account ke KPIs (spend, CPC) nahi hote, aur account report mein GA4 channels nahi hote — dono alag hain.
- Report banane se Google Ads mein kuch change nahi hota.

---

## Audit Log — `/audit-log` (Module P22)
**Ye page kya hai:** Ye ek sirf-padhne wala record hai ki kisne kab kya sensitive kaam kiya, aur pehle/baad ki value kya thi. Isme kuch edit ya delete nahi ho sakta (append-only). Ye page sirf admin dekh sakta hai.

**Data kahan se aata hai:**
- Local database table `audit_logs` (P22). Dusre modules apne kaam ke saath yahan entry likhte hain; P22 khud kuch generate nahi karta.
- Abhi jo cheezein code mein record hoti hain:
  - P16 Approval Center: har approve, reject, withdraw (actions `approval_approved`, `approval_rejected`, `approval_withdrawn`) aur `approval_executed`.
  - P09 Ads & Assets: ad draft ka status badalna (`ad_draft_<status>`, jaise approved/rejected).
  - P17 Execution: har validate, execute aur rollback (`execution_<mode>_<status>`, jaise `execution_validate_validated`, `execution_execute_executed`, `execution_execute_failed`).
  - P17 CLI: live execution flag on/off (`execution_flag_on`, `execution_flag_off`); actor server ka OS user hota hai.
- Experiments, Monitoring, Reports ke actions code mein yahan record hote nahi dikhe.

**Screen par kya dikhta hai:**
- Explain text: "Every approval decision and ad draft review ..." (ye line purani hai; ab execution aur flag changes bhi record hote hain).
- Filters (dropdown aur boxes).
- Entries ki list (ek page par 25, naya pehle). Har entry mein:
  - Module tag (P16, P09, P17...), `action`, time.
  - Actor (email ya "system"), role bracket mein, `entity_type #entity_id`.
  - `Before` aur `After` (JSON, ek line mein) agar maujood hon.
  - `Note` agar likha ho.
- Neeche "1–25 of N" counter aur `Previous` / `Next` buttons.
- Khaali: "No matching entries."
- Non-admin ko: "Admin permission required to view the audit log."

**Buttons aur controls:**

| Control (exact label) | Kya karta hai | Data kahan se / kahan jaata hai | Kaun kar sakta hai |
|---|---|---|---|
| `Module` dropdown | Sirf ek module ki entries (list mein wahi modules aate hain jinki entry maujood ho) | `GET /api/v1/security/audit-logs/facets` aur `audit-logs?module_id=` | Sirf admin |
| `Action` dropdown | Sirf ek action type (maujood actions se banti hai) | Same (`action=`) | Sirf admin |
| `Actor` (box, "email") | Kisi ek vyakti ki entries; poora email exact likhna padta hai | `actor=` | Sirf admin |
| `Entity type` (box, "approval, ad_draft…") | Kis cheez par action hua (approval, ad_draft, flag...) | `entity_type=` | Sirf admin |
| `Entity id` (box) | Us cheez ki id (jaise approval ka number) | `entity_id=` | Sirf admin |
| `Previous` / `Next` | 25-25 entries ke page aage-peeche | `limit=25&offset=` | Sirf admin |

(Filter badalte hi list pehle page par wapas aa jaati hai. Date filter `since`/`until` backend mein hai, par is page par uska control nahi hai.)

**Kaise use karein:**
1. Admin account se sign in karke `/audit-log` kholein.
2. Kisi approval ka itihaas dekhna ho to `Entity type` mein `approval` aur `Entity id` mein uska number likhein.
3. Kisi vyakti ke kaam dekhne ho to `Actor` mein uska poora email likhein.
4. Kisi module tak seemit karne ke liye `Module` ya `Action` dropdown use karein.
5. Entry mein `Before` aur `After` padhein, aur `Note` mein reason dekhein. Zyada entries ho to `Next` dabayein.

**Dhyan rakhne ki baat:**
- Sirf admin dekh sakta hai. Analyst, approver, viewer ko "Admin permission required" dikhega.
- Append-only: API mein edit ya delete ka koi raasta nahi hai. Is page se koi change nahi hota.
- Yahan wahi dikhta hai jo dusre modules ne record karna chuna. Har click yahan nahi aati (jaise "Sync queue" ya report banana record hote nahi dikhe).
- `Actor` filter exact email match hai, adhoora naam kaam nahi karega.
- Before/after mein sirf status jaisi cheezein jaati hain; secrets ya passwords record karne ka koi code nahi hai.
- Time aapke browser ke local time (en-AU format) mein dikhta hai.

---

# Aakhri hissa: Roles, Locks, Glossary, FAQ

## A. Roles (kaun kya kar sakta hai)

| Role | Kya kar sakta hai |
|---|---|
| `viewer` | Sab pages dekh sakta hai. Koi change nahi kar sakta. |
| `analyst` | Viewer + analysis chalana, sync, suggestions banana (Run audit, Analyze, Generate report, Run analysis, draft likhna). |
| `approver` | Analyst + Approval Center mein `Approve` / `Reject`. |
| `admin` | Approver + users manage karna, Audit Log dekhna, settings. |
| `execute` (alag switch) | Role nahi, ek **alag permission** hai. Sirf server ke command-line se kisi user ko di jaati hai. Iske bina live change nahi ho sakta. |

Self-approval: jisne suggestion banayi, wo usse khud approve nahi kar sakta (Approval Center ka rule).

## B. Safety locks (live Google Ads change kyun nahi hota)

Live change ke liye ye **sab** zaroori hain. Abhi inme se zyada tar band hain:

1. Kill switch `ADS_EXECUTION_KILL_SWITCH=true` -> ye sab se upar hai. Jab tak ON hai kuch nahi chalta.
2. Flag `ads.execution.enabled` ON hona chahiye (sirf P17 ke command-line se).
3. User ko `execute` permission mili ho (`set-execute` command se).
4. Change pehle Approval Center mein **Approved** ho.
5. 24 ghante ke andar `Validate with Google` (jo kuch change nahi karta) pass hua ho.
6. Screen par `EXECUTE` type karke confirm kiya ho.

Bina inke `Execute live` kaam nahi karta. Galti se kuch nahi hoga.

## C. Feature flags (switches) ki current halat

| Flag | Matlab | Abhi |
|---|---|---|
| `crawler.enabled` | Website scan allowed | ON |
| `competitor.research.enabled` | Competitor public site research allowed | ON |
| `ai.live_calls.enabled` | Live Claude AI use ho | ON |
| `ads_sync.scheduled.enabled` | Scheduled Ads sync | ON |
| `monitoring.scheduled.enabled` | Scheduled monitoring checks | ON |
| `ads.execution.enabled` | Live Google Ads change allowed | OFF (kill switch) |
| `ads.execution.automation.enabled` | Auto-execute | OFF (kill switch) |

## D. Glossary (shabdon ka matlab)

| Shabd | Matlab |
|---|---|
| Impressions (Impr.) | Aapka ad kitni baar dikha |
| Clicks | Kitne logon ne ad par click kiya |
| CTR | Click-through rate = clicks / impressions. Zyada = ad pasand aaya |
| Avg CPC | Ek click ka average kharcha |
| Spend / Cost | Kul kharcha (AUD) |
| Conv. / Conversions | Kitne logon ne quote/booking jaisa kaam kiya |
| Cost/conv. | Ek conversion ka kharcha (CPA) |
| Search term | Jo asli shabd logon ne Google par type kiya |
| Keyword | Jo shabd aapne bid ke liye chuna |
| Negative keyword | Aisa shabd jis par aap ad dikhana nahi chahte |
| Ad group | Ek jaise keywords + ads ka group |
| RSA | Responsive Search Ad (kai headlines/descriptions, Google mix karta hai) |
| Quality Score | Google ka 1-10 score keyword/ad/landing page ki quality ka |
| Impression share | Kitne possible dikhne ke mauke mein se aap kitni baar dikhe |
| Lost to budget / rank | Kitne mauke budget ya kam rank ki wajah se chhoot gaye |
| GA4 | Google Analytics 4, website visitors aur events ka tool |
| GSC | Google Search Console, organic search ka data |
| `generate_lead` | GA4 ka event jo thank-you page par lead hone par fire hota hai |
| Observed / Attributed / Confirmed | Observed = tracking mein dikha. Attributed = Google Ads ko credit. Confirmed = booking records se match hua |
| Paused / Removed | Paused = ruka hua par wapas chal sakta hai. Removed = hamesha ke liye hata diya |
| Not measured | Is cheez ka data hai hi nahi (0 nahi). Isse 0 mat samjho |
| est. | Anuman (estimate), pakka number nahi |
| Confidence % | App ko apni salah par kitna bharosa hai |
| Approved / Executed | Approved = aapne haan kaha. Executed = Google Ads mein sach mein lag gaya (abhi nahi hota) |

## E. Aksar poochhe jaane wale sawal (FAQ)

**Q1. Maine Approve kiya, par Google Ads mein kuch nahi badla. Kyun?**
Ye sahi hai. Approve sirf app ke andar "haan" hai. Google Ads mein change ke liye `/execution` ke saare locks khulne chahiye. Abhi sab lock hain. Chaho to suggestion ko Google Ads Editor ke CSV export se manually apply karo.

**Q2. Bookings / Revenue "not measured" kyun dikhta hai?**
Kyunki booking aur amount ka data app ko nahi mila (Driver App ka access nahi hai, Zoho emails mein amount nahi). Conversions page se bookings CSV import karoge to ye bharne lagega.

**Q3. Dashboard par purana data dikh raha hai.**
Header ka `Sync now` dabao. Last sync ka time page par likha hota hai.

**Q4. Removed campaigns kyun nahi dikhte?**
Idle removed campaigns by default chhupe hote hain. Page par `Show removed` toggle on karo.

**Q5. Sab campaigns paused hain, kya app ko dikkat hai?**
Nahi. Abhi sirf `29Sept_Corporate_Ads_Campaign` bacha hai aur wo PAUSED hai. Page par warning banner aata hai. Campaign Google Ads mein hi enable karo. Enable karne se pehle location option "Presence" karna na bhoolo.

**Q6. AI ka jawab "template" likha hai, live Claude nahi.**
Ya to `ai.live_calls.enabled` OFF hai ya API key mein dikkat hai. Label dekh kar pata chalta hai ki jawab live AI ka hai ya rule-based.

**Q7. Alert baar-baar aa raha hai.**
`Acknowledge` karo (maine dekh liya) ya problem sudhar kar `Mark resolved`. Agle check mein problem khatam ho to alert khud resolve ho jaata hai.

**Q8. Ek page par button disabled / dikh nahi raha.**
Aapka role kam hai. Upar ke Roles table se dekho. Admin se role badalwao.

**Q9. Kisi galti ya change ka record kahan milega?**
`Audit Log` page par (sirf admin). Har approve, reject, execute, flag change ka record wahan hai aur wo badla nahi ja sakta.

**Q10. Server par daalna ho to?**
`docs/DEPLOY.md` aur `docs/GO_LIVE_CHECKLIST.md` dekho. Ek hi domain par poora app chalta hai (login cookie isi ki wajah se).

## F. Madad ke liye files

| File | Kis kaam ki |
|---|---|
| `docs/DEPLOY.md` | Server par deploy karna |
| `docs/GO_LIVE_CHECKLIST.md` | Live jaane se pehle ki list |
| `docs/RUNBOOK.md` | Kuch kharab ho jaye to kya karein, backup/restore |
| `docs/SECURITY.md` | Security ke niyam |
| `docs/bookings_import_template.csv` | Bookings CSV ka sample |
| `docs/MODULE_REGISTRY.md` | Sabhi modules (P00 se P24) ki list |
