# Conversation memory and selected-journey upgrade

Implemented in the existing React/FastAPI application. English text enquiries remain local and deterministic when the configured local classifier is unavailable or unapproved. No model was downloaded, trained, approved or activated by this change. Transport facts continue to come from the database.

## Root cause and correction

The failure was in backend query scope, rather than a changing frontend session ID. Selecting a planner result persisted `selected_itinerary`, but deliberately cleared the single-service IDs. The next fare intent had no selected-itinerary execution path and fell through to an origin/destination timetable search. This could produce no result or a different departure's fare. The failing real FastAPI/SQLite reproduction returned INR 101 instead of the selected itinerary's INR 313. Evidence: `models/benchmarks/conversation-repro-before.txt` and `conversation-repro-after.txt`.

The existing context engine now stores the actual selected result, stable reference, dated service/leg references and boarding/alighting stop IDs. An adapter in the existing references module revalidates those exact segments using RTCEnquiryEngine. Fare lookup uses each current database fare, including existing operator, date and trip-override rules. It never uses a cached result's fare as the answer. Multi-leg totals require known fares for every leg; a known subtotal is labelled separately. Missing single-service fare returns: “The fare for that service is not available in the current database.”

Operational follow-ups resolve the current local Trip for the selected service/date, including trips added after the selection. They use the existing freshness/status engine. A cancelled selection can still answer cancellation/status; a subsequent journey/fare enquiry explains that updated options are required. Unknown platform stays unknown. Multi-leg operational questions identify the boarding leg used, or ask for a leg when necessary.

## Requirement verification

1. **Audit and exact regression:** failing integration reproduction recorded before the fix; selected itinerary option 2 followed by fare now queries its exact legs. Direct and intermediate boarding paths are also tested.
2. **Persistent memory:** existing conversation/context/message tables store owner-bound state, actual result snapshots, selection, dates/windows/preferences, clarification, last question/answer/activity and monotonically increasing revision. No new tables or migration changes were needed. Separate HTTP requests and a disposed/reopened database connection retain selection.
3. **Structured updates:** SET/REPLACE/CLEAR/INHERIT/CONFIRM/REJECT/RESET and SELECT_RESULT are supported by the existing ContextOperation engine. Public context actions allow only validated enquiry slots; private ownership/version fields are protected. Slot provenance distinguishes defaults, explicit changes, inheritance and confirmed selection.
4. **References:** current displayed-list references support numbers, first/second/last/next, previous confirmed option, cheapest/fastest and same-service follow-ups. Comparisons re-read current database facts before choosing. Ties ask for a service. Removed/rejected results cannot remain selected. Result-list versions prevent old cards from selecting against a new ordering.
5. **Elliptical follow-ups:** fare, duration, arrival, AC/sleeper attributes, stops/via location, platform and recorded operational status inherit selection. Explicit date/destination/filter changes invalidate selection and rebuild options. Named time periods survive date-only changes. Same bus tomorrow searches the recurring service on the new date and discards the old trip.
6. **Flows A–E:** 100 parameterized multi-turn real FastAPI/database scenarios cover different dates, intermediate boarding and selection phrases. Additional tests cover missing/changed fares, partial connections, cancellations, platform records added later, midnight boarding, expiry, concurrency, idempotency, resets and result refinement.
7. **Natural replies and provenance:** repetitive DEMO prose prefixes were removed. Source metadata and visible message-level DEMO badges remain. The UI uses server replies, facts, context and suggestions, without fabricated transport answers.
8. **Chat interface:** compact controls and context strip show DB station/category/service names, travel date and confirmed selection. Optional filter chips issue typed CLEAR_SLOT requests. Older card lists collapse, current cards retain valid references, messages scroll within the thread, and the composer remains visible. Existing loading, retry, reset, accessibility and mobile controls remain.
9. **Follow-up suggestions:** backend-generated typed suggestions reflect search, selection, fare and empty-result state. An optional-filter recovery action clears only its named filter. Every suggestion calls the real conversation API.
10. **API contract:** POST `/api/v1/conversation/message` retains legacy fields and adds message_id, response_text, detected_intents, detected_entities, current_context, selected_journey, result_set, follow_up_suggestions, pending_clarification and data_source. POST `/api/v1/conversation/state` restores owner-authorized state and up to 40 stored messages.
11. **Sessions/privacy:** shared kiosk is the default (15-minute backend idle cap; UI may clear sooner). Personal mode defaults to 24 hours. SQLite write transactions and PostgreSQL row locks serialize updates; expected_state_version rejects out-of-order writes with 409. Wrong owners receive 403. IDs are unpredictable and not displayed in chat. Reset deletes stored message history and clears selection. Personal mode changes require server acknowledgement.
12. **Recovery:** expired/missing session reports a new private conversation; restore of expired context returns 410. Interrupted requests retain their exact request ID/body for safe retry. Conflicting revisions offer a server-state restore. Changed/departed/cancelled services are rechecked, never silently replaced for a reference. Missing data receives a specific answer and useful follow-up actions.
13. **Offline:** the smoke imports and starts the backend, runs migrations and eight API turns with every socket connection and DNS operation denied. It uses a private SQLite snapshot, checks foreign keys/integrity, and leaves the live database unchanged. Browser tests deny external requests; their backend harness blocks external sockets.
14. **Live acceptance:** `conversation-upgrade-live.json` records all eight requested turns, full public state, selected reference, executed queries and source metadata against port 8000. Three fictional services, a recorded Ongole stop, AC vehicle assignments and two fares were published through the existing independent approval workflow. They remain clearly DEMO and have limited validity. Existing saved operational events were preserved. Temporary approver access was removed.

## Request and restore contract

New clients send owner_token (a browser-generated capability), client_message_id (unique per turn), expected_state_version (0 initially, then previous version), and session_id after the first response. Owner capabilities and internal receipt state never appear in public context or debug output. First-message retry recovers an opaque owner/message-derived session even when the first response was lost. A reused message ID with a different body is rejected. Last three complete receipts permit exact replay; last 100 processed IDs reject older duplicate submissions and request state restoration. Legacy clients without these optional concurrency fields remain supported; they do not receive the same explicit stale-version protection. Legacy ownerless sessions retain random-ID access compatibility; the passenger UI always sends an owner capability.

`context_action` is optional, for example `{ "op": "CLEAR", "slot": "ac" }` with text “Next bus”. Public slots cannot edit ownership, receipts or state_version. Responses retain existing `answer`, `intents`, `entities`, `context`, `results`, `state`, `requires_clarification`, `duration_ms`, `warnings` and `context_changes`. Selected-query metadata includes exact `segments`; each segment can be submitted to the existing enquiry endpoint using its supported request fields. The metadata object itself also includes selection diagnostics and is not a replacement EnquiryRequest schema.

Restoration is POST `/api/v1/conversation/state` with session_id and owner_token. It restores historical messages and context; a new enquiry always rechecks current database facts. Message history is retained in the database until reset or expiry cleanup; only the latest 40 are returned for restoration. Browser sessionStorage preserves the current tab across reload/navigation. This is not account-based cross-device recovery.

## Expiration and cleanup

`RTC_KIOSK_ONLY=1` rejects personal mode. `RTC_PERSONAL_IDLE_MINUTES` configures personal TTL within 15–10080 minutes (default 1440). A kiosk's UI idle selector permits shorter local clearing, while the backend enforces its 15-minute maximum. Changing mode preserves journey context and takes effect after server acknowledgement.

Expired context is unusable immediately. A bounded cleanup command redacts expired JSON and legacy journey columns, deletes stored messages and leaves only an ownership/expiry/revision tombstone. It does not delete master transport data. Run `python scripts/cleanup_conversations.py --limit 1000` to inspect counts. Add `--apply` to redact. If next_cursor is returned, pass it using `--after` for the next page. Use the application's DATABASE_URL. Schedule this local command according to the installation's retention policy; no background scheduler was introduced. Owner checks occur before accessing or resetting protected sessions.

## Reproduce checks

```powershell
python -m ruff check backend scripts training
python -m mypy backend/app --ignore-missing-imports
$env:RTC_TEST_POSTGRES_URL='postgresql+psycopg://rtc_phase5a_test@127.0.0.1:55435/rtc_phase5a_tests'
python -m pytest -q --junitxml=docs/conversation-upgrade-backend.xml
npm run lint --prefix frontend
npm run build --prefix frontend
npm test --prefix frontend
python scripts/verify_conversation_offline.py
```

The PostgreSQL command requires an independently running local test database. It must never point to the production database. The browser suite runs isolated DEMO databases on ports 8020/8021. The offline script copies rtc.db into a temporary directory; it does not write into the live database. On Windows it creates the test harness's asyncio wake-up loop before the guard because Windows implements that pipe with loopback sockets; backend import/startup/inference all occur after deny-all enforcement. The live-fixture script requires explicit execution and an administrator capability, creates DEMO master data through approval, and is not part of ordinary startup.

## Limitations

- Broad statistical intent accuracy is unchanged; the existing candidate remains subject to its approval gates. Unsupported language and low-confidence/out-of-domain text retain deterministic clarification behavior.
- “Same bus tomorrow” on a multi-leg itinerary asks which service/leg is meant. It cannot safely promise that a whole connecting journey repeats unchanged.
- A multi-leg platform/status response identifies the boarding leg used; separate leg selection is necessary for another leg.
- No live GPS, booking integration, invented seat counts or official transport claims were added. Scheduled/verified/stale/unknown remain distinct in existing enquiry responses.
- Context and result snapshots are historical references. Every selected follow-up revalidates eligibility and fares; a changed schedule may require a fresh list instead of silently selecting another departure.
- The station-wide next-departure board bounds its scan to 501 active services; larger installations should use a dedicated paginated departure query/index. Normal destination enquiries use the existing engine.
- Personal browser recovery is for the current tab and locally retained owner capability, not login-based synchronization. Expired text is removed by access-triggered redaction or the cleanup command; operators must run cleanup to meet their retention policy.

## Executed verification

Status: **IMPLEMENTED AND VERIFIED** for this conversation upgrade. No Phase 6 or voice work was started.

- Full backend suite: **1,736 passed, 0 failed, 0 skipped**, 992.253 seconds. This includes **69 PostgreSQL-parameterized tests actually executed**. Evidence: `conversation-upgrade-backend.xml`, `models/benchmarks/conversation-backend-final.txt`.
- Final conversation memory suite after the additional edge cases: **117 passed**, including 100 real multi-turn scenarios, midnight boarding, result refinement and the separate-process offline test. Evidence: `conversation-upgrade-memory.xml`, `models/benchmarks/conversation-memory-complete.txt`. The focused memory/text-dialogue run also passed all 431 tests; the older Phase 2 dialogue regression passed all 304.
- Additional real database memory/replay/concurrency test: **2 passed**, one SQLite and one PostgreSQL. PostgreSQL row-lock/version behavior was exercised, not inferred. Evidence: `conversation-upgrade-databases.xml`, `models/benchmarks/conversation-databases.txt`.
- Full Playwright suite on final build: **148 passed, 0 skipped, 0 unexpected failures, 0 flaky**, 305.664 seconds. One additional browser regression for a 409 conflict followed by actual server-history/selection restore: **1 passed**. Evidence: `conversation-upgrade-playwright.json`, `models/benchmarks/conversation-browser-final.txt`, `conversation-browser-restore.txt`.
- Ruff, configured Mypy (55 files), ESLint, TypeScript and Vite production build: **passed**. Evidence: `conversation-upgrade-ruff.txt`, `conversation-upgrade-mypy.txt`, `conversation-upgrade-eslint.txt`, `conversation-upgrade-build.txt`.
- Final local port-8000 replay: **all eight turns passed**, reusing the existing DEMO fixture after a process restart. No duplicate transport records were created in the replay. Option 2 fare: **INR 205**, queried for its exact service/date/segment. Evidence: `conversation-upgrade-live.json`, `models/benchmarks/conversation-live.txt`.
- Offline startup/migrations/eight-turn smoke: **passed**, with egress and DNS denied before backend import. SQLite integrity and foreign keys passed. Evidence: `conversation-upgrade-offline.json`, `models/benchmarks/conversation-offline.txt`.
- Live database read-only checks: **integrity_check=ok**, **0 foreign-key violations**, existing Alembic revision **0016** retained. Cleanup dry run scanned 18 contexts, identified 16 expired, and changed none.
- Five-run seeded DEMO benchmark medians: page ready **179.4 ms**; chat send to rendered answer **257.4 ms**; NLP API processing **140.3 ms**; planner HTTP **209.3 ms**. These are measured local-machine samples, not production load guarantees. Evidence: `conversation-upgrade-performance.json`.
- Main-app named-browser verification found no console errors. The full requested sequence was performed in the browser and separately checked through typed API responses. Screenshots: `conversation-upgrade-selected-fare.png`, `conversation-upgrade-main.png`.

The initial full run exposed 40 selected-query metadata compatibility failures; restoring the existing filter metadata fixed them. Browser runs exposed outdated suggestion selectors, an overly broad test edit and insufficient thread height in mobile kiosk mode; these were corrected and the final full browser suite passed. The existing Starlette TestClient/httpx deprecation warning remains; no functional failures remain in the executed suites.

Machine-readable final summary: `conversation-upgrade-verification.json`. Operational and approval data created by the earlier Phase 5B work remain intact. No Git commit/push was requested for this upgrade.
