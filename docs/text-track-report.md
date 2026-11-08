# English text conversation track — execution report

Executed 8 November 2026 (Asia/Kolkata). Text terminal functionality is delivered; full high-accuracy NLP and all backend capabilities are not complete.

## Delivered

- Terminal entry point: `python -m app.cli.chat` with `PYTHONPATH=backend`; independent/resumable session IDs, operator/boarding defaults and all six requested slash commands.
- Existing NLP and enquiry APIs reused: normalization, database lexicon extraction, rule/candidate gate, context merge, typed EnquiryRequest, local database lookup and English response formatting. No SQL is generated from language output.
- Fifteen-minute sliding session expiry; destination/date/AC/category retention and replacement, morning/afternoon/evening/night windows, explicit before/after times, contradictory-filter clarification, filter clearing, numbered service selection and station switching.
- Route/date/filter changes invalidate selection. Invalid input rolls back partial context edits. Multi-intent requests execute up to three enquiries; earlier results can supply service IDs to dependent questions.
- Demo provenance is displayed, including empty results from an all-demo service catalogue. Missing prices, seats, platforms and operational reports remain unknown. Inactive fares no longer apply. Selected-service enquiries now constrain journey rows to the structured selected service ID.
- Debug mode is opt-in and includes normalized input, intents, rule score or model state, entities, context, structured queries, function invoked, matching service IDs, provenance/freshness fields, formatter branch and timings. No debug trace is returned by default.

## Verification

- Full backend unit/NLP/dialogue/API regression suite: 490 passed, 0 failures, 0 errors; JUnit duration 54.180 seconds.
- New text dialogue file: 315 tests, including 240 parameterized conversations (12 patterns over 20 seeded routes), 60 canonical intent mappings, clarifications, unknown fares, reset, station changes, unknown destination, midnight arrival, contradictions and API debug opt-in. These are agent-authored functional acceptance checks, not independent model-quality measurements.
- Ruff: `python -m ruff check backend scripts/benchmark_text.py` passed. Mypy: `python -m mypy backend/app --ignore-missing-imports` passed across 35 source files.
- Terminal subprocess smoke exercised /help, /context, /debug, /station, /reset and /exit using a temporary demo DB with Python socket egress denied; grounded fare and debug output assertions passed.
- The requested five-turn Nellore → AC → cheapest → tomorrow morning → Tirupati chain was executed against a seeded database; destination/date/filter preservation and selection invalidation assertions passed.
- Python socket connection attempts are blocked in new dialogue tests; the benchmark and CLI smoke enforce the existing socket audit guard. OS-level network isolation was not exercised.
- Existing Starlette/httpx deprecation warning remains; dependencies were not changed.

## Actual measured performance

100 warm repetitions of “Next bus to Guntur and ticket fare” against a temporary SQLite demonstration database with canonical taxonomy seeded. Debug and tracemalloc are enabled; these add overhead. Database initialization is outside timed requests. Component timings are not disjoint totals because context/rule/database-content work also occurs around them.

- Intent/rule inference including registry mapping: median 11.245 ms; p95 16.642 ms.
- Entity extraction: median 4.048 ms; p95 6.429 ms.
- Typed database enquiry including label enrichment: median 167.228 ms; p95 210.128 ms.
- End-to-end response: median 204.303 ms; p95 255.722 ms.
- Process working set: 80,474,112 bytes; peak working set: 89,759,744 bytes. Python traced peak: 6,800,392 bytes.

## Local model status

The existing pilot-v2 SVM artifact loaded successfully and produced NEXT_BUS, TICKET_FARE, BUS_PLATFORM and SEAT_AVAILABILITY for the four recorded probe questions. Model load took 1.339 seconds; 100 warm single-question predictions had median 1.075 ms and p95 1.700 ms. The probe ran in the existing English environment with socket egress blocked. Artifact SHA-256 and outputs are recorded in text-candidate-probe.json.

The model is CANDIDATE, not an approved runtime model. Runtime EnglishIntentModel returns NOT_READY and deterministic rules remain active. No model was promoted, retrained or tuned. Successful inference on four questions is not an independent accuracy score. No claim of high general-English accuracy or full 60-label learned-model coverage is made.

## Remaining gaps and capability boundaries

All 60 canonical entries have recognition/mapping checks. Exactly 41 map to partial existing handlers; 19 return UNSUPPORTED: BUS_AT_TIME, SERVICE_FREQUENCY, SPECIAL_DAY_SCHEDULE, ACCESSIBLE_BUS_AVAILABILITY, BUS_CAPACITY, ROUTE_DISTANCE, DESTINATION_REACHABILITY, BOOKING_OPTIONS, BOOKING_STATUS, CANCELLATION_POLICY, REFUND_POLICY, LUGGAGE_RULES, ESTIMATED_ARRIVAL, BUS_DEPARTED_STATUS, BUS_ARRIVED_STATUS, PLATFORM_CHANGE, OPERATOR_CONTACT, STATION_NAVIGATION and COMPLAINT_GUIDANCE. Recognition does not implement a missing booking, fare-policy, navigation or live-data integration.

Free-form English coverage remains limited by the local lexicon and rule patterns; exact taxonomy examples/canonical names are recognized, but this is not broad paraphrase validation. Relative date/time support is bounded to implemented forms, not arbitrary natural-language date ranges. Up to three simultaneous intents and five displayed choices are supported. The seeded data does not supply realistic inventory, operational freshness or comprehensive station facilities. Selected trip lookup requires a unique local trip for the service/date. Complete category/amenity policy and connection-specific constraints remain dependent on the existing partial enquiry backend. PostgreSQL, concurrency under multiple terminal processes and real operator data were not validated.

## Scope preservation

No voice component was downloaded, installed, loaded or tested by this track. Existing speech code and model files were preserved. No graphical UI, model registry change, training dataset change or simulation-lab change was made. Existing additive taxonomy work was consumed through its database API; this track added no migration. All new evaluation cases stay separate from training. CLI smoke added ordinary conversation records when exercised against the configured demonstration DB; later smoke and benchmarks used temporary databases.

Artifacts: text-tests.xml, text-benchmark.json, text-candidate-probe.json and text-capabilities.json in this docs directory. README contains execution/setup commands.
