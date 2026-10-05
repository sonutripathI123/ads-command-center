# AI Google Ads Command Center — User Manual (Hinglish)

Yeh manual business owner ke liye hai (Corporate Cars Melbourne / Opal Chauffeurs). Har section kya karta hai,
data kahan se aata hai, aur abhi kaunsa mode (live ya test) mein chal raha hai — sab yahan seedha bataya gaya hai.

## Sabse pehle: Data audit ka result

Poora backend aur frontend check kiya gaya (2 independent deep-dive audits) — **kahin bhi fabricated/fake/demo
data nahi mila jo real data ban ke dikhaya ja raha ho.**

- Har page apna data seedha backend API se fetch karta hai (`fetch()`/`call()` se), koi bhi number/list hardcoded
  nahi hai jo asli lage.
- Jab bhi AI (Claude) band hota hai, system ek clearly-labeled "Template" ya "Rule-based (AI off)" version dikhata
  hai — kabhi bhi template output ko asli AI-likha hua content bata ke nahi dikhaya jaata. Har jagah "Written by
  Claude" vs "Template/Rule-based" saaf likha hota hai.
- Jo numbers "estimate" hain (jaise leads ka estimate P13 mein) unpe hamesha "(estimate)" ya "est." label lagा
  hota hai. Jo cheez measure nahi ho payi (jaise abhi tak koi booking import nahi hui) usko "not measured" dikhaya
  jaata hai, kabhi bhi jhootha "0" nahi.
- Sirf 2 chhoti cosmetic cheezein mili (bug nahi): Ads & Assets ke ad preview mein khaali URL field ke liye
  "example.com" placeholder, aur Campaign Builder/Business Rules ke form mein load hone se pehle ek default number
  dikhta hai jo turant real data se replace ho jaata hai. Yeh dono normal form-input behavior hain, data fabrication
  nahi.

**Matlab: jo bhi numbers/insights aapko dikh rahe hain (chahe AI se likhe ho ya template se), woh ya to real synced
data se calculate hue hain, ya clearly bataya gaya hai ki yeh ek placeholder/template hai.**

## App kaise organized hai

Sidebar mein 6 groups hain — Overview, Sources, Google Ads, Insights, Actions, Operations. Har section ek "module"
(P00 se P22 tak) ke through banaya gaya hai. Har module ka apna status hota hai:

- **approved_frozen** = business owner (aap) ne review karke final approve kar diya hai — yeh ab locked hai, bina
  approval ke change nahi hoga.
- **review** = bana hua hai, kaam kar raha hai (real data ke saath), lekin abhi aapki final "haan yeh sahi hai"
  wali approval baaki hai.
- **planned** = abhi tak banaya hi nahi gaya (sirf future roadmap mein hai).

---

## OVERVIEW

### Sync now (upar header mein, har page par)
Ek click mein Google Ads + GA4 + Search Console ka fresh data aata hai (sirf padhta hai, Google Ads mein kuch change nahi
karta), phir monitoring alerts refresh hote hain, aur page apne aap reload hoke naya data dikhata hai. Ye apne aap nahi
chalta (scheduled sync off hai), isliye subah/jab bhi naya data dekhna ho tab dabao. Analyst/approver/admin role chahiye.

**Roz subah 7 baje automatic sync (Windows Task Scheduler):** `scripts/daily_sync.ps1` Google Ads + GA4 + Search Console
sync karta hai aur monitoring check chalata hai (sab read-only). Log: `C:\Users\Administrator\.ads-command-center\logs\daily_sync.log`.
Task ek baar *Administrator PowerShell* mein banana padta hai (command docs/DEPLOY.md mein). PC us waqt on ho (nahi to agli
baar on hote hi chalega). Server par deploy ke baad script ki jagah cron use hota hai.

### Overview (P01 — approved_frozen)
Dashboard ka home page. Yahan se website aur Google Ads account select karte hain (upar dropdown), aur backend
health / kill-switch status dikhta hai. Isme khud koi business logic nahi hai — yeh sirf baaki modules ko jodta
hai.

---

## SOURCES

### Websites (P03 — approved_frozen)
Apni websites (corporatecarsmelbourne.com.au, opalchauffeurs.com.au) yahan add karte hain — domain, service, area,
linked Google Ads account. Ek "scan" chalta hai (`crawler.enabled` flag se, **abhi ON hai**) jo har page ko padhta
hai aur dikhata hai: title/H1 missing, CTA nahi hai, form/phone nahi hai, page slow hai, wagera. Ads ke final URLs
ko scanned pages se match bhi karta hai (broken link pakadne ke liye).

### Ads Accounts (P04 — approved_frozen)
Google Ads account ko connect karna (OAuth login), manager account ke neeche ke accounts dhoondhna, aur connection
health check karna. **Sirf read-only** — yahan se Google Ads mein kabhi kuch change nahi hota.

### Conversions (P06 — approved_frozen)
GA4 (website analytics), Search Console, aur bookings (CSV import) — teeno ek jagah. Yeh teen tarah ke number alag
rakhta hai: **observed** (GA4/GSC ne kya dekha), **attributed** (Google Ads ne kya conversion mana), **confirmed**
(asli booking). Tracking mein problem ho to yahan automatically pakda jaata hai (jaise "GA4 se koi lead event nahi
aa raha").

---

## GOOGLE ADS

### Campaigns / Ad Groups (P05 — approved_frozen)
Aapke Google Ads account ka real synced data — campaigns, ad groups, daily spend chart. Har sync ke baad yeh
update hota hai ("Sync now" button se).

### Keywords / Search Terms (P05 base + P08 — approved_frozen)
P05 raw keyword/search-term data dikhata hai; P08 uske upar intent classify karta hai (yeh search "service" hai ya
"galat location" hai ya "competitor ka naam" hai) aur **negative keyword suggestions** deta hai — evidence aur
confidence % ke saath. Aap accept/reject karte ho, kuch bhi automatically Google Ads mein nahi jaata.

### Ads & Assets (P09 — review)
Existing ads ko check karta hai (Google ke rules ke against — headline zyada lamba, "!" use hua, competitor naam
aaya, wagera), aur naye ad (RSA) likhta hai — **Claude AI se (abhi live hai) ya template se**. Draft banta hai,
approve karne ke baad CSV export hota hai (Google Ads Editor ke liye) — **kabhi bhi seedha Google Ads mein launch
nahi hota**.

---

## INSIGHTS

### Bookings / Revenue (P13 — review)
Ek funnel dikhata hai: ad impressions → clicks → website visits → leads (estimate) → bookings → revenue. Jo step
measure nahi ho paaya (abhi tak koi booking import nahi hui, koi lead event set nahi hai) uspe "not measured"
likha hota hai. Jahan funnel leak ho raha hai (jaise "GA4 mein koi lead event set nahi hai") woh bataya jaata hai.

### Landing Pages (P10 — review)
Har page jahan ads bhejte hain use check karta hai — CTA hai ya nahi, form hai ya nahi, trust signals (reviews,
guarantee) hain ya nahi, mobile-friendly hai ya nahi, speed kaisi hai. Fir developer ke liye ek "implementation
brief" banata hai (kya fix karna hai) — **Claude AI se ya template se**, dono mein fake facts/ratings kabhi invent
nahi kiye jaate, sirf `[your Google rating]` jaise bracket placeholders diye jaate hain jo aapko khud bharne hain.

### Competitors (P11 — review)
Named competitors ki **public** website research karta hai (unki Google Ads ka data kabhi nahi le sakta — woh kisi
ko bhi nahi dikhta). Service/location coverage compare karta hai (kaunsi cheez competitor ke paas hai jo aapke paas
nahi), aur ek AI/template interpretation deta hai (strengths/weaknesses/opportunities). **Flag `competitor.research.enabled`
abhi ON hai**, matlab real crawling ho rahi hai.

### AI Recommendations (P14 — approved_frozen)
P07 audit se mile issues ko ek central list mein laata hai, priority laga ke. Har recommendation ke saath ek AI
action plan bhi hai (**Claude AI se, abhi live**) jo bataata hai kya karna hai aur kyun. Aap accept/reject karte ho.

---

## ACTIONS

### Campaign Builder (P15 — review)
Existing keywords se ek **draft, paused** campaign banata hai — service ke hisaab se ad groups (Airport, Wedding,
Corporate, wagera), negatives, ads (P09 se), aur ek launch checklist. **Kabhi bhi Google Ads mein khud se create
nahi karta** — sirf draft + CSV export.

### Approval Center (P16 — review)
Har proposed change (chahe woh negative keyword ho, naya ad ho, naya campaign ho) yahan ek queue mein aata hai —
before/after, evidence, risk ke saath. Aap approve/reject/withdraw karte ho. **Approve karne ka matlab yeh nahi ki
Google Ads mein change ho gaya** — asli execution alag module (P17) karta hai, jo **locked** hai (neeche dekho),
aur ek "kill switch" hamesha on hai jo kisi bhi live change ko rokta hai.

### Google Ads Execution (P17 — review, **locked**; page: `/execution`, Approval Center ke link se)
Approve ho chuke changes ko Google Ads tak pahunchane wala module. Abhi sirf do type: **negative keywords add karna** aur
**naya responsive search ad add karna (hamesha PAUSED)**. Baaki sab (naya campaign, bid/budget) haath se karna hai.
- **Validate:** Google se poochhta hai "ye request theek hai?" — **kuch change nahi karta**.
- **Execute (live):** tabhi chalega jab sab ek saath ho: kill switch off + execution flag on + aapke user ko execute
  permission + approval abhi bhi "approved" + aap `EXECUTE` type karo + wahi plan 24 ghante ke andar validate ho chuka ho.
- **Rollback:** execute se jo bana tha, sirf wahi hata deta hai.
- Har step audit log mein jaata hai. Ye kabhi apne aap, schedule se, nahi chalta.
- **Unlock sirf server pe operator karta hai** (website pe koi button nahi): `p02_auth.cli set-execute`, phir
  `p17_ads_execution.cli enable`, phir `ADS_EXECUTION_KILL_SWITCH=false`. Abhi sab **locked** hai, isliye Google Ads
  waisa hi hai jaisa tha.

### Budget & Bid Insights (P12 — review; page: `/budget-bid`, Monitoring ke link se)
Batata hai ki paisa **kis device, din, time aur jagah** par kaam kar raha hai ya waste ho raha hai, aur har campaign ko
**budget** ya **ad rank** rok raha hai. "Run analysis" dabane par Google Ads se sirf padhta hai (kuch badalta nahi).
Kam conversions hon to kisi din ya time ko "kharab" nahi bolta (kismat ho sakti hai); har point ke saath confidence aur
"expected conversions" dikhata hai. Aaj ki run ne pakda: Australia ke bahar ke clicks par ~AUD 296 kharch, aur campaign
44% searches ad rank par haar raha hai. Bid/schedule badalna Google Ads mein haath se karna hai.

### Experiments (P20 — review)
A/B test ya before/after test set up karna (ek change ka asar naapne ke liye). Start karne se pehle Approval Center
se approval chahiye. Result mein statistical significance test hota hai, aur agar data kam hai to "insufficient
data" saaf bataya jaata hai — jhootha result kabhi nahi diya jaata.

---

## OPERATIONS

### Monitoring & Alerts (P18 — review)
Account ko regularly check karta hai — spend achanak badh gaya, spend ruk gaya, conversions gir gaye, CTR/CPC mein
badlaav, tracking toot gaya, wagera. Ek problem ke liye ek hi alert rehta hai jab tak woh khud clear na ho jaaye.
Abhi "Run checks now" button se manual chalana padta hai (automatic daily schedule off hai).

### Reports (P19 — review)
Daily/weekly/monthly ya custom date ka report banata hai (account ke liye ya website ke liye) — key figures,
campaigns, funnel, recommendations, approvals, alerts sab ek jagah. CSV download ya PDF (print) ho sakta hai. Yeh
module khud koi naya data nahi banata, sirf baaki modules ka data ek report mein jodta hai.

### Business Rules (P21 — approved_frozen)
Yeh system ki "memory" hai — aapke services, areas, jo areas nahi serve karte, jo searches kabhi nahi chahiye,
competitor/brand names, thresholds (kitna spend hone ke baad negative keyword suggest kare). Yeh baaki AI modules
(P08, P09, wagera) is jaankari ko use karte hain. Har change ek naya version banata hai (purana history mein rehta
hai, delete nahi hota).

### Audit Log (P22 — review, **naya module, abhi-abhi banaya**)
Yeh security ke liye hai — kaun, kab, kya approve/reject kiya (ads change ho ya ad draft review), before/after
values ke saath. Sirf admin dekh sakta hai, aur yeh **kabhi edit ya delete nahi ho sakta** — ek permanent trail hai.

### Settings (P01 — approved_frozen)
Environment info aur feature flags ka status read-only dikhata hai.

---

## Zaroori cheezein jo har jagah lagu hoti hain

**1. Google Ads mein abhi koi live change nahi hota (locked)**
P17 (execution) ban chuka hai lekin **locked** hai: `ADS_EXECUTION_KILL_SWITCH` on hai — chahe koi flag on kar de, yeh
switch usse override kar deta hai. Matlab: jo bhi is app mein "approve" karte ho, woh sirf ek record hai, Google Ads mein
kuch nahi badalta jab tak operator server pe 3 alag cheezein (permission, flag, kill switch) khud unlock na kare.

**2. AI ke 2 mode — dono clearly labeled hain**
- Jab `ai.live_calls.enabled` flag ON ho (**abhi ON hai**) → Claude AI se real likha hua content aata hai, page pe
  "Written by Claude" jaisa likha hota hai.
- Jab OFF ho → ek deterministic template/placeholder version aata hai, page pe "Template (AI off)" ya "Rule-based"
  jaisa saaf likha hota hai.
Dono cases mein aapko pata chal jaata hai ki content AI ne likha ya template ne — kabhi confuse nahi hoga.

**3. Abhi kaunse flags ON/OFF hain (2026-09-29 tak)**
| Flag | Status | Matlab |
|---|---|---|
| `crawler.enabled` | **ON** | Apni websites (P03, P10) scan ho rahi hain |
| `competitor.research.enabled` | **ON** | Competitors ki public websites research ho rahi hai |
| `ai.live_calls.enabled` | **ON** | Claude AI live hai (ads, briefs, recommendations sab AI-written) |
| `ads_sync.scheduled.enabled` | off | Google Ads sync abhi manual button se chalana padta hai |
| `monitoring.scheduled.enabled` | off | Monitoring checks abhi manual button se chalana padta hai |
| `ads.execution.enabled` / `.automation.enabled` | off (kill-switch se locked) | Google Ads mein koi live change nahi ho sakta |

**4. Data ke 3 tarah**
- **Real synced data** — Google Ads (P05), GA4/Search Console (P06), bookings (P06 CSV import), website scan (P03).
- **AI-generated ya template content** — hamesha labeled, kabhi fake nahi bataya jaata as real.
- **Estimates** — jaise "estimated leads" — hamesha "(estimate)" likha hota hai, kabhi real number ki tarah nahi
  dikhaya jaata.

---

*Yeh manual `docs/USER_MANUAL_HI.md` mein save hai — jab bhi naya module banega ya koi flag change hoga, isko
update kar diya jaayega.*
