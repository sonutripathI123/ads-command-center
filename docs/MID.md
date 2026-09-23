MASTER IMPLEMENTATION DOCUMENT (MID)
AI Google Ads Specialist / PPC Command Center
Chauffeur Business — Claude Code Build & Controlled Change System

# 0. PURPOSE — READ THIS FIRST

This MID is the authoritative build contract for Claude Code. Claude Code must use this document to build the complete AI Google Ads Specialist and then maintain it section-by-section without unnecessarily reading, refactoring, redeploying, or modifying unrelated parts of the application.
- The first objective is to build the complete working product described in this MID.
- The second objective is controlled maintenance: after a section is approved, later changes must be isolated to that section and its minimum required direct dependencies.
- A local change must never become an excuse to refactor the entire backend.
- Existing approved behaviour is protected by default.
- Live Google Ads changes are approval-gated and disabled until explicitly enabled.

# 1. THE CORE PRINCIPLE: MODULAR ISOLATION

GLOBAL RULE

Every feature belongs to exactly one primary MODULE_ID.

Every module owns:
- its UI
- its backend service/routes
- its data access layer
- its AI prompts/logic
- its tests
- its documentation
- its feature flags
- its API adapter usage

A later change request MUST be resolved by:
1. Identifying the MODULE_ID from the request.
2. Opening that module's manifest/spec first.
3. Finding the smallest set of files responsible for the requested behaviour.
4. Reading only those files and direct dependencies.
5. Editing only those files unless a dependency is genuinely required.
6. Testing only the affected module plus necessary regression tests.
7. Reporting exactly what changed and what was intentionally untouched.


# 2. IMPORTANT REALITY — WHAT 'DO NOT READ THE WHOLE BACKEND' MEANS

The system must be architected so Claude can normally locate a feature without scanning the whole repository. Claude Code cannot be physically prevented from reading files, but this MID requires the repository to make broad reading unnecessary.
- Use a module registry, ownership manifest, route registry, component map, service map and dependency map.
- Each module gets a README/spec that lists its exact files and direct dependencies.
- Shared code must be small, stable and explicitly labelled as SHARED.
- No giant universal backend file should contain unrelated business logic.
- No giant frontend page should contain all dashboard functionality.
- Each module exposes narrow interfaces/contracts.
- Claude must search the module registry first, not recursively inspect the entire codebase by default.
- If the registry is stale, Claude must update the registry only as part of the relevant change.

# 3. REQUIRED REPOSITORY GOVERNANCE FILES

/docs/MID.md                         ← this document
/docs/PROJECT_MAP.md                 ← module map
/docs/MODULE_REGISTRY.md             ← feature → module → files
/docs/DEPENDENCY_MAP.md              ← allowed dependencies
/docs/CHANGE_PROTOCOL.md             ← isolated-change rules
/docs/ARCHITECTURE.md                ← approved architecture
/docs/SECURITY.md
/docs/TESTING.md
/docs/DECISIONS.md                   ← architecture decisions

Each module:
  /module-name/MODULE.md
  /module-name/OWNERSHIP.md
  /module-name/TESTS.md
  /module-name/CHANGELOG.md


# 4. MODULE OWNERSHIP CONTRACT

MODULE_ID
MODULE_NAME
PURPOSE
OWNER_PATHS
OWNED_ROUTES
OWNED_COMPONENTS
OWNED_SERVICES
OWNED_TABLES
OWNED_PROMPTS
ALLOWED_DEPENDENCIES
FORBIDDEN_DEPENDENCIES
PUBLIC_INTERFACES
FEATURE_FLAGS
TEST_COMMANDS
ACCEPTANCE_CRITERIA
DO_NOT_TOUCH

A file must have one clear owner wherever practical. Shared utilities are exceptions and must be explicitly registered as SHARED.

# 5. CLAUDE CHANGE REQUEST PROTOCOL — NON-NEGOTIABLE

When the user asks for a change:

STEP 1 — CLASSIFY
Identify the requested MODULE_ID.

STEP 2 — SCOPE
Read:
- MODULE.md
- OWNERSHIP.md
- relevant component/service
- direct dependency files only

STEP 3 — PLAN
Before editing, produce a SHORT scope plan:
- target module
- files likely to change
- why each file is needed
- files explicitly not to change

STEP 4 — IMPLEMENT
Make the smallest possible change.

STEP 5 — VERIFY
Run module-specific tests/checks.
Run only necessary cross-module regression tests.

STEP 6 — REPORT
Return:
- changed files
- unchanged protected areas
- tests
- any dependency change
- any migration
- any risk

STEP 7 — STOP
Do not continue improving unrelated code.
Do not refactor.
Do not redesign.
Do not 'clean up' unrelated files.


# 6. CROSS-MODULE CHANGE GATE

If a requested change genuinely requires another module, Claude must not silently expand scope.
CROSS-MODULE REQUEST

Target:
PXX / MXX

Required dependency:
PYY / MYY

Reason:
...

Exact interface/dependency:
...

Files that must change:
...

Risk:
LOW / MEDIUM / HIGH

Approval:
REQUIRED

Until approval:
DO NOT MODIFY THE DEPENDENT MODULE.

If the dependency is a stable existing interface, prefer adapting the target module to the interface instead of changing the shared module.

# 7. PROTECTED BEHAVIOUR RULE

- Approved modules are treated as frozen unless the change request explicitly targets them.
- A change request must not alter unrelated UI, API endpoints, database tables, authentication, execution permissions, prompts, or business rules.
- No mass formatting, renaming, lint-only cleanup or dependency upgrades during feature changes.
- No full rebuild/rewrite because one component needs a modification.
- No deleting working code merely because another implementation is easier.
- No automatic migration of unrelated data.
- No production deployment merely because a local change was completed.

# 8. PRODUCT GOAL

Build a specialised AI Google Ads/PPC command centre for an Australian chauffeur business with approximately 7–8 service/location websites and one or more Google Ads accounts. The system must understand websites, campaigns, keywords, search terms, ads, conversion funnels, bookings and public competitor information.
Business objective:
Qualified chauffeur bookings + revenue

Core loop:
CONNECT
→ INGEST
→ AUDIT
→ RESEARCH
→ DIAGNOSE
→ RECOMMEND
→ HUMAN APPROVAL
→ EXECUTE
→ MONITOR
→ LEARN


# 9. REQUIRED HIGH-LEVEL ARCHITECTURE

Frontend:
Next.js + TypeScript

Backend:
FastAPI/Python (or approved equivalent)

Database:
PostgreSQL

Jobs:
Redis + scheduler/worker

AI:
Claude API

Advertising:
Google Ads API

Analytics:
GA4

Organic/search context:
Google Search Console

Website:
Crawler/parser

Competitor:
Public web/SERP research adapter

Authentication:
Google OAuth 2.0

Execution:
Approval-gated Google Ads mutation service


# 10. MODULE REGISTRY — MASTER

P00 — Foundation & Governance
P01 — Dashboard Shell
P02 — Authentication & User Access
P03 — Website Intelligence
P04 — Google Ads Connection
P05 — Google Ads Data Sync & Warehouse
P06 — Analytics & Conversion Data
P07 — PPC Audit Engine
P08 — Keyword & Search-Term Intelligence
P09 — Ad & Creative Intelligence
P10 — Landing Page & CRO Intelligence
P11 — Competitor Intelligence
P12 — Budget / Bid / Geo / Device / Time Intelligence
P13 — Booking Funnel & Revenue Attribution
P14 — AI Recommendation Engine
P15 — AI Campaign Builder
P16 — Approval Center
P17 — Google Ads Execution
P18 — Monitoring & Alerts
P19 — Reports & Exports
P20 — Experiments
P21 — Business Memory & Rules
P22 — Security / Audit / Rollback
P23 — Testing & QA
P24 — Production Hardening

# 11. PHASE SPECIFICATIONS


## P00 — Foundation & Governance

- Create repository structure and module boundaries.
- Create MID, project map, module registry and dependency map.
- Create environment configuration and secret handling.
- Create database migration framework.
- Create stable API/service conventions.
- Create feature flags.
- Create logging/error conventions.
- Create module-level test conventions.

## P01 — Dashboard Shell

- Create global layout, navigation and module routes.
- Website/account selector.
- Global status/alerts.
- Use mock data until data modules are connected.
- Do not put business logic for other modules into the shell.

## P02 — Authentication & User Access

- Google OAuth.
- Application users and roles.
- Secure server-side credentials.
- Read/recommend/execute permissions.
- Execution permission disabled by default.

## P03 — Website Intelligence

- Website onboarding.
- Sitemap/robots-aware crawling.
- Page extraction.
- Service/location detection.
- Titles, headings, content, CTAs, forms, contact signals, schema and internal links.
- Landing-page relevance records.
- Crawl history.

## P04 — Google Ads Connection

- Google OAuth/API connection.
- Manager/customer account selection.
- Read-only discovery and health check.
- Secure credential handling.
- Connection status.

## P05 — Google Ads Data Sync & Warehouse

- Campaigns.
- Ad groups.
- Keywords.
- Search terms.
- Ads/assets.
- Metrics.
- Historical snapshots.
- Incremental sync.
- Sync health/error logs.

## P06 — Analytics & Conversion Data

- GA4 integration.
- Conversion event mapping.
- Calls/forms/quotes/bookings where available.
- CRM/booking adapter interface.
- Offline conversion workflow.
- Distinguish observed, attributed and confirmed values.

## P07 — PPC Audit Engine

- Account health.
- Campaign structure.
- Ad groups.
- Keywords.
- Search terms.
- Ads/assets.
- Conversion tracking.
- Landing page relevance.
- Budget/bid checks.
- Evidence-backed issue generation.

## P08 — Keyword & Search-Term Intelligence

- Keyword research.
- Intent classification.
- Keyword expansion.
- Duplicate/overlap detection.
- Negative keyword candidates.
- Search-term analysis.
- Business-value classification.
- Approval required for live keyword mutations.

## P09 — Ad & Creative Intelligence

- Existing ad analysis.
- RSA copy generation.
- Messaging variants.
- Performance comparison.
- Claim validation.
- Policy/safety checks.
- Draft first; no automatic launch.

## P10 — Landing Page & CRO Intelligence

- Keyword/ad/page intent matching.
- CTA analysis.
- Booking form analysis.
- Trust signals.
- Mobile UX signals.
- Page speed/technical observations.
- Generate website implementation briefs.

## P11 — Competitor Intelligence

- Public competitor website research.
- Public SERP observations.
- Service/location coverage.
- Messaging.
- Landing-page themes.
- Content gaps.
- Clearly separate observations from AI interpretation.
- Never claim private competitor Ads data.

## P12 — Budget / Bid / Geo / Device / Time Intelligence

- Budget utilisation.
- Spend anomalies.
- Geo performance.
- Device performance.
- Day/time performance.
- Bid strategy observations.
- Recommendations only during initial implementation.

## P13 — Booking Funnel & Revenue Attribution

- Click → Lead → Quote → Booking → Revenue model.
- Available attribution links.
- Booking quality analysis.
- Revenue-aware campaign/keyword analysis.
- Funnel bottleneck detection.

## P14 — AI Recommendation Engine

- Standard recommendation schema.
- Evidence.
- Reasoning.
- Confidence.
- Risk.
- Expected impact.
- Priority.
- Approval state.
- Observation vs inference separation.

## P15 — AI Campaign Builder

- Goal/service/location input.
- Campaign structure.
- Ad groups.
- Keywords.
- Negative candidates.
- RSA ads.
- Assets.
- Landing-page recommendation.
- Launch checklist.
- Draft/paused output.

## P16 — Approval Center

- Review recommendations.
- Approve/reject/modify.
- Before/after values.
- Evidence.
- Risk level.
- Approver and timestamp.
- High-impact confirmation.

## P17 — Google Ads Execution

- Allowlisted mutation types.
- Validation.
- Approved changes only.
- API execution.
- Execution result.
- Post-change sync.
- Global execution kill switch.

## P18 — Monitoring & Alerts

- Scheduled checks.
- Spend spikes.
- Conversion drops.
- CPC changes.
- Tracking failures.
- Search-term shifts.
- Change-impact monitoring.

## P19 — Reports & Exports

- Daily.
- Weekly.
- Monthly.
- Website-level.
- Account-level.
- Campaign-level.
- Bookings/revenue.
- Recommendations/actions.
- CSV/PDF export where required.

## P20 — Experiments

- Hypothesis.
- Control/variant.
- Primary/secondary metrics.
- Dates.
- Approval.
- Results and limitations.

## P21 — Business Memory & Rules

- Services.
- Locations.
- Target customer types.
- Excluded intent.
- Business priorities.
- Operational constraints.
- Versioned editable rules.

## P22 — Security / Audit / Rollback

- Secret security.
- Permission separation.
- Action log.
- Before/after values.
- Execution kill switch.
- Rollback/compensation procedures.

## P23 — Testing & QA

- Unit tests.
- Integration tests.
- API mocks.
- Fixture-based AI tests.
- Approval tests.
- Isolation tests.
- Regression tests.

## P24 — Production Hardening

- Deployment.
- Backups.
- Monitoring.
- Retries.
- Rate limits.
- API quota handling.
- Security review.
- Smoke tests.
- Recovery documentation.

# 12. MODULE ISOLATION TEST — MANDATORY

The project is not considered correctly modular until this test passes.
ISOLATION TEST

Given:
P08 Keyword Intelligence is already approved.

Request:
'Add a confidence filter to the negative keyword review table.'

Expected:
- Claude identifies P08.
- Claude opens P08 MODULE.md.
- Claude locates the negative-keyword UI/data path.
- Claude changes only the minimum required files.
- P09, P10, P15, P17, authentication and unrelated shared components remain untouched.
- P08 tests pass.
- No production deployment occurs automatically.

If unrelated modules are changed:
FAIL THE TASK.
REVERT UNRELATED CHANGES.
REASSESS SCOPE.


# 13. SHARED CODE RULES

- Shared code must not become a dumping ground.
- Every shared module must have a documented owner and public interface.
- Changing shared code is automatically considered a cross-module change.
- If a feature can be implemented locally without touching shared code, prefer the local implementation.
- Do not move code between modules merely for aesthetics.

# 14. DATABASE ISOLATION

- Each module should own its tables or table areas where practical.
- Do not alter unrelated schemas for convenience.
- All migrations must identify the owning module.
- Destructive migrations require explicit approval.
- Existing production data must never be dropped as part of ordinary feature work.
- Schema changes must include migration and rollback/recovery notes.

# 15. API ISOLATION

- Routes belong to modules.
- Use service interfaces rather than importing internal implementation details across modules.
- Do not change an existing API response contract for an unrelated feature.
- Breaking changes require a versioned migration plan.
- External API adapters must be isolated behind internal interfaces.

# 16. AI SAFETY & GOOGLE ADS EXECUTION

LEVEL 0 — READ ONLY
Audit, reporting, analysis.

LEVEL 1 — DRAFT
Keywords, ads, campaign plans, recommendations.

LEVEL 2 — APPROVAL REQUIRED
Keyword changes, negative keywords, ad changes, campaign creation, budget/bid changes.

LEVEL 3 — HIGH-IMPACT APPROVAL
Major budget changes, bid strategy changes, broad structural changes.

LEVEL 4 — AUTOMATION
Disabled initially. Enable only for explicitly allowlisted low-risk operations.

- No live mutation during P00–P16.
- P17 must remain behind an execution feature flag and kill switch.
- Every mutation requires a stored approval record.
- Default new campaigns to draft/paused.
- Never claim that an AI forecast guarantees bookings.

# 17. REQUIRED DATA MODEL CONCEPTS

Core:
users
roles
websites
business_rules
ads_accounts
connections

Ads:
campaigns
ad_groups
keywords
search_terms
ads
ad_assets
metrics_snapshots

Website:
pages
crawl_runs
page_signals
landing_page_mappings

Conversion:
conversion_events
leads
quotes
bookings
revenue_records
attribution_records

AI:
recommendations
ai_runs
ai_evidence
campaign_drafts
experiments

Governance:
approvals
executions
audit_logs
feature_flags
sync_runs
alerts


# 18. STANDARD AI RECOMMENDATION CONTRACT

{
  id,
  module_id,
  website_id,
  ads_account_id,
  entity_type,
  entity_id,
  severity,
  title,
  observation,
  evidence[],
  reasoning,
  proposed_action,
  expected_impact,
  confidence,
  risk,
  assumptions[],
  requires_approval,
  status,
  created_at,
  approved_at,
  executed_at,
  execution_result
}

# 19. REQUIRED DASHBOARD SECTIONS

- Overview
- Websites
- Ads Accounts
- Campaigns
- Ad Groups
- Keywords
- Search Terms
- Ads & Assets
- Conversions
- Bookings / Revenue
- Landing Pages
- Competitors
- AI Recommendations
- Campaign Builder
- Approval Center
- Monitoring & Alerts
- Reports
- Experiments
- Business Rules
- Audit Log
- Settings

# 20. FULL USER WORKFLOW

1. Add website.
2. Define website purpose/service/location.
3. Connect Google Ads account.
4. Connect GA4 / conversion sources.
5. Run website crawl.
6. Import historical Ads data.
7. Run initial audit.
8. Run keyword/search-term analysis.
9. Run conversion/funnel analysis.
10. Run competitor research.
11. Generate master report.
12. Review recommendations.
13. Build a campaign draft.
14. Review ads/keywords/landing page.
15. Approve selected actions.
16. Execute through Google Ads API.
17. Monitor performance.
18. Attribute leads/bookings/revenue.
19. Generate recurring reports.
20. Repeat optimisation cycle.


# 21. FIRST BUILD SEQUENCE

1. P00 → P01 → P02 → P04 → P05 → P03 → P06
1. P07 → P08 → P09 → P10 → P11 → P12 → P13
1. P14 → P15 → P16 → P17
1. P18 → P19 → P20 → P21 → P22 → P23 → P24

# 22. PHASE ACCEPTANCE GATE

PHASE ACCEPTANCE

Phase:
Module:

[ ] Feature works
[ ] UI reviewed
[ ] Data flow reviewed
[ ] Error states handled
[ ] Security checked
[ ] Module tests passed
[ ] Regression tests passed where required
[ ] No unrelated files changed
[ ] No unrelated behaviour changed
[ ] Documentation updated
[ ] User reviewed and approved

ONLY THEN:
Mark module APPROVED/FROZEN.
Proceed to next phase.


# 23. CHANGE REQUEST TEMPLATE FOR FUTURE USE

CHANGE REQUEST

Project: AI Google Ads Specialist

Phase ID:
Module ID:
Section:
Current behaviour:
Required change:
Reason:
Expected behaviour:
Must NOT change:
Acceptance criteria:

Claude:
- identify module
- inspect module manifest
- inspect direct dependencies only
- create minimal change plan
- implement
- test
- report changed files
- report untouched protected modules
- stop


# 24. CLAUDE CODE MASTER SYSTEM INSTRUCTION

You are the implementation and maintenance engineer for the AI Google Ads Specialist project.

AUTHORITATIVE DOCUMENT:
Master Implementation Document (MID)

PRIMARY OBJECTIVE:
Build the complete functional product defined by the MID.

MAINTENANCE OBJECTIVE:
After a module is approved, preserve it. When the user requests a change, modify only the requested module and the minimum direct dependencies required.

MANDATORY RULES:

1. Treat the MID as the source of truth.
2. Treat MODULE_ID as the primary scope boundary.
3. Start every task by classifying the request into a MODULE_ID.
4. Read that module's MODULE.md and OWNERSHIP.md first.
5. Use MODULE_REGISTRY.md to locate files.
6. Do not recursively read the entire repository for a local change.
7. Read only direct dependencies required to understand or implement the change.
8. Do not perform unrelated refactoring.
9. Do not redesign unrelated UI.
10. Do not rename unrelated files/components.
11. Do not change unrelated database schemas.
12. Do not change unrelated API contracts.
13. Do not modify authentication/security/execution settings unless the request targets them.
14. Do not change Google Ads live execution behaviour unless the request explicitly targets execution and the required approval gate is satisfied.
15. Do not delete working functionality.
16. Do not install dependencies unless necessary.
17. Do not deploy automatically after a local change.
18. If a cross-module change is genuinely required, stop and produce a dependency notice before editing the other module.
19. Prefer the smallest safe patch.
20. Preserve existing approved behaviour.
21. After implementation, run targeted tests.
22. Report exact changed files.
23. Report exact protected areas not changed.
24. Report any migration/API/dependency impact.
25. Stop after the requested change is complete.

INITIAL BUILD MODE:
When the user says 'build the project from the MID':
- implement phases in the approved build order;
- complete one phase/module;
- test it;
- document it;
- do not skip the acceptance gate;
- do not silently jump into future modules;
- do not enable live Google Ads execution early.

CHANGE MODE:
When the user says 'change PXX/MXX':
- treat that module as the only intended scope;
- locate its files through the registry;
- make the smallest change;
- run module tests;
- do not touch unrelated modules.

FINAL RESPONSE FOR EVERY CHANGE:
Phase:
Module:
Requested change:
Files inspected:
Files changed:
Files not changed:
Tests:
Dependencies changed:
Migration:
Risk:
Acceptance status:


# 25. FINAL SUCCESS CRITERIA

- The full agent is functional across the approved phases.
- Each major feature has a clear module boundary.
- Claude can locate features from the module registry.
- Local changes do not require broad repository refactoring.
- Unrelated modules remain stable.
- Google Ads execution is approval-gated.
- Every live action has an audit trail.
- Website, Ads, conversion and booking data can be analysed together where integrations exist.
- AI recommendations explain evidence and reasoning.
- Reports show business outcomes, not only advertising metrics.
- The user can approve each module before moving forward.
- Later change requests can be issued using Phase + Module + Section.

# 26. FINAL INSTRUCTION TO CLAUDE

Do not interpret this document as permission to build a giant monolithic application. The opposite is required. Build a modular system whose boundaries are explicit enough that a future developer or AI agent can change one feature without unnecessarily loading, rewriting or redeploying unrelated features.
The success of this project is not only that the first version works. Success also means that Version 2, Version 3 and future maintenance can be performed safely, locally and predictably.