# Phase 4A working application report

A working passenger and administrator application is delivered and running locally at http://127.0.0.1:8000. This is a verified local application delivery, not a claim that earlier backend phases or the overall RTC system are complete or production-ready. No speech, cloud inference, payments or booking integration was added.

[Setup and offline deployment](APP_SETUP.md) · [Requirement coverage](phase4a-coverage.json) · [Original request](phase4a-request.md)

## Implemented pages

- Smart enquiry: real conversation API, owner-bound sessions, contextual follow-ups, corrections, numbered service/itinerary selection, rich bus/journey cards, timestamped messages, request feedback/retry, current stand/operator and server reset.
- Find a bus: station/alias autocomplete and exact ID selection, direct-service search with time/category/operator/AC/sleeper/fare/verified-seat filters.
- Journey planner: direct/connecting results with actual legs, named transfer stations, waits, fares, deadlines and backend ranking. Unknown total fare remains unknown; comparison uses backend facts.
- Service detail: ordered variant-aware stop timeline, boarding/alighting permissions, scheduled stop dates/times, actual local operator/category/amenities/fare/platform/status data. Cancelled dated services show cancellation even when no journey is searchable.
- Protected admin overview: actual operators/stations/services counts and a local Recharts inventory chart. Management sections cover operators, stations, depots, categories, routes, services, calendars, fare stages/rules, platforms, exceptions, imports, diagnostics and status.
- CRUD tables: existing backend-supported resources use typed schema-driven add/edit forms, foreign-key choices from local records, validation feedback and confirmed soft deletion. Sorting/filtering/column visibility use TanStack Table; pagination uses existing backend limits.
- Read-only management: depots, calendars, fare rules, platform assignments and import batches have truthful protected catalog views. No unsupported editor is faked.
- CSV: existing atomic import endpoint, dry-run default, real row-level backend report, file/content entry, size checks and explicit commit confirmation.
- Developer diagnostics: guarded stateless NLP interpretation; actual original/debug/entities/context/query/results/latency data. Rule scores are explicitly uncalibrated. System status distinguishes deterministic fallback from a trained/approved classifier.

## APIs reused and small adapters

Reused conversation/message, conversation/reset, owned conversation context, station search/resolve, journeys/search, admin CRUD/import and nlp/health. The frontend never computes routes, fares, intent matches or operational statuses itself.

Added /api/v1/app/bootstrap (actual DB inventory/reference metadata), /app/services/{id} (combines existing enquiry/fare/status engines with reference data), protected /admin/ui/metadata (existing Pydantic schemas and FK resource references), /admin/ui/catalog/{resource} (read-only missing admin domains) and /admin/ui/diagnostics (existing stateless interpretation with debug). These are adapters, not duplicate tables or business engines. Existing migrations and model artifacts were not changed.

Debug=true on public interpretation/conversation endpoints now requires an Authorization Bearer administrator token. This intentionally tightens the old opt-in public debug behavior to meet developer-only diagnostics requirements; the existing regression now checks both denial and authorized success. Ordinary passenger requests retain their contract. Empty operator selection can explicitly clear an inherited operator while omitted/None preserves compatibility.

Compiled local assets are served by FastAPI when frontend/dist exists. SPA paths fall back to index; unknown /api paths remain JSON404, including Windows path normalization. Development Vite proxies /api on the same local origin.

## Actual verification

- Backend: **1388 passed**, one Starlette/httpx deprecation warning,112.58seconds. Log: models/benchmarks/phase4a-verified-backend-pytest.txt. New adapter/security regressions cover real DB counts, authorization, guarded diagnostics, actual service details/cancellation, production deep links, API404 and request limits.
- Production Playwright: **19 passed**, zero failures, zero skipped. JSON: [phase4a-playwright.json](phase4a-playwright.json). Tested compiled frontend through real FastAPI on8020 with an isolated SQLite DEMO database, not mocked successful API replies.
- Browser scenarios: offline app load; real enquiry/result; fare follow-up; destination correction; server reset; selected service verified via owned backend context; null fare rendering; DEMO labels; actual stop details; strict-filter no results; DB autocomplete; unauthorized admin GET/POST denial; mobile layout; Enter/Shift+Enter; atomic CSV dry run; authenticated create/edit/deactivate verified against DB; actual diagnostics; failed-network retry followed by real API; selected stand/session consistency after reload.
- Frontend ESLint/hooks review passed with no warnings. TypeScript and production Vite build passed. Passenger bundle369.33kB (116.15kB gzip); lazy admin bundle470.44kB (135.63kB gzip); CSS30.13kB. Admin chart/table/dialog code stays out of the initial passenger route.
- Ruff passed across backend/scripts/training; Mypy passed for54 source files. npm audit and runtime-only audit: zero reported vulnerabilities. A scoped minimatch override patches the development lint dependency; exact dependencies are locked.
- Browser verification skill/agent-browser was used on the running development and production app. Desktop/mobile chat and protected admin overview were visually inspected. No browser errors observed. Screenshots: phase4a-desktop.png, phase4a-chat-results.png, phase4a-mobile.png, phase4a-admin.png.
- Both Windows launcher modes executed successfully, migrations ran against the existing DB, and production startup health returned successfully. Production mode is left running on8000.
- Against the existing, unmodified timetable database, selecting Tirumala then asking "Next bus to Nellore?" returned recorded DEMO24/DEMO66/DEMO3/DEMO45/DEMO87 services and INR100 fares. "What is the fare?" retained the selected service. These were actual local DB responses, not the additional isolated browser-test fixtures.

## Offline and security scope

Every browser request in automated tests is restricted to loopback; the test backend blocks external socket connections. Production assets use only local JS/CSS, local icons, system fonts and same-origin APIs. No CDN, external inference, analytics or image calls exist. This is application-level offline verification; OS firewall isolation and PostgreSQL browser/integration runs were not executed.

Admin credentials are entered at runtime and stay in memory, never bundled. Passenger session capabilities and conversation data use tab-scoped sessionStorage. The backend checks owner tokens and admin tokens. Safe React text is used throughout; no arbitrary HTML injection. Local limits are300 mutating requests/minute per IP and passenger/admin bucket, plus import body checks and existing CSV bounds. These are single-process protections, not distributed gateway controls or an enterprise identity system. Default binding is127.0.0.1.

## Known limitations

- Existing Phase1–3B engine coverage/accuracy/routing/model-readiness limitations remain. The app exposes them truthfully rather than inventing results. Unsupported intents, missing fare/platform/inventory/GPS and search-resource exhaustion remain backend outcomes.
- Standard demo data does not serve every origin/destination pair. Select an actual boarding station and date; missing routes are not populated automatically. The isolated test server adds clearly fictional DEMO fixture services only to its temporary DB, never rtc.db.
- Table sorting/filtering is local to the current25-row page, not a whole-database search. Foreign-key selects show up to100 records. Large master-data administration needs server-wide search/sort/reference pagination improvements.
- Some management domains remain read-only because compatible mutations are absent. This is explicitly allowed by the request; no duplicate CRUD implementation was added.
- Import recency is unknown because existing import batches lack timestamps. Counts and model/fallback status are actual backend values, not fabricated daily metrics.
- Times are displayed in Asia/Kolkata for this RTC deployment. Search timestamps resolve the selected source timezone, but broader multi-timezone display conventions need further work. Scheduled route details do not imply live tracking or a booking guarantee.
- Single local administrator token; no granular roles, cloud identity, shared-account isolation or production multi-worker rate limit. The frontend is not a PWA/service-worker cache: a running local backend is required.
- Chromium desktop/mobile-emulation tests and visual inspection passed; exhaustive tablet/device/browser/screen-reader testing and formal accessibility certification are not claimed.

## Files and exact startup

Frontend source: frontend/src/{App,api,main}, pages/{ChatPage,PlannerPage,ServicePage,AdminPage}, components/{BusCard,JourneyCard,StationPicker,AdminTable,ui}, local styles and Vite/TypeScript/ESLint/Playwright configuration. Backend adapters/security: frontend_api.py, frontend_security.py; compatible changes in main.py, enquiry.py and nlp/pipeline.py. Tests: frontend/tests/app.spec.ts, backend/tests/test_frontend_api.py, updated protected-debug regression. Fixtures: scripts/serve_ui_test.py. Launcher: start-rtc.ps1. README, setup, coverage and report updated.

Run from repository root: **.\start-rtc.ps1** for development, or **.\start-rtc.ps1 -Production** for compiled offline assets. The launcher prints local URLs and a temporary administrator token unless RTC_ADMIN_TOKEN is already configured. It downloads nothing at runtime.
