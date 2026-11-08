# Phase 5A completion report

Date: 2026-11-08. **PHASE 5A COMPLETE** for the bounded local data-management workflow specified here. This does not certify an official APSRTC dataset, multi-user deployment capacity, or the separately unapproved NLP model. No voice, Telugu AI, cloud dependency or model training was added.

## Implemented behavior

The existing backend and administration app now maintain operational master data through operator-scoped drafts, validation, independent approval and atomic publication. CSV/XLSX upload, explicit column mapping, duplicate detection, row errors, before/after previews, schema-generated templates, scoped CSV exports, persistent import history, versioned audit and guarded rollback are working. Existing CRUD routes are reused and stage writes by default. An explicit root-only demo/test flag preserves legacy direct-write compatibility.

Route editing supports ordered stops, cumulative distance, separate arrival/departure elapsed offsets, boarding/alighting permissions, direction, route copies, selected-stop variants and variant copies. Service/timetable editing supports depot/type metadata, calendars, stop-specific schedules, bulk time shifts, service copies and actual calendar previews. Fares support dated Decimal rules, category/operator scope, surcharges, exact trip overrides, draft previews, concessions and history. Platform updates and all eight requested exception types feed the existing enquiry engines after publication.

Named local editor/approver capabilities use existing user/role tables. Independent review and operator isolation are enforced in the backend. Shared definitions require global authorization. Demo provenance cannot be relabelled official. Overview and quality metrics query actual scoped stored records; source issues can be resolved through published changes. No operational dataset has been invented.

The requirement-by-requirement gap matrix is in **PHASE_5A_AUDIT.md**; deployment and usage are in **PHASE_5A_SETUP.md**; the unmodified request is **phase5a-request.md**.

## Actual verification

- Full backend regression: **1,566 passed, zero failures**, 317.79 seconds. PostgreSQL was enabled and its cases executed, not skipped. Raw log: `models/benchmarks/phase5a-backend-final.txt`; JUnit: `docs/phase5a-backend.xml`.
- Final data-management regression after the final validation-message and APSRTC configuration checks: **84 passed, zero failures or skips**, 86.33 seconds: **42 SQLite and 42 PostgreSQL cases**. This overlaps the full regression; counts must not be added. Raw log: `models/benchmarks/phase5a-database-tests.txt`; JUnit: `phase5a-database.xml`.
- Maximum-size import test: **two passed**, 10,000 validated rows on SQLite and PostgreSQL, 10,001-row rejection and no live rows written during validation. Per-case durations including fixture/validation: 15.762 and 31.105 seconds. Raw log/JUnit: `models/benchmarks/phase5a-large-import.txt`, `phase5a-large-import.xml`. Normal regression uses 500 rows; maximum-size reproduction sets `RTC_IMPORT_TEST_ROWS=10000`.
- Final production-bundle browser integration: **140 passed, zero failures/skips/flaky tests**, 138.19 seconds. Both real local test servers were used: explicit compatibility mode on 8020 and strict publication on 8021. Includes upload/map/validate/independent approval/publish/passenger alias recognition/rollback, XLSX, templates, strict CRUD staging, permissions, route/variant/timetable drafts and existing passenger flows. Evidence: `phase5a-playwright.json`, `models/benchmarks/phase5a-browser-final.txt`.
- Ruff over `backend scripts training`: passed. Configured Mypy over `backend/app`: passed, 53 files. Frontend ESLint, TypeScript and Vite production build: passed.
- SQLite and PostgreSQL incremental upgrade verification to **0014**: passed, including existing operator/import-batch preservation and the fare-rule check constraint. Evidence: `phase5a-migration-verification.json`.
- Actual `rtc.db` upgrade: all original values across **71 tables and 1,112 rows** matched the private pre-upgrade backup; SQLite integrity was `ok`, foreign-key errors were empty. Evidence: `phase5a-live-migration.json`. Subsequent explicit live smoke added audit/history and a rolled-back inactive DEMO alias; it did not replace original seed data.
- Live application on `127.0.0.1:8000`: passenger/admin pages loaded without browser errors. A real CSV alias upload remained hidden as a draft, was independently approved/published, resolved in a passenger conversation, and disappeared after guarded rollback. The temporary reviewer was revoked. Evidence: `phase5a-live-smoke.json`, `phase5a-passenger.png`, `phase5a-import-center.png`. Script: `scripts/verify_data_management_smoke.py`.
- Offline test servers import/start the application after external socket blocking; browser tests reject non-local requests. Imports, validation, publication and enquiries completed under those restrictions. This is application-level outbound blocking, not an OS-firewall or physical-air-gap certification.

The backend emits one existing Starlette/httpx TestClient deprecation warning. It does not indicate a test failure. An initial browser run exposed an optional-reference form bug; it was fixed, and final runs above passed. Two test servers initially shared a Windows rotating log file; each now uses its own log, and the final browser run has no logging-error tracebacks. Initial reports are retained separately rather than presented as passing final evidence.

## PostgreSQL evidence

Tests ran against local **PostgreSQL 17.11** on loopback port 55435, database `rtc_phase5a_tests`, using isolated random schemas which were dropped after each case. The downloaded [official EDB Windows binary package](https://www.enterprisedb.com/download-postgresql-binaries) was kept outside Git in `.tools/postgres/`. Its locally computed SHA-256 was `80379b2c04d51c30225532e0ae04509899141e9957ed096fe749d7fd9df8f82f`; this is a local integrity record, not a claim of independent publisher-checksum verification. The isolated test cluster used local trust authentication and is stopped after verification; it is not a production authentication configuration or installed Windows service.

SQLite uses BEGIN IMMEDIATE to serialize write actions and explicit transaction starts before validation savepoints. PostgreSQL uses normal transactions/savepoints and an advisory transaction lock to serialize publication and rollback. Both reject a stale competing publication rather than lose updates. High-concurrency throughput is not certified.

## Measured local passenger performance

Five final browser samples used the isolated seeded SQLite DEMO database and the actual configured deterministic fallback. Median / slowest observed times: page-ready **138.36 / 152.69 ms**, visible chat answer **207.30 / 224.73 ms**, autocomplete including debounce **269.28 / 276.52 ms**, backend NLP total **59.36 / 65.71 ms**, planner HTTP **69.82 / 77.58 ms**. These are local samples under the test workload, not production SLAs. Raw timing and phase breakdown: `phase5a-performance.json`. The ten-step passenger acceptance context is in `phase5a-passenger-acceptance.json`.

## Schema and files

No new tables were introduced. Original migrations 0001–0010 remain intact. Incremental **0011** extends existing import batches/audit logs with workflow, checksum, scope, actors, timestamps, revision, snapshots and changed fields. **0012** adds service depot/type, typed exception details/reason and effective fare-rule/surcharge fields. **0013** explicitly restores/names a fare-rule check omitted by SQLite table rebuilding. **0014** adds route direction and nullable separate route-stop arrival/departure offsets. Legacy defaults preserve existing published records and legacy stop offsets.

New backend modules: `data_access.py`, `data_resources.py`, `import_files.py`, `publication.py`, `data_api.py`. Existing modules extended: `main.py`, `catalog.py`, `domain.py`, `records.py`, `imports.py`, `timetable.py`, `fares.py`, `enquiry.py`, `engine.py`, `frontend_api.py`, `data_quality.py`, and Alembic environment. New migration files are under `backend/alembic/versions/0011*` through `0014*`.

New frontend pages: ImportCenter, ManagementScope, ManagementOverview, AccessManagement, AuditHistory, RouteEditor, TimetableEditor and FarePreview. Existing AdminPage, AdminTable, api client, DataQualityPage and styles were extended. Test additions: `backend/tests/test_data_management.py`, `frontend/tests/data-management.spec.ts`; isolated server/test configuration and report filenames were updated. Scripts: `verify_data_migrations.py`, `verify_data_management_smoke.py`. Dependency: local `openpyxl` (tested 3.1.5); weights, private backups and local PostgreSQL binaries/cluster are ignored by Git.

The workspace also contains prior phase work and separate model/evaluation work. Those files were not bundled into a commit or pushed by this task. Model approvals and speech artifacts were preserved.

## Known limits and unfinished deployment inputs

- No authoritative APSRTC schedules/fares/platforms/vehicles/source files were supplied. The database remains clearly labelled demonstration data. APSRTC onboarding stages requested operator/category names only and requires independent approval. Operational data onboarding remains a deployment input, not fabricated completed work.
- Import bounds: 10 MB, 10,000 rows, one XLSX sheet, expanded archive maximum 40 MB/1,000 entries; first 100 changes in preview. Processing is synchronous. Larger imports must be split; no resumable background queue or full-replacement deletion mode is implemented.
- Legacy direct-import batches lack old snapshots and cannot be rolled back. Historical rejected rows cannot be reconstructed. New staged errors are persisted and audited. Rollback is refused if newer changes or foreign-key dependencies make it unsafe.
- Scope selectors show up to 100 operators/sources; editor service/route selectors initially show 100 records. Generic reference controls support server search. Deployments with larger editor option lists should use master search/export and explicit IDs/import bundles; full virtualized editor selectors are not implemented.
- All foreign keys are explicit local IDs. Imports do not resolve external operator/station codes through fuzzy matching. Templates contain fictional format values, not turnkey valid linked datasets.
- Existing dated-trip uniqueness is one trip per service/date. Multiple additional festival departures on one date require separately numbered services/calendars, not multiple trips sharing that key.
- Exception changes use service-local dates and validated elapsed/departure minutes. No external live data or GPS feed was added; verification/freshness still depends on actual local observations.
- Concession configuration/history is supported, but passenger eligibility is not inferred from an enquiry. No booking, payment or refund-system integration was added.
- API capability authentication is intended for this loopback/offline deployment. No remote identity provider, multi-process rate limiter, per-row encryption or multi-site synchronization was added. Production authentication/network policy is a deployment responsibility.
- The independent statistical intent model remains unapproved. Existing deterministic English enquiry behavior is preserved; this phase makes no model-quality or voice-readiness claim.

No substantial Phase 5A workflow requirement is left as a mockup or empty script. Operational source onboarding and the explicit deployment/scale limits above remain visible. Do not infer that Phase 5B or later phases were implemented.
