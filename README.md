# RTC offline backend — Phase 1

**PHASE 1 INCOMPLETE.** No Phase 2 work is included.

## Startup

Requires Python 3.12+. Install development/runtime dependencies with `pip install -r requirements.txt` during setup. Runtime code does not call external services.

```powershell
$env:PYTHONPATH='backend'
python -m alembic upgrade head
python -m app.seed
python -m app.demo
python -m uvicorn app.main:app --host 127.0.0.1
```

OpenAPI: http://127.0.0.1:8000/docs. Set DATABASE_URL to choose a local PostgreSQL database. PostgreSQL has NOT been tested here. No Docker, psql or PostgreSQL service was found through the environment checks performed.

## Implemented schema

The following 63 application tables exist (plus Alembic's version table). Presence does not mean every business rule or integration is complete.

audit_logs, booking_references, bus_service_categories, bus_stations, bus_type_aliases, cities, city_aliases, conversation_context, conversation_messages, conversation_sessions, data_import_batches, data_quality_issues, data_sources, depots, districts, enquiry_execution_logs, extra_services, fare_concession_eligibility, fare_concessions, fare_history, fare_rules, fare_stages, fare_tables, nlp_entity_aliases, nlp_entity_types, nlp_intents, nlp_response_templates, nlp_utterances, operational_alerts, operator_divisions, platform_assignments, reservation_channels, route_aliases, route_distance_data, route_stops, route_variant_stops, route_variants, routes, seat_availability_snapshots, service_calendar_exceptions, service_calendars, service_disruptions, service_stop_times, service_vehicles, services, states, station_aliases, station_bays, station_facilities, station_geography, transport_operators, trip_delay_events, trip_fare_overrides, trip_inventory, trip_status_history, trip_stop_times, trips, vehicle_amenities, vehicle_locations, vehicle_seat_layouts, vehicle_seats, vehicle_types, vehicles

Incremental revisions 0003–0006 expand the existing foundation. 0001 is unchanged. Revision 0006 reconciles missing tables; downgrade retains reconciled tables to preserve data. New migrations still depend on live metadata and must be frozen before schema evolution in a production release.

## Enquiries and APIs

The Enquiry service implements these twenty database-backed entry points:

- get_arrival_time
- get_available_bus_types
- get_bus_fare
- get_cheapest_services
- get_concessions
- get_connecting_services
- get_direct_services
- get_fastest_services
- get_first_bus
- get_journey_duration
- get_last_bus
- get_next_buses
- get_operator_services
- get_platform_assignment
- get_route_stops
- get_seat_availability
- get_service_details
- get_service_status
- get_services_via_stop
- get_station_facilities

GET /api/v1/enquiry/ supports next-bus, first-bus, last-bus, fare, bus-types, service, route, duration, arrival, platform, availability, status, cheapest, fastest, direct, connections, via, operator-services, concessions and facilities. First/last use an explicit boarding-local calendar day (midnight to next midnight). Connections support one transfer, 15-minute default minimum, 100 candidate stations and bounded leg/result counts.

GET reference resources: operators, stations, bus-types, services, routes. GET /api/v1/stations/search resolves matching names and aliases. Existing next-bus route is retained. Results preserve DEMO labels, scheduled versus estimated departure/arrival, unknown fares and unknown/stale inventory. No passenger concession eligibility is assumed.

Local master mutations use `Authorization: Bearer <RTC_ADMIN_TOKEN>`. Configure RTC_ADMIN_TOKEN in the process environment; no default administrator credential exists. POST creates, PUT replaces validated master fields and DELETE soft-deactivates. One local administrator role exists; multi-user role management is unfinished. These routes allow only explicitly registered master resources.

Example:

```
GET /api/v1/enquiry/next-bus?origin=Vijayawada&destination=Guntur&at=2026-11-08T00:00:00%2B05:30
GET /api/v1/enquiry/last-bus?origin=Vijayawada&destination=Guntur&day=2026-11-08
```

## Imports

POST /api/v1/admin/imports/{resource}?dry_run=true accepts text/csv and requires the administrator token. Supported resources:

states, districts, cities, operators, stations, bus-types, routes, stops, schedules, fares, calendar-exceptions

Headers are generated in data/import_templates by scripts/import_templates.py. Foreign references use database UUIDs. Each file validates schemas, references, natural keys and ordering; conflicts report row errors and roll back the file. Identical rows are counted as duplicates. Dry runs leave no imported records. Successful files retain digest/resource/count provenance. Maximum 2 MB / 10000 rows. Approved provider adapters are not yet implemented.

## Actual verification

- 14 SQLite unit/API integration tests passed, with one installed Starlette/HTTPX deprecation warning.
- Mypy passed for application modules.
- Ruff passed for application, tests and scripts; final repository check recorded separately in command output.
- Existing SQLite database migrated to head. Separate verification.db migrated, seeded and enriched successfully.
- SQLite integrity_check and foreign_key_check passed.
- Median next-bus latency: 14.59 ms over ten local runs with 100 demo services, after route candidate SQL filtering. This is a smoke benchmark, not a production performance guarantee.
- API tests exercise all twenty enquiry paths, local authentication and OpenAPI. An API test blocks socket.create_connection; exhaustive process-wide network isolation is not verified.
- PostgreSQL tests did not execute. No PostgreSQL compatibility claim is made.

```powershell
python -m pytest -q
python -m ruff check backend scripts
python -m mypy backend/app --ignore-missing-imports
$env:PYTHONPATH='backend'
python scripts/verify.py
```

## Known limitations and unfinished requirements

- PostgreSQL execution and a real HTTP server smoke test remain unverified.
- Models have incomplete timestamps/auditing, cascade policies, provenance links and cross-table integrity rules. Operational updates lack some required operator/service linkage. API CRUD is limited to import master resources.
- Route variants, service stop times, distance fare rules, inventory reservation metadata and some other tables are not fully integrated into enquiry calculations. Vehicle amenity filtering exists; richer classification comparisons remain incomplete.
- Seed enrichment supplies aliases, extra category references and 42 intent records, but lacks complete weekly/intermediate/calendar/operational/variant fixtures and multilingual utterances/templates. All schedules and fares are FICTIONAL DEMO data valid in 2026–2027.
- Typed request validation exists; responses and internal methods are not comprehensively Pydantic typed. A generic enquiry dispatcher does not document each enquiry separately in OpenAPI.
- Structured JSON logging, comprehensive audit writes, provider integration architecture, overlapping-calendar/fare validation, full effective-time operational status history and extensive adversarial import tests remain incomplete.
- Current schedule time construction uses the boarding station timezone; routes across different timezone regions need origin timezone binding. Delay propagation to arrival is an estimate rather than a verified destination observation. Circular route repeated-stop fare-stage identity needs strengthening.
- Full original acceptance criteria have not been met. Do not advance to Phase 2.

## Phase 1A schema continuation

Additive migrations 0007–0009 add eight domain tables and nullable compatibility fields across existing geography, stations, operators, categories, routes, services, trips, inventory, NLP and conversation models. Existing identifiers and canonical API column names are retained. SQLite batch migration dropped some unnamed legacy checks; revision 0009 restores missing checks. Fresh schema1a-verification.db migration, seed, enrichment and integrity verification were executed. Full Phase 1A acceptance remains INCOMPLETE: PostgreSQL schema tests have not run, several detailed fields and temporal/overlap constraints remain absent, nullable legacy backfills remain unfinished, and exact-name alternatives such as concession_schemes are not duplicated over existing fare_concessions. See docs/phase1a-compatibility.md for per-entity columns and gaps. No Phase 2 code was added.

## Phase 1B enquiry continuation — INCOMPLETE

Added RTCEnquiryEngine with Pydantic EnquiryRequest/SearchFilters/EnquiryResponse, StationResolver, RouteSearch, FareEngine, OperationalStatusEngine and TimetableEngine. Existing specialized endpoints and Enquiry service remain compatible. POST /api/v1/enquiry calls the new central engine; GET /api/v1/stations/resolve returns exact candidates, city station sets, ambiguity or bounded suggestions. The legacy specialized endpoints still call Enquiry directly; complete unification remains unfinished.

Central search combines known vehicle AC/sleeper/electric/accessibility attributes, category, operator, amenity, reservation policy, fare bounds and departure windows. Unknown properties do not satisfy requested filters. RouteSearch supports up to two transfers, calendar-aware legs, visited-station cycle prevention, transfer waits and bounded expansion. The search truncation is not yet surfaced through response warnings. Existing legacy connection endpoint still uses the older one-transfer search.

Example unified request:

```json
{"intent":"NEXT_BUS","origin":"Bezawada","destination":"Guntur","travel_date":"2026-11-08","filters":{"max_fare":"200.00"}}
```

Actual checks: 16 SQLite tests passed; Ruff passed across backend and scripts; Mypy passed across 20 application modules. One installed Starlette/HTTPX deprecation warning remains. PostgreSQL execution remains unverified.

Unfinished Phase 1B requirements: all 44 intents are not complete; ARRIVALS_AT_STATION, OPERATOR_CONTACT and LUGGAGE_RULES are not supported by the central dispatcher. AVAILABLE_BUS_TYPES, SERVICE_CATEGORY_COMPARISON, ARRIVAL_TIME, JOURNEY_DURATION and RESERVATION_SUPPORTED currently return filtered journey records rather than full intent-specific projections. FareEngine covers exact segment tariffs and trip overrides, not stage/distance calculations, surcharges or confirmed concessions; it is not yet integrated into every result path. Full seat-segment search filtering, configurable sort options, exhaustive ambiguity handling, calendar-origin timezone correctness, all operational status events, complete typed nested results, and 100/1000/10000-service benchmark reports remain incomplete. Two-transfer search and several newly added components require additional deterministic tests. No UI, AI training, voice processing or cloud runtime integration was added.

PHASE 1B INCOMPLETE. Original acceptance criteria have not been met.

## Phase 1D text conversation integration

PHASE 1D INCOMPLETE. New modules under backend/app/nlp implement Unicode normalization, script/language heuristics, configurable deterministic intent phrases, database station/category extraction, relative-date parsing, context persistence with 15-minute expiry, clarification, query orchestration through RTCEnquiryEngine, and short deterministic responses. No model downloads, training, UI or audio orchestration are introduced.

New endpoints: POST /api/v1/nlp/interpret (does not persist a session), POST /api/v1/conversation/message, POST /api/v1/conversation/reset, GET /api/v1/nlp/status and GET /api/v1/models/status. Session IDs are random UUIDs; a fresh request without a session ID creates separate context. Session ownership authentication and concurrent same-session serialization are not implemented. Reset currently accepts the same NLPRequest contract, so text is required.

The MuRIL adapter reports NOT_READY and never uses pretrained MLM outputs as intent classifications. Registry inspection exists; real classification-head loading, checksum enforcement, device management and timeout support are unfinished. The deterministic fallback works without model libraries.

Known substantial gaps: reviewed 20–30 examples per intent corpus is absent; 44 rule labels exist but many have only one English phrase and some target unsupported Phase 1B operations. Responses are not fully localized and templates are not yet read from nlp_response_templates. Entity extraction scans the active local lexicon and cannot safely resolve all ambiguous aliases/city-level spans, arbitrary spelling variants or unknown categories. Time parsing covers relative days and morning only; full clock, fare, passenger and service identifiers remain incomplete. Multi-intent execution is bounded to three tools but service/trip reuse and partial-result semantics require further work. No calibrated confidence or measured production accuracy is claimed. Full database-failure recovery, stale-result handling, retention deletion, context locking and complete offline OS isolation remain unverified. API classification errors can still surface as no results rather than the desired precise dialogue state. Phase 1A/1B/1C limitations remain.

The new clean-text tests comprise 100 rule/phrase/location combinations, multilingual/end-to-end checks, and 30 parameterized multi-turn destination/filter/date scenarios. They are synthetic regression fixtures, not a reviewed training corpus or evidence of ASR robustness. Final test counts are recorded in the implementation report. PostgreSQL tests have not run.

## Current scope: English first

Multilingual model integration is DEFERRED; all previous files are retained. See ENGLISH_SETUP.md for executed model/speech checks, terminal commands and blockers. Both requested English Vosk models downloaded and transcribed the official example recording locally. Windows local TTS synthesized a WAV. The deterministic typed terminal completed a database-backed enquiry. New training code provides SVM and TextCNN paths but refused to train because reviewed DB dataset partitions are absent; no trained NLP accuracy is claimed. Runtime NLP rules and passenger response copy now come from the DB, with authenticated CRUD/import for nlp-intents, nlp-rules and nlp-templates. Final regression checks: 151 tests passed, Ruff passed and Mypy passed. English-first acceptance remains INCOMPLETE, including trained classifiers, reviewed accuracy/WER evaluation, live microphone conversation, playback verification and OS-level offline isolation.

## Phase 2 training execution

PHASE 2 INCOMPLETE. Actual English-only pilot-v2 SVM and TextCNN checkpoints were trained/reloaded on 63 unreviewed rule phrases across 44 labels. Training-only macro-F1 was 1.0000 for SVM and 0.15647 for TextCNN. There is no independent-test score, no 10000-record reviewed corpus and no production model selection. Candidates are not active; runtime DB rules remain in use. See docs/phase2-report.md and models/benchmarks/phase2-comparison.json for audit, measured results and limitations. No Phase 3 or UI work was added.

## Phase 2A taxonomy

Registered exactly 60 canonical enquiry intents in six groups, separate from 14 dialogue acts, with 32 entity definitions, 300 agent-authored English examples pending human review, explicit slot alternatives/clarifications, 11 semantic ambiguity pairs and canonical-to-legacy compatibility links. Source files: training/config/intent_registry.yaml, entity_registry.yaml, dialogue_acts.yaml and training/datasets/phase2a_seed_examples.jsonl. JSON-compatible YAML is used to avoid an extra parser dependency.

Runtime taxonomy reads come from existing NLP database tables, expanded with additive migration 0010. See docs/NLP_INTENT_CATALOG.md, docs/NLP_INTENT_AMBIGUITIES.md and docs/NLP_ENTITY_SCHEMA.md. Intent APIs: GET /api/v1/nlp/intents, GET /api/v1/nlp/intents/{code}, GET /api/v1/nlp/entities. API responses expose 41 PARTIAL and 19 UNSUPPORTED capabilities, with zero falsely marked IMPLEMENTED. Registration does not complete those operational handlers or provide live/booking integrations. Intent-specific response template IDs are reserved, with template_available=false until real templates are installed.

Validation: python scripts/validate_taxonomy.py. Existing and fresh SQLite migrations, repeat seeding, integrity_check and foreign_key_check succeeded. Taxonomy API smoke tests block Python socket connection attempts. PostgreSQL and OS-level network isolation were not exercised. The 300 seed questions are taxonomy verification material, not human-reviewed training data and not an independent test set. No Phase 2B corpus expansion, model training, speech or UI work was performed in Phase 2A. Existing prior-phase limitations remain.

## English text conversation track

Run from the repository root in the existing backend Python environment (no speech installation is needed):

```powershell
$env:PYTHONPATH = 'backend'
python -m app.cli.chat --station DEMO0 --operator DEMO
```

The command `python -m app.cli.chat` also works with that PYTHONPATH; it prompts for a boarding stand and, if necessary, operator. Database connection comes from `DATABASE_URL` (default `sqlite:///rtc.db`). `--database`, `--station`, `--operator`, `--session` and `--debug` are optional. Sessions are independent and expire after 15 minutes of inactivity. The terminal accepts `/help`, `/reset`, `/context`, `/debug`, `/station [name or code]` and `/exit`. `/reset` clears saved context and starts a new conversation; boarding/operator defaults remain configured for the terminal.

Examples: `Next bus to Nellore`, `AC only`, `Cheapest one?`, `Tomorrow morning`, `No, Tirupati`, `The second one`, `How much?`, `Seats?`, `Is the platform still the same?`. Filters persist until changed or `Clear filters`; route, date and filter changes invalidate the previous selected service. Numbered selection uses the displayed first five results. The earliest service is selected automatically for explicit next/first/last/cheapest/fastest requests; broader result lists require a numbered selection when multiple services match. Unknown or contradictory input prompts for clarification. No language-model output is used to generate SQL.

For an isolated demonstration database, leaving the active database untouched:

```powershell
$env:PYTHONPATH = 'backend'
$env:DATABASE_URL = 'sqlite:///text-demo.db'
python -m alembic upgrade head
python -m app.seed
python -m app.demo
python -m app.nlp_seed
python -m app.taxonomy_seed
python -m app.cli.chat --station DEMO0 --operator DEMO
```

All schedule, fare and operational answers use local database values. Demo results are visibly labelled; absent fares, platforms or inventory remain unknown. The 60 canonical taxonomy entries are recognized through local database rules/registry examples and explicit mappings: 41 have partial backend integrations and 19 return an honest unsupported response. This is not a claim of complete capability or high measured general-English accuracy. The locally loadable SVM is still CANDIDATE and is not promoted by this track. No independent NLP accuracy evaluation has been completed.

Verification and measurement:

```powershell
python -m pytest -q backend/tests
python -m ruff check backend/app backend/tests scripts/benchmark_text.py
python -m mypy backend/app --ignore-missing-imports
python scripts/benchmark_text.py --iterations 100
```

Tests use temporary demo databases. The new dialogue suite is evaluation-only and is not copied into training or the independent simulation lab. The benchmark blocks Python socket egress, uses a temporary seeded database and records component/end-to-end latency and memory. See `docs/text-track-report.md`, `docs/text-benchmark.json`, `docs/text-capabilities.json` and `docs/text-tests.xml` for actual results and limits. No voice components or passenger graphical interface are introduced.

## Phase 2B dataset generation

PHASE 2B INCOMPLETE. Reproducible local generator, typed validators, duplicate/diversity checks, parent/family guards and exports are implemented. Current collection: 449 schema-valid unreviewed synthetic candidates, including 300 preserved/reused Phase 2A seeds and 149 additional records. Dataset categories: 300 single-intent, 16 multi-intent, 12 contextual, 20 out-of-scope, 11 ambiguity, 13 negative/correction and 77 ASR-style. All 60 intents have dedicated generation specifications, but only five authored single-intent examples each; the requested 200 per intent and overall 16000 minimum are unmet. No destination-substitution padding was used to claim those targets.

Canonical combined file: training/datasets/generated/2b-v1/all.jsonl. Category files, DB vocabulary snapshot and exports are beside it. Reports: training/reports/PHASE_2B_DATASET_REPORT.md, phase2b_quality.json and phase2b_foundation_coverage.json. Detected normalized duplicate pairs: 0; near-duplicate heuristic pairs: 82. These findings do not establish semantic uniqueness. All generated examples remain PENDING_HUMAN_REVIEW; no human-reviewed or real-world accuracy claim is made.

Commands: python training/generation/generate.py; python training/validation/validate_phase2b.py; python training/generation/export.py training/datasets/generated/2b-v1/all.jsonl --output training/datasets/generated/2b-v1/exports. Native Hugging Face Arrow export is optional and was not tested; local JSON transport and CSV exports were executed. No training, actual split construction, Phase 2C advancement, speech orchestration or UI work was performed.

## Phase 2 final execution

PHASE 2 INCOMPLETE. Created a checksummed family/parent/near-duplicate grouped 449-record synthetic snapshot (234 train, 76 validation, 139 synthetic challenge; independent test 0). Actually trained and reloaded new 60-label SVM and TensorFlow TextCNN candidates. Validation macro-F1: SVM 0.177540, TextCNN 0.014697; synthetic-challenge macro-F1: 0.212619 and 0.071667. SVM is the development winner, but neither model is approved or active. No suitable validation confidence threshold was found. Runtime retains DB deterministic rules and safe clarification.

Added shared thread-safe local model loading, inference facade, /api/v1/nlp/health, composed conversation regressions and fixes for ordinal selection and feature modifiers. Final tests: 796 passed; Ruff and Mypy passed. Local text benchmark median 32.4 ms, P95 42.5 ms. These are performance measurements on fictional demo data, not production accuracy. No human-reviewed independent corpus, production model selection, representative answer accuracy or OS-level isolation is established. See docs/PHASE_2_FINAL_REPORT.md and docs/MODEL_COMPARISON.md. No UI or Phase 3 audio orchestration was added.


## Phase 3A advanced English dialogue

PHASE 3A INCOMPLETE. Implemented typed conversation state, explicit context operations and dependency invalidation, stable result references, selected-service handling, bounded multi-intent fare/arrival reuse, additional temporal and correction handling, CLI result selection/history, and owner-token protected context inspection. Operational answers continue to use local database records. Existing tokenless message sessions remain supported for compatibility; universal ownership enforcement is unfinished.

Verification: 1,109 tests passed (one dependency deprecation warning); Ruff passed; Mypy passed for 51 source files. Added 300 parameterized 2/5/10-turn scenarios plus focused regressions. These synthetic scenarios do not establish representative passenger-language accuracy. Reproducible 100-request SQLite demo benchmark: P50 22.166 ms, P95 29.305 ms, P99 50.391 ms. Concurrent-load performance and OS-level network isolation were not verified.

Contextual category comparisons, general next-three pagination, some ambiguous references/date corrections, proactive cached-result invalidation and same-session conflict handling remain incomplete. See [Phase 3A report](docs/PHASE_3A_REPORT.md) for implemented behavior, measurement scope, commands and remaining requirements. No speech or graphical UI was introduced.


## Phase 3B local journey planning

PHASE 3B INCOMPLETE. Added bounded time-dependent direct/one-/two-transfer planning with intermediate and variant stops, calendars, cancellations, fresh verified stop observations, transfer/wait limits, typed validated itineraries, seven ranking modes, unknown-fare-safe totals, explicit missed-bus alternatives and fresh-search replanning. Four versioned journey APIs and English conversation selection/ranking/date integration reuse the existing database and enquiry modules. Existing TimetableEngine API and migrations are preserved.

Actual benchmark:100-service median11.725ms (P95 13.411ms),1000-service median64.774ms,10000-service median687.925ms;14 DB queries per completed same-corridor SQLite fixture. The50000-service fixture was refused at the capacity bound. These are synthetic measurements, not national-network/concurrency certification. Final full suite: **1,381 passed** (one dependency deprecation warning); Ruff and Mypy passed. See [Phase3B report](docs/PHASE_3B_REPORT.md).

Remaining work includes leg-scoped constraints/dialogue, explicit inter-stand transfer data, concession/surcharge evaluation, detailed disruption/stop-closure semantics and production-scale verification. PostgreSQL and OS-level offline isolation were not tested. See [journey usage](docs/JOURNEY_PLANNER.md), [algorithm](docs/ROUTING_ALGORITHMS.md) and [requirement matrix](docs/phase3b-gap-matrix.json). No voice or graphical UI was added.


## Phase 4A — working passenger and admin app

The application has been built, started and tested against the existing backend/database. Passenger chat, real bus cards, search, connecting-journey planning, service timelines, protected administration, supported CRUD/imports, diagnostics and system status are implemented. Domains without write APIs are explicitly read-only. Earlier backend/model limitations remain; this is not a claim of overall RTC or production completion.

```powershell
# From the repository root, with dependencies already installed:
.\start-rtc.ps1
# Compiled offline app, served directly by FastAPI:
.\start-rtc.ps1 -Production
```

Development: http://127.0.0.1:5173. Production: http://127.0.0.1:8000. The launcher runs existing migrations, prints the local administrator token (or uses RTC_ADMIN_TOKEN), and performs no downloads. Ctrl+C stops its processes. Optional `-InitializeDemo` runs the existing demo seeds; the default preserves existing records. Choose the actual current stand: the standard Tirumala → Nellore DEMO enquiry and fare follow-up were verified against the existing database.

One-time setup: `python -m pip install -r requirements.txt`, `npm ci --prefix frontend`, `npm run build --prefix frontend`. Production needs only Python and compiled frontend/dist; it does not require Node. Model artifacts are preserved and no speech/cloud model is introduced.

Verification: **1388 backend tests passed;19 production Playwright tests passed**. Frontend lint/TypeScript/build, Ruff and Mypy passed; npm audit reports zero vulnerabilities. Browser tests block external requests and use actual API/SQLite fixtures. No OS firewall isolation or PostgreSQL execution claim is made. See [app setup](docs/APP_SETUP.md), [Phase4A report](docs/PHASE_4A_REPORT.md), [coverage](docs/phase4a-coverage.json), and browser screenshots in docs. Phase 4B supersedes the page-local sorting/filtering limitation with server-wide search and sorting; unsupported administration remains read-only.

Frontend checks: `npm run lint --prefix frontend`; `npm run build --prefix frontend`; `cd frontend; npm test`. Browser setup once: `npx playwright install chromium`. Backend checks retain the commands above. Assets use local bundles/system fonts only; no CDN, remote analytics, payment or booking flow.

## Local capability extension and frozen SVM evaluation

The latest text-only extension adds 15 enquiries using existing tables: buses near a specified time; per-date departure counts/gaps; special-date schedules; wheelchair-accessible vehicles; recorded capacity; route-segment distances; bounded destination reachability; reservation channels; fresh verified arrival estimates and actual arrival/departure observations; platform reassignment history; operator websites; recorded station addresses/bay zones; and complaint contacts.

There are now **56 PARTIAL local handlers and four UNSUPPORTED intents**. Booking status has no authorized status record; cancellation policy, refund policy and luggage rules have no applicable policy records. They remain unsupported. A partial handler returns UNKNOWN when its required local records are absent. Capacity is never vacant-seat inventory; a timetable is never proof that a bus has arrived or departed. Operator contact exposes only the recorded website, and station navigation provides recorded locations without inventing indoor directions.

Existing database taxonomy entries are adapted at read time for these implemented handlers; new taxonomy seeds use the updated capability metadata. No automatic database refresh, migration, model promotion or training is performed. Existing speech artifacts are preserved.

Run the additional checks and evaluation:

```powershell
python -m pytest -q backend/tests/test_local_intents.py backend/tests/test_svm_holdout_integrity.py
.\.venv-english\Scripts\python.exe scripts/evaluate_svm_holdout.py
```

The newly authored frozen evaluation has 180 single-intent questions and 20 out-of-scope questions; one exact-overlap out-of-scope question is excluded by the preregistered lexical audit. Pilot-v2 SVM accuracy was **26.67%**; grouped-60-v1 SVM accuracy was **65.00%** on the same 180 eligible questions. Both raw forced-choice classifiers falsely accepted all 19 eligible out-of-scope questions. No candidate was activated or tuned. These are agent-authored held-out results, not human-reviewed field accuracy.

See `docs/local-intents-report.md` and `evaluation/english-svm-v1/REPORT.md` for measured results, limitations and reproduction details. All questions and their predictions stay outside training datasets.

## Improved text SVM and out-of-scope rejection

The `selective-60-v2` candidate uses a 60-intent SVM plus a binary in-scope/out-of-scope SVM. Train-only TF-IDF features and separate validation data determine its parameters and rejection thresholds. Existing active-model approval gates remain unchanged, so the candidate is **not enabled in ordinary chat**.

Inspect the candidate without changing deployment:

```powershell
.\.venv-english\Scripts\python.exe scripts/predict_selective_svm.py "Please explain whether this bus has an AC cabin"
.\.venv-english\Scripts\python.exe scripts/predict_selective_svm.py "Help me choose a mutual fund investment"
```

This terminal-only command runs offline and displays KNOWN, OUT_OF_SCOPE or CLARIFICATION_REQUIRED with decision margins, not probabilities. It validates the saved candidate checksum and never queries or changes the RTC database.

The snapshots contain 771 training and 240 validation records. Nine proposed training examples were excluded by leakage/duplicate checks. Fresh-test questions were frozen before fitting, and none of the earlier evaluation questions were used to train or tune the model. On the new 180-ID/60-OOS test, closed-set intent accuracy improved from **49.44% to 81.67%**. The candidate rejected **58/60 OOS** questions, accepted **171/180 ID** questions and had **80.70% accuracy among accepted ID questions**. These agent-authored results are not human-reviewed field accuracy. No test-driven retraining or threshold changes followed evaluation.

See `docs/selective-svm-report.md`, `training/datasets/selective-60-v2/README.md` and `evaluation/english-svm-v2/REPORT.md` for data boundaries, measured results and remaining limits. All work is text-only; speech artifacts, existing models, prior evaluation sets and UI code are preserved.

## Phase 4B — interactive passenger and admin improvements

Implemented real conversational follow-ups and expiry-safe kiosk resets, fresh service cards, backend-validated journey comparison, accessible service tabs, server-wide admin search/sort, database Data Quality, actual NLP diagnostics and System Status. No schema replacement, cloud service or voice feature was introduced.

Verification: **1,459 backend tests and 35 production browser tests passed**. Final Ruff, configured Mypy, frontend lint/TypeScript/build passed; npm audit snapshot has zero vulnerabilities. Existing SQLite fixtures and blocked external application requests were used. PostgreSQL and OS firewall isolation are not claimed. Fare-rule expiry/rejected-row history checks remain limited by existing schema, some admin domains are read-only, and reference choices are capped at 100. See [Phase 4B report](docs/PHASE_4B_REPORT.md), [gap audit](docs/PHASE_4B_AUDIT.md), and [app setup](docs/APP_SETUP.md).

## Phase 4C — passenger conversation and reliability stabilization

Added database-backed pending station clarification, current-list selection revalidation, destination-safe stop/transfer questions, explicit no-result recovery, planner reset, configurable activity-aware kiosk expiry, interrupted-request/draft recovery, unsaved admin edit guards, additional data-quality checks and bounded local request diagnostics. Existing migrations/APIs and model approval gates are preserved.

Backend regression: **1,484 passed, 0 failed**. The production browser suite contains **132 real-local-backend tests** including the requested conversations and ten-step seeded acceptance flow. Ruff, configured Mypy, frontend lint/TypeScript/build pass. A local SVM candidate loads and infers with all socket connections blocked in the provisioned model environment; production continues with deterministic fallback because that candidate remains unapproved. Data/schema, model-readiness and deployment limits are explicit in the [Phase 4C report](docs/PHASE_4C_REPORT.md), [audit](docs/PHASE_4C_AUDIT.md), [coverage](docs/phase4c-coverage.json) and [performance report](docs/PHASE_4C_PERFORMANCE.md). This records the Phase 4C baseline; the Phase 5A implementation below supersedes its admin/database limitations.


## Phase 5A — offline enterprise data management

Implemented operator-scoped administration, named editor/independent approver access, staged CSV/XLSX imports with explicit mapping and row validation, schema-generated templates, transactional publication, audit/version snapshots and guarded rollback. Route/variant and timetable editors, dated Decimal fare rules/surcharges and preview, all eight service exception types, platform updates and actual quality metrics feed existing passenger enquiries after publication.

Original migrations 0001–0010 remain intact; incremental migrations 0011–0014 extend existing tables. The actual SQLite upgrade preserved all original values in 71 tables/1,112 rows and passed integrity/foreign-key checks. No official operational dataset was invented. Existing DEMO records remain labelled DEMO.

Verification: **1,566 full backend regression tests passed**, followed by **84 final SQLite/PostgreSQL data-management tests** (overlapping counts), **two maximum-size 10,000-row validation tests**, and **140 production browser tests**. Ruff, configured Mypy, ESLint, TypeScript and build passed. PostgreSQL cases actually ran on a local dedicated database. External application requests were blocked in the browser/backend integration servers. The running app also passed a real import → independent approval → passenger alias enquiry → rollback smoke.

**PHASE 5A COMPLETE** within the documented local limits. No authoritative APSRTC timetable/fare/source files were supplied; onboarding them remains a deployment input. Legacy batches without snapshots cannot roll back; imports are synchronous and bounded at 10 MB/10,000 rows. Existing model approval gates remain unchanged. See [completion report](docs/PHASE_5A_REPORT.md), [requirement audit](docs/PHASE_5A_AUDIT.md), [data-management setup](docs/PHASE_5A_SETUP.md) and [live smoke evidence](docs/phase5a-live-smoke.json).


## Phase 5B - local Bus Stand Operations Control Center

Implemented `/admin/operations` and the public `/board`, validated dispatcher state transitions, station/operator-scoped staff roles, idempotent versioned events, confirmed/observed platform distinctions, revised ETA/delays, cancellation and independently approved reinstatement, reviewed disruptions/English announcements, append-only audit and reconnecting local WebSocket updates. Existing passenger NLP/enquiry and journey planning use the same operational projections. No clock-based actual movement, GPS feed, cloud broker or voice feature was introduced.

Incremental migrations 0015-0016 extend existing tables. The live SQLite upgrade preserved all original values in 71 tables/1,150 rows with integrity and FK checks passing. Verification: **1,618 full backend tests passed**, followed by **54 final SQLite/PostgreSQL dispatcher tests** (overlapping), and **144 production browser tests**. Ruff, configured Mypy, frontend lint/TypeScript/build pass. Main-app labelled DEMO acceptance verifies delay/revised departure/platform, no false departure, recorded departure, NLP and actor/source/time audit; temporary capabilities were revoked.

**PHASE 5B COMPLETE** within documented local limits. Official operations/data still require authorized local input; demo fixtures remain DEMO, GPS/physical bay occupancy remain unknown without observations, and multi-server scale is not certified. See [completion report](docs/PHASE_5B_REPORT.md), [requirement audit](docs/PHASE_5B_AUDIT.md), [operations setup](docs/PHASE_5B_SETUP.md) and [live acceptance](docs/phase5b-live-acceptance.json).


## Selected-journey conversation upgrade

The backend now persists actual selected journeys and exact boarding/alighting segments across turns. After choosing option 2, fare/amenity/stop/platform follow-ups use that selection, re-read current database records and distinguish missing data. Context corrections invalidate outdated selection. Owner-bound versioned sessions, safe retries, server restoration, backend suggestions and compact chat controls are implemented. See [implementation, contract, cleanup and verification](docs/CONVERSATION_UPGRADE.md) and the [original request](docs/CONVERSATION_UPGRADE_REQUEST.md). Existing database migrations and transport records are preserved; acceptance fixtures are explicitly DEMO.


Conversation-upgrade verification: **1,736 backend tests passed** with PostgreSQL enabled; final memory tests **117 passed**, additional SQLite/PostgreSQL memory/concurrency tests **2 passed**; **148 full browser tests + 1 restore regression passed**. Ruff, Mypy, ESLint and production build passed. The eight-turn local acceptance and network-blocked offline smoke passed. See [actual results and limitations](docs/CONVERSATION_UPGRADE.md#executed-verification) and [machine-readable evidence](docs/conversation-upgrade-verification.json).


## Phase 5C — offline conversation intelligence

Implemented compositional enquiry plans, primary-bound secondary queries, validated journey comparisons, deeper stable references, arrival-deadline reasoning, corrections, summaries and focused DB category clarification. Passenger chat now includes expandable answer sections and comparison facts. Existing APIs, model approval gates, transport data and migrations remain intact; no voice or cloud runtime was added.

Verification: **2,048 backend tests passed** (including **70 PostgreSQL cases**), **307 Phase 5C scenarios passed**, **153 browser tests passed**, and a final focused browser rerun passed all four tests. Ruff, Mypy, ESLint and production build passed. The exact ten-turn live acceptance and networking-blocked offline smoke passed. Median seeded DEMO chat send-to-render: **166 ms**. [Completion report, gap matrix, measured results and limitations](docs/PHASE_5C_REPORT.md); [verification JSON](docs/phase5c-verification.json).

## Phase 5D — recovery, feedback and supervised NLP improvement

Implemented targeted conversation repair, explicit uncertainty, bounded DB-backed no-result diagnosis, compact optional passenger feedback and an operator-scoped NLP Review Queue at `/admin/nlp-review`. Approved-only dataset export feeds an authorized offline SVM candidate workflow with leakage checks, validation thresholds, regression gates, separate manual approval/deployment and rollback. Actual usage/review metrics and question-mix drift require recorded evidence; no missing feedback or automated DEMO label counts as human-reviewed accuracy. Existing transport schema, migrations and APIs are preserved.

Verification: **2,307 backend tests passed**, including **71 PostgreSQL cases**; the overlapping Phase 5D suite passed **259 tests**. **157 browser tests** and **4 final focused browser tests** passed. Ruff, configured Mypy (60 files), ESLint, TypeScript and production build passed. Main-app DEMO acceptance and the outbound-network-blocked conversation/feedback/review/export smoke passed. Median five-sample browser send-to-answer latency was **209 ms**; measured live feedback write was **27 ms**.

**PHASE 5D COMPLETE within the documented local limits.** No production model was retrained or promoted; genuine human-reviewed full-taxonomy data and independent holdouts are still required to establish model improvement. Question retention defaults off (`RTC_FEEDBACK_RETAIN_TEXT=0`); enabling it still requires passenger opt-in. See the [requirement audit, operating instructions and limitations](docs/PHASE_5D_REPORT.md), [original request](docs/PHASE_5D_REQUEST.md) and [actual verification results](docs/phase5d-verification.json). No Phase 5E or speech work was started.

## Phase 5E — local deployment and recovery

Implemented explicit standalone SQLite / central PostgreSQL modes, production Windows/Linux launchers without automatic migration/downloads, process locking and graceful stop, service/task templates, pool recovery/timeouts, WAL, periodic session cleanup, authenticated health diagnostics, broader versioned local invalidation, verified backups/restores and private-data-free snapshots with guarded transactional reconciliation. Existing schema, migrations, weights and active model registry are preserved. Startup now requires explicit private configuration; use the [deployment instructions](docs/PHASE_5E_DEPLOYMENT.md), which supersede earlier automatic startup/seed examples.

Verified: **2,317 backend tests**, including **75 PostgreSQL cases**, and **157 final production browser tests** passed. The overlapping final reliability/model suite passed **11 tests**. Ruff, configured Mypy, ESLint and production build passed. Real DB outage/recovery, API crash/manual restart, graceful stop, duplicate launch rejection, SQLite and PostgreSQL isolated restore, and live/socket-denied platform updates passed. Short final load runs reached 50 simulated kiosks with zero request errors; P95 was **4.04 s SQLite / 4.77 s PostgreSQL**, with earlier failed/limited trials retained in the report.

**PHASE 5E INCOMPLETE:** OS-level network-isolation certification, installed-service reboot/automatic restart tests and physical multi-terminal LAN/TLS/firewall verification remain blocked or unexecuted on this nonadministrative Windows host without Linux. The approved English model also remains unavailable; deterministic fallback is explicit. See the [audit, results and remaining gates](docs/PHASE_5E_REPORT.md) and [verification JSON](docs/phase5e-verification.json). No Phase 6 or speech development was started.

## English model accuracy recovery

Trained immutable `recovery-60-v3` SVM and TensorFlow TextCNN candidates from **2,209 synthetic training examples**, including **34–35 examples for each of the 60 enquiry intents**. Frozen validation and synthetic challenge each contain 180 in-scope / 60 out-of-scope questions. Contextual and multi-intent records remain outside the single-label loss; DB vocabulary, leakage exclusions and provenance are recorded.

On the identical 180-question synthetic challenge, grouped SVM scored **49.44% accuracy / 0.4764 macro-F1**, the new SVM **92.78% / 0.9266**, old CNN **9.44% / 0.0901**, and new CNN **85.00% / 0.8479**. New SVM selective acceptance has **97.71% accepted-ID accuracy at 72.78% ID coverage**, with 0/60 OOS false accepts; this small synthetic sample does not establish production safety. The CNN failed validation rejection calibration and remains reject-all. These raw/coverage figures must not be conflated.

**DETERMINISTIC_RULES remains active. Both candidates are unapproved.** The user confirmed that no independently human-reviewed test set is available; reviewed validation, independent test evidence and further corpus expansion toward 200+/intent remain required. Full backend regression **2,327 passed**, focused dialogue/offline regression **679 passed**, corpus/model checks **25 passed**; Ruff and Mypy passed. No UI or speech changes were made. See the [complete analysis, comparisons, inference measurements and promotion recommendation](evaluation/english-recovery-v3/REPORT.md) and [original request](docs/ENGLISH_ACCURACY_RECOVERY_REQUEST.md).
