# Phase 5D: conversation recovery and supervised improvement

Implemented in the existing RTC backend and passenger/admin UI. This phase adds no migrations, transport tables, cloud runtime or speech work. Existing enquiry services still fetch RTC facts from the database. The original request is preserved in `PHASE_5D_REQUEST.md`.

## Requirement audit and implemented behavior

1. **Failure audit and taxonomy.** Inspection covered `inference.py`, `entities.py`, `components.py`, `state.py`, `planner.py`, `pipeline.py`, response templates, the English model descriptor/registry, and the existing training/evaluation scripts. The gaps were generic no-results responses, intent corrections being interpreted as displayed-option references, absent owner-bound feedback, absent reviewed-feedback workflow and absent aggregate reliability evidence. `nlp/reliability.py` now defines all eleven requested error categories and separates provisional classification from a reviewer's finding.
2. **Repair engine.** `ConversationRepairEngine` handles targeted intent, destination and selected-bus corrections alongside the existing date/category correction machinery. Valid origin, destination, date and preferences persist; dependent selections are invalidated. Changing a filter after a platform/detail enquiry now executes a new journey search. Fare follow-ups continue to use the actual selected segment.
3. **Uncertainty.** Responses add typed reliability metadata with CONFIDENT, CLARIFICATION_REQUIRED, LOW_CONFIDENCE, OUT_OF_SCOPE or UNSUPPORTED. First-versus-next conflicts offer explicit choices. Entity ambiguity and missing slots use existing DB-backed clarification. Rule/SVM margins are never reported as probabilities. Reviewed candidate rejection thresholds are selected on validation data.
4. **No-results diagnosis.** Empty searches alone trigger bounded counterfactual probes for category, time and fare restrictions; route/stop, coverage and recorded cancellation checks use stored records. Hard preferences remain unchanged. Connecting searches report unconfirmed connection feasibility rather than applying a direct-route explanation. Missing/unpublished coverage is distinguished from a supported exclusion reason. Expired platform evidence is reported as stale without presenting its old bay as current.
5. **Optional feedback.** Every owner-bound assistant message supports compact Helpful/Not helpful/issue controls. Local feedback references the exact message and captures source, model/rules version, dataset version and minimal structured context. It is idempotent and excludes owner capabilities and raw session identifiers.
6. **Separate error workflows.** MODEL_ERROR, DATA_ERROR, CONTEXT_ERROR, RESPONSE_ERROR and OPERATIONAL_ERROR have separate counts and reviewer classifications. No matching service is not automatically an NLP mistake. Actual DB execution failures return a structured retryable 503.
7. **Review queue.** `/admin/nlp-review` offers all seven requested statuses, evidence, intent/entity corrections, notes, answer correctness, example kinds, dataset splits and independent-holdout attestation. Existing named admin roles and operator scope protect records; an editor cannot approve training. Version checks prevent lost review updates. Anonymization and deletion redact retained content and revoke training eligibility.
8. **Reviewed dataset.** NDJSON export includes only explicitly approved, consented, unexpired records with corrected labels/spans, context, provenance, reviewer, dates and training eligibility. It supports hard negatives, confusions, short follow-ups, contextual and out-of-scope examples. Raw feedback never enters training automatically.
9. **Manual offline improvement.** An explicit root-admin action validates the approved corpus, checks duplicate/group/template leakage and fits a candidate using the existing word/character TF-IDF + LinearSVC approach. Immutable local artifacts include dataset hash, labels, model checksum, validation thresholds, test/confusion metrics and regression comparison. Approval, deployment and rollback are separate versioned actions; the previous registry/model is retained. No passenger turn starts training or changes the active model.
10. **Quality and drift.** Text-free daily counters track actual intent mix, clarification, OOS, no-results, repairs, entity failures and station/category IDs. Seven-day question-mix comparisons require at least 100 observations in each window. New/renamed DB station identifiers and new categories are reported. Missing feedback is never positive feedback. Human-reviewed labels alone contribute accuracy/confusion evidence; automated DEMO labels are excluded.
11. **Grounded responses.** Missing fare/platform and unsupported enquiries are explicit; repair acknowledgements and recovery suggestions retain the current journey constraints. No operational observation, fare or platform is invented.
12. **Admin diagnostics.** The review page shows actual evidence counts, reviewed intent/slot/answer metrics, error distribution, model readiness/version, dataset version, candidates and dated manual deployment history. Unmeasured metrics display “Not measured.”
13. **Passenger UI.** Compact feedback, clarification choices, acknowledgements, unknown-data messages and existing optional conversation summaries preserve the chat layout. Diagnostics stay in administration.
14. **Regression scenarios.** `test_phase5d.py` contains 250 parameterized real API/database recovery cases plus four focused regressions. Learning and SQLite/PostgreSQL scope suites add five tests, for **259 Phase 5D tests**. These exercise actual deterministic interpretation and queries; they do not substitute mocked NLP outputs.
15. **Performance.** Repair detection and diagnostic time are measured separately; feedback writes and complete responses are timed. Diagnostics are skipped on successful ordinary searches. Recorded samples and limits are described below.
16. **Security/privacy.** Existing session ownership, authorization and operator scope apply to feedback and review. Private message envelopes stay out of public context. Sensitive responses are no-store; no external telemetry was added. Feedback question retention requires both an environment toggle and passenger opt-in. Text is bounded and email/long-number patterns are redacted.
17. **Live acceptance.** The main app passed next Nellore bus → last-bus correction → select → exact fare → wrong-bus correction → refresh/select another → platform → feedback → independent scoped reviewer approval → approved export. Additional turns verify a fare restriction diagnosis and first/next clarification. Sources remain explicitly DEMO. The acceptance label is AUTOMATED_DEMO_ACCEPTANCE and cannot satisfy human-evidence promotion gates.
18. **Delivery.** Code, APIs, UI, regression tests, offline verification script, screenshots, raw execution results and this report are included. No Phase 5E or speech work was started.

## API and storage contract

Existing conversation endpoints remain compatible. Additions are `reliability` and `feedback_policy` response fields and `POST /api/v1/conversation/feedback`.

Authenticated endpoints under `/api/v1/admin/nlp` are `GET /reviews`, `POST /reviews/{id}/review`, `POST /reviews/{id}/anonymize`, `DELETE /reviews/{id}`, `GET /export`, `GET /quality`, `POST /retention`, `POST /training` and `POST /models/{id}/{approve|deploy|rollback}`. Review pagination uses limit/offset; mutations require the expected version. Training and model transitions require explicit global root-admin authorization. Operator-unattributed records are visible only to root/global reviewers.

Namespaced records reuse the existing Audit table: NLP_FEEDBACK, NLP_REVIEW_EVENT, NLP_DAILY_METRICS, NLP_MODEL_RUN and NLP_MODEL_EVENT. Message ownership/sequence is checked against the existing Context/Message tables. No existing migration was edited.

## Operating the workflow

`RTC_FEEDBACK_RETAIN_TEXT=0` is the default. Set it to `1` to offer a passenger checkbox; unchecked submissions still retain no question text. `RTC_FEEDBACK_RETENTION_DAYS` defaults to 30 and is bounded to 1–365. Normal conversation history retains its existing shorter session lifetime. Run the authorized retention action regularly; reads/exports also redact expired records they encounter. No background service or external scheduler is required by runtime.

Review and classify the failure before approving it. Data/response/operational corrections should go to their respective maintenance workflow. Training approval requires retained consented text, valid labels and reviewer notes. Use independent conversation groups across train/validation/test and mark provenance truthfully.

Candidate promotion requires the complete active intent taxonomy plus OOS, at least 30 validation and 30 independently collected test records, accepted precision at least 0.95, test accuracy at least 0.90, no previously correct baseline regression, human-reviewed provenance, unchanged approved source versions and artifact checksums. The workflow may train an insufficient candidate for inspection, but it cannot approve/deploy one with failed gates. Synthetic test fixtures demonstrate mechanics, not passenger-model quality.

Artifacts are stored under the already ignored `models/english/nlp/reviewed/{run_id}`. The registry switches by file replacement with a lock/checksum guard. Rollback refuses to overwrite unrelated registry edits. Keep normal local database/registry backups together.

## Executed verification

Final counts, timings and exact commands are recorded in `phase5d-verification.json`; JUnit and Playwright JSON contain individual results. The full backend suite passed **2,307 tests**, with **71 PostgreSQL cases**, zero failures/errors/skips and one deprecation warning. The overlapping Phase 5D focused suite passed **259 tests**, and the full production browser run passed **157 tests**. A final focused browser run passed **4 tests** after the last review UI changes. Ruff, configured Mypy (60 files), ESLint, TypeScript and Vite build passed.

The dedicated local PostgreSQL test database ran on port 55435. SQLite and PostgreSQL scope tests actually executed; PostgreSQL support is not inferred from SQLite results. The full backend suite also covers the earlier dispatcher, data-management, enquiry, conversation and Phase 5C behavior.

`python scripts/verify_phase5d_live.py --offline` copies the local DB to a private temporary SQLite database, blocks all socket connection attempts and DNS before backend import, and runs the conversation/feedback/review/export flow in-process. It passed with SQLite integrity `ok` and zero foreign-key violations. This is application-level deny-all enforcement, not a claim of OS firewall certification. Browser/backend integration servers separately reject external destinations.

A final isolated learning rerun passed all **3 tests**, including actual candidate fitting, evaluation, loading, manual transitions and rollback with socket connection/DNS APIs blocked. Evidence: `phase5d-learning.xml` and `models/benchmarks/phase5d-learning.txt`.

The real main-app acceptance used an explicit labelled DEMO import approved through the existing independent publication workflow. Existing records were preserved; no official timetable, fare, platform or live feed was fabricated. Production model registry/weights were not changed.

## Measured performance

Live main-app DEMO sample (10 turns): last-bus repair detection **0.0098 ms**; focused clarification response **31.63 ms**; empty fare-filter diagnostic probes **117.33 ms**; local feedback write **27.25 ms**. Complete NLP response durations range **31.43–245.25 ms**. The diagnostic sample deliberately includes extra DB probes; ordinary successful turns show zero diagnostic time.

Five isolated production-browser DEMO samples have median send-to-visible-answer latency **208.84 ms**. These are local functional samples while other validation jobs ran, not throughput, load-test or production SLA results. `phase5d-live.json`, `phase5d-offline.json` and `phase5d-performance.json` retain the individual measurements.

## Limits and readiness

- Repair uses bounded deterministic patterns plus the existing classifier; arbitrary English misunderstanding is not claimed solved. Diagnostic probes report uncertainty when the DB does not establish a cause.
- No production model was retrained, approved or deployed. The current installation reports deterministic fallback because no approved active English model meets its existing deployment requirements. Real human-reviewed full-taxonomy data and independent holdouts are still needed to establish any accuracy improvement. This is a corpus/deployment input, not an automatic training step.
- Slot accuracy is measured only when a reviewer supplies comparable canonical corrections. Entity span accuracy remains unmeasured because the existing extractor does not produce comparable predicted character spans. Reviewed intent/answer metrics require actual human labels and may be null.
- Pattern redaction does not detect every possible personal detail. Reviewers must anonymize sensitive text and protect exported files. External copies cannot be recalled by the app.
- Revoking feedback removes managed raw dataset snapshots and blocks future promotion from that source. It does not mathematically remove influence from already trained weights; an administrator must roll back/retrain if required.
- Registry replacement and DB audit commit are separate filesystem/database operations. Normal deployment/rollback is guarded and tested, but crash recovery across that boundary and multi-server model publication are not certified. The synchronous local training action is bounded to 5,000 feedback records.
- One existing Starlette/httpx TestClient deprecation warning remains in backend tests; it does not fail the suite.

**PHASE 5D COMPLETE within these stated local limits.** No production accuracy gain is asserted from DEMO or synthetic evidence.
