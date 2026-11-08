# Phase 3A — advanced English text dialogue

Status: PHASE 3A INCOMPLETE. Implemented and regression-tested improvements exist, but the full requested breadth and deployment security are not complete. No speech model, training, graphical UI or Phase 3B work was added.

## Implementation audit and changes

- Existing trained candidates are preserved and unapproved because their measured synthetic holdout quality remains poor. DB deterministic fallback stays active. No model readiness claim changed.
- Existing registry, extractor, orchestrator, templates and CLI were extended rather than replaced. Existing migrations and API request fields remain compatible.
- New ConversationState/JourneyPreferences validate the existing JSON state. Revisions, activity, pending questions, slot sources/origins, selected-route references and explicit/system selection distinction are recorded. Inferred candidate values stay separate until confirmed.
- ContextUpdateEngine supports SET_SLOT, REPLACE_SLOT, CLEAR_SLOT, CONFIRM_SLOT, REJECT_SLOT, RESET_CONTEXT, SELECT_RESULT, REFINE_RESULTS and SWITCH_INTENT. Extracted slots, result selection and price-limit removal use explicit operations; some older policy branches still perform direct updates.
- Dependency invalidation removes stale trip/fare/platform/result references when origin/destination/category/date constraints change. Same recurring bus tomorrow retains a service reference but re-queries the new operating date and does not carry a stale trip ID.
- Result IDs derive from service/date/departure/arrival. Ordinal selection and list refinement preserve remaining IDs. Cheaper/fastest/previous/current-reference helpers reject ties, missing prices/times or unavailable previous lists. Remove-first and any-other operate on current cached results; they are not unrestricted new route searches.
- ExecutionPlanner reorders primary journeys before dependent fare/arrival projections and reuses their DB rows within the same request. A test verifies NEXT_BUS plus fare uses one enquiry-engine call rather than two and does not replace the whole result list with the dependent projection. Operational status still queries its own fresh records.
- TemporalParser uses an injected station-local aware clock, explicit dates/relative days, after/before times, around ±15-minute windows, the next 1–24 hours and midnight. Original text/resolution metadata are retained. Explicit clock filters inherit an already selected travel date; same-time tomorrow re-bases a known window. Arrival-before/after constraints are distinct from departure bounds. Bare ambiguous clock expressions ask AM/PM instead of assuming.
- Passenger counts support English one–ten and numeric counts, skip explicitly negated counts, and clarify contradictions or values outside 1–100.

## API and privacy

Existing message/reset contracts remain. Responses add context_changes; GET /api/v1/conversation/{session_id}/context provides owner-bound context. Clients can send an owner_token of 32–256 characters with messages/reset; a SHA-256 hash is stored, tokens/hashes are omitted from public context/debug, and wrong/missing tokens are denied for bound sessions. Context GET uses Authorization: Bearer <owner_token>. Bound resets retain the binding.

Legacy clients without a token remain random-session-ID capability based for compatibility; the new context endpoint does not expose those unbound legacy contexts. Universal mandatory ownership would require a coordinated client migration. Session expiry is logical; old database rows are not physically purged by this change. Same-session conflicting updates are not protected with database optimistic-lock revision checks.

## CLI

python -m app.cli.chat --station DEMO0 --operator DEMO supports /help /reset /context /results /select N /history /debug /station /exit. UTF-8 output is configured when supported. History is capped at 50 entries in memory. RTC_SESSION_TOKEN can provide the owner token for a bound session. Typed CLI, result listing, selection and history were smoke-tested against the local DEMO database. No graphical UI or microphone was used.

## Tests

Added 300 parameterized scenarios across 20 seeded routes, five action sequences and 2/5/10 turns, with state, revision, actual structured query, real service ID and route-stop assertions. Additional tests cover owner binding, dependencies, unconfirmed candidates, temporal boundaries, tie clarification, planner reuse, stable list IDs, same-service revalidation and negated passenger counts. These are synthetic regression fixtures, not calibrated intent/entity/response accuracy on a reviewed passenger corpus. Original tests were retained. Executed full suite: 1,109 passed, one Starlette/httpx deprecation warning, in 102.51 seconds. Ruff passed for backend, scripts and training. Mypy passed for 51 source files across the backend and training generation/validation/preparation/English modules. Full log: models/benchmarks/phase3a-final-pytest.txt.

## Measured benchmark

100 iterations of one happy-path enquiry with persisted in-transaction state on an in-memory SQLite 100-service fictional fixture, fixed clock and Python socket blocking. No active learned classifier or audio is included.

- total_ms: P50 22.166 ms, P95 29.305 ms, P99 50.391 ms (100 samples).
- intent_inference_ms: P50 1.874 ms, P95 3.222 ms, P99 5.515 ms (100 samples).
- context_update_ms: P50 0.260 ms, P95 0.431 ms, P99 0.449 ms (100 samples).
- database_lookup_ms: P50 14.817 ms, P95 20.602 ms, P99 23.513 ms (100 samples).

Process RSS: 84066304 bytes. Average CPU: 99.81% of one core. Hardware identifier: Intel64 Family 6 Model 151 Stepping 5, GenuineIntel.
Context stage includes station resolution; memory is process RSS, not model-specific peak. This is a happy-path microbenchmark, not passenger accuracy or concurrent-load certification.

## Remaining requirements

- Category-specific contextual comparisons, general next-three pagination and broad there/that-Express references are not fully implemented. Cached-reference ranking uses the current session result list; changes to source DB records do not proactively invalidate cached lists.
- Multi-intent planning reuses fare/arrival facts but is not a general dependency optimizer across all sixty intents. Existing backend coverage remains 41 partial/19 unsupported.
- Full AM/PM disambiguation in inherited conversational clocks, negated date expressions, all same-time/same-service variants, per-operator time-period configuration and globally correct cross-timezone/arrival-day searches require more work.
- Some generic clarification/rendering copy still resides in existing policy code. Operational values remain database-derived, but complete DB-driven copy management is unfinished.
- Universal owner enforcement, same-session update conflicts, physical retention cleanup, PostgreSQL execution, representative accuracy evaluation, concurrent-load latency and OS-level network isolation remain unverified/incomplete.

## Reproduction

python -m pytest -q; python -m ruff check backend scripts training; python -m mypy backend/app training/generation training/validation training/preparation training/english --ignore-missing-imports; python scripts/benchmark_phase3a.py. Benchmark JSON: models/benchmarks/phase3a-latency.json. No phase completion or production-readiness claim follows from passing regression fixtures.