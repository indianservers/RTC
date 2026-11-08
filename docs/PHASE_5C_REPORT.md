# Phase 5C: advanced offline conversation intelligence

## Scope and audit

This change strengthens the existing FastAPI/React conversation engine. It introduces no new chatbot architecture, cloud model, inference API, voice runtime, transport table or migration. The existing local classifier approval gates and deterministic fallback remain intact. Administrative screens were not redesigned. The original request is in `PHASE_5C_REQUEST.md`.

The concise requirement-by-requirement capability gap matrix is `phase5c-gap-matrix.json`. Its 12 rows record the inspected code gap, correction and test evidence. Existing ownership/version/reset/offline behavior was preserved, rather than rebuilt.

The main audited defects were: early-return intent rules dropping composed questions; secondary enquiries using a default service rather than the primary result scope; no common validated comparison path; missing summary/reference policies; reaching-before interpreted as departure-before; and an unknown category silently failing to become a constraint. The live database has only labelled Demo seater/sleeper/electric/express categories and no Super Luxury alias. The final acceptance therefore correctly asks for a recorded category; it does not create a fictional official category or silently ignore the requested restriction.

## Implemented behavior

- **Compositional parsing and planning:** the existing planner is now named ConversationQueryPlanner, with ExecutionPlanner retained as a compatibility alias to the same implementation. Canonical intents are deduplicated, bounded to three tool intents, and ordered by dependency. AC/sleeper constraints remain filters of the primary enquiry. The response exposes primary_intent, secondary_intents, shared_entities and executed dependencies. Timetable fare/arrival projections reuse the same fresh primary rows; platform/delay/seats/via questions bind to their service/date/segment. No unrelated service search is used for a secondary question. Partial results remain available when one field is unknown.
- **Contextual comparisons:** current displayed references are refreshed through the existing RTCEnquiryEngine, including fares, times, cancellation eligibility and actual vehicle attributes. Comparisons require equal boarding/alighting segment and boarding date. Unknown fares are never zero or cheaper; a cheapest-known comparison explicitly excludes unpriced options. Ties are listed. Fare/duration/arrival/AC facts and result IDs are returned. A comparison with the first option keeps the confirmed selection. Premium fare differences require an unambiguous selected baseline and category match.
- **References:** that one, next one, predecessor, other one, category name, clock time, last option, second service, cheapest, previous, both and neither use the existing result set. Unique references become numeric selections in the established stable-ID and DB-revalidation path. Multiple other options or category/time matches ask for clarification. Both requests a two-option comparison; when more than two are shown it asks which pair. Neither clears the selected/listed options and retains route/preferences; it does not imply a booking operation.
- **Multi-step constraints and corrections:** reaching-before sets arrival_before. AC, budget, date/window and transfer preferences survive later turns. Removing the earlier time explicitly clears time bounds and invalidates dependent selection. Passenger count changes also invalidate dependent result state. Unknown category restrictions remain pending until a database category is chosen or Any bus type explicitly clears them. Not AC, ordinary preserves the explicit non-AC correction while asking for a category if ordinary has no DB record.
- **Clarification and summaries:** fare uses a selected exact segment; no route context asks for destination/service. Is it available on a selected service checks recorded operational status, without claiming seat availability. Summaries use DB names and saved constraints, label the current bus-stand default, distinguish confirmed selection from a query default, and mention unresolved category restrictions. Remind me of the options revalidates stored references. Reset clears server history through the existing path.
- **Natural, grounded responses:** empty searches explain the active route/date/restrictions and offer a next action. Fare, platform, capacity and other missing facts retain their existing explicit unknown behavior. Scope-only weather, political, food-order and joke requests run no transport tools and retain context. Scheduled/estimated arrival labels are preserved in comparisons; operational freshness stays in existing engine results and additive source metadata.
- **Passenger UI:** expandable answer sections and recorded comparison facts, accessible native details controls, real category clarification buttons and backend-driven follow-up chips. No simulated streaming. Existing owner capabilities, stale-response guards, retry IDs, reset, compact context strip and mobile layout remain. Old clarification choices are disabled once their response is no longer current.

## Backward-compatible contract

POST `/api/v1/conversation/message` is unchanged. Existing answer/intents/entities/context/results fields and the previous memory upgrade aliases remain. Additions are typed Pydantic fields:

- dialogue_act
- query_plan: primary_intent, secondary_intents, shared_entities, dependencies
- answer_sections: intent, title, text, status
- clarification_choices: id, label, text
- source_metadata: source, freshness, recorded_at, expires_at per result row

These are informational or real API actions, not new transport facts. The UI continues to show the backend response text; details and suggestions also come from the backend. Comparison results use CONTEXT_COMPARISON with exact result_ids, structured current facts, explicit winners and answer_text. This is a conversation-level result, not a new enquiry endpoint. Session ownership, SQLite write transactions, PostgreSQL row locks, expected versions and idempotent request handling remain in the existing implementation. Cleanup/retention remains documented in `CONVERSATION_UPGRADE.md`.

## Tests and measurement

The new authored suite includes 300 multi-turn FastAPI/SQLite scenarios (15 behavior families across 20 dates) and additional targeted cases. Assertions measure intent identity, entity IDs, context transitions, query-plan scope, selected stable references, exact fares, unknown fields and comparison winners. These are controlled regression pass rates, not a claim of general-language model accuracy. Separate existing suites exercise concurrency, session isolation, expiry, reset, changed fares, overnight boarding and SQLite/PostgreSQL operation. The browser suite blocks external requests; its backend harness blocks external socket access.

**Status: PHASE 5C IMPLEMENTED AND VERIFIED.**

- Full backend: **2,048 passed, 0 failed, 0 skipped**, 393.566 seconds. **70 PostgreSQL cases actually executed** against the dedicated local test database. Evidence: `phase5c-backend.xml`, `models/benchmarks/phase5c-backend.txt`.
- Final authored Phase 5C suite: **307 passed**, including the full 300 multi-turn matrix and seven focused cases. Evidence: `phase5c-conversation.xml`, `models/benchmarks/phase5c-scenarios.txt`. The matrix uses 15 behavior families and 20 dates. Every scenario checks initial intent, entity IDs, query-plan intent and stable session/version transitions; each family adds exact tool/result/constraint assertions. This is a regression outcome, not a claimed statistical model-accuracy improvement.
- Full browser suite: **153 passed, 0 skipped, 0 flaky, 0 unexpected failures**. Final focused browser rerun after the source-label/suggestion refinements: **4 passed**. Evidence: `phase5c-playwright.json`, `models/benchmarks/phase5c-browser.txt`, `phase5c-browser-focused.txt`.
- Ruff, configured Mypy (**55 files**), ESLint, TypeScript and Vite production build: **passed**. Evidence: `phase5c-ruff.txt`, `phase5c-mypy.txt`, `phase5c-eslint.txt`, `phase5c-build.txt`.
- Network-blocked offline startup/migrations and all **10 conversation turns passed**. Evidence: `phase5c-offline.json`, `models/benchmarks/phase5c-offline.txt`.
- Exact main-app acceptance: **10 turns passed**, with service/date/segment, fare, AC, arrival and comparison assertions. Source records were reused without transport-master changes. The live category limitation is explicitly represented, including after destination correction and summary. Evidence: `phase5c-live.json`, `models/benchmarks/phase5c-live.txt`.
- Named-browser main-app inspection: requested conversation performed, comparison and summary displayed, no console errors. Screenshots: `phase5c-comparison.png`, `phase5c-summary.png`, `phase5c-main.png`.
- Five-run isolated seeded DEMO medians: page ready **115.31 ms**; chat send-to-render **166.31 ms**; NLP API **44.76 ms**; planner HTTP **66.67 ms**. These local measurements are not production capacity guarantees. Evidence: `phase5c-performance.json`.
- Read-only live SQLite integrity: **ok**, **0 foreign-key violations**, Alembic revision **0016** retained. No applied migration was edited.

The initial new-scenario run passed 280 cases before an expiry test-helper assertion stopped it; that helper wrongly required the expired session ID to remain unchanged and was corrected. The initial full regression exposed 22 old assertions expecting generic no-results wording or a clarification question for out-of-scope requests. Those expectations were updated while retaining their database/context checks; the final full suite passes. Live acceptance additionally exposed the missing-category silent fallback, which was fixed and independently regression-tested. The existing Starlette TestClient/httpx deprecation warning remains.

Machine-readable summary: `phase5c-verification.json`. No known failing tests or substantial unimplemented Phase 5C feature remains within the bounded capabilities described here. No Git commit or push was requested for this phase.

## Offline and live acceptance

`python scripts/verify_conversation_offline.py --phase5c --first-query "Next bus to Nellore tomorrow?" --report docs/phase5c-offline.json` copies the live DB into a temporary SQLite snapshot, runs migrations and starts the backend with all socket egress and DNS blocked before backend import. The Windows test harness creates its asyncio wake-up loop before the guard, as documented in the existing smoke test. It executes ten turns and checks SQLite integrity and foreign keys. No master data is written by this smoke.

`python scripts/verify_phase5c_live.py` runs the exact ten requested utterances against the main local app on port 8000. It writes only ordinary chat state. The selected fare is cross-checked with the existing enquiry API, vehicle AC with a read-only database query, and arrival/comparison fields against the exact returned service references. All public context/query/answer records are saved in `phase5c-live.json`. No owner capability is written to the report. Existing labelled DEMO services from the previous acceptance were reused; no new official or synthetic transport records were added.

## Limitations

- The parser and response policies are bounded deterministic English grammars plus the existing approved-local-model gate. They are not an open-ended generative model. The existing unapproved candidate is not presented as newly approved or improved model accuracy.
- A maximum of three enquiry intents and five displayed options are planned per turn. For more questions, the passenger should ask another turn.
- Comparisons cover the current displayed compatible options, not every service in the database. A service that departed, was cancelled or changed eligibility requires a fresh search. Unknown fares prevent an overall cheapest claim.
- Same-category/time/other/both references must be unique; otherwise the system asks. Multi-leg operational questions retain the established boarding-leg disclosure. No GPS, booking, live seat inventory or reason for delay is invented.
- Unknown category names require DB master data or aliases. The live acceptance's Super Luxury request remains explicitly unresolved because no such category exists locally; it is not relabelled as Express.
- Summaries describe saved conversation state and label saved service references. Fresh transport enquiries revalidate current DB facts. Browser restoration is local-tab/capability based, not account synchronization.
- No speech work or unrelated administrative redesign is included.
