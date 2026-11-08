# Text-only local capability extension — 8 November 2026

Added 15 of the previous 19 unsupported intents against existing local tables. The taxonomy now exposes 56 PARTIAL handlers and four UNSUPPORTED intents. No handler is falsely labelled complete, and record availability is evaluated per enquiry.

## Added handlers and data boundaries

- BUS_AT_TIME: explicit requested time, with a half-open window from 15 minutes before to 15 minutes after. Clock time follows the selected travel date on follow-up.
- SERVICE_FREQUENCY: counts and gaps from recorded departures within the selected local calendar day. Gaps are not promised periodic headways.
- SPECIAL_DAY_SCHEDULE: existing calendar/exception/cancellation semantics for the requested date; no official holiday calendar is inferred.
- ACCESSIBLE_BUS_AVAILABILITY: only explicitly wheelchair-accessible assigned vehicle types, respecting operator/category/other filters.
- BUS_CAPACITY: dated trip inventory capacity, otherwise assigned active vehicle layout seats/berths. No vacant-seat inference.
- ROUTE_DISTANCE: selected forward unique stops, active variant membership, explicit distance record or recorded cumulative-distance difference. Conflicting explicit records are UNKNOWN.
- DESTINATION_REACHABILITY: reuses the existing JourneyPlanner with a 24-hour horizon, transfer limits and whole-itinerary preferences. Empty/truncated search does not prove global unreachability.
- BOOKING_OPTIONS: active local ReservationChannel name and instructions for the selected operator. It does not make a booking.
- ESTIMATED_ARRIVAL, BUS_DEPARTED_STATUS and BUS_ARRIVED_STATUS: fresh verified TripStopTime observation at the explicit/current station. Effective and recorded timestamps must not be in the future, expiration is exclusive, actual events cannot be future events, and past ETAs are not current estimates. Scheduled timestamps do not substitute for observations. Passenger-visible times use the station timezone.
- PLATFORM_CHANGE: compare the latest current verified assignment with a distinct earlier verified assignment at the same station. Expired current assignments or missing history yield UNKNOWN. Future observations do not mask the current assignment.
- OPERATOR_CONTACT: recorded active operator website only; no operator telephone is inferred from a station contact.
- STATION_NAVIGATION: recorded station address and active bay zones/floors only; no indoor route is invented.
- COMPLAINT_GUIDANCE: active station contacts explicitly typed COMPLAINT; no procedure or current contact availability is inferred.

## Retained unsupported capabilities

BOOKING_STATUS has only a BookingReference identifier/channel link, without passenger authorization or an authoritative status field. CANCELLATION_POLICY, REFUND_POLICY and LUGGAGE_RULES have no applicable policy tables. These four continue to return UNSUPPORTED rather than fabricate answers or repurpose unrelated records.

## Integration and verification

Handlers are isolated in backend/app/local_intents.py and invoked through the existing typed RTCEnquiryEngine. Dialogue uses existing normalization, taxonomy mappings, context, request planning and response rendering. New natural-language patterns preserve the existing “How can I reach…” itinerary flow. Existing database capability definitions are adapted at read time; newly seeded definitions use updated metadata. No data model, migration or runtime dependency was added. The capability metadata file changed; training questions and model artifacts did not.

- Full regression: 1450 passed, 0 failures, 0 errors; JUnit time 128.788 seconds. Includes backend, NLP, dialogue, journey and API tests.
- Final targeted checks after the explicit-station ETA refinement: 64 passed, zero failures; JUnit time 2.585 seconds. This comprises 61 local capability/dialogue checks and three evaluation-integrity checks. Targeted cases overlap the full regression run; these counts must not be added as separate coverage.
- Ruff passed for backend and scripts/evaluate_svm_holdout.py. Mypy passed over 46 app source files with --ignore-missing-imports.
- Covered known and absent records, all four unsupported responses, inactive/expired/unverified/future observations, service/date mismatch, category filters, calendar removals, capacity versus availability, route direction and variant membership, conflicting distances, platform history, clock boundaries, date follow-ups, structured query arguments and grounded English answers.
- Existing Starlette/httpx deprecation warning remains. Tests use temporary synthetic/demo databases; no fake records were added to the active RTC database. Python socket egress is blocked in new tests/evaluation; OS isolation was not tested.

## Frozen English SVM results

The evaluation set was newly agent-authored and frozen before predictions, outside training: three questions per 60 canonical labels plus 20 out-of-scope questions. Exact/near-duplicate audit against local datasets/rules excluded one exact-overlap out-of-scope question; all 180 single-intent questions remained eligible. It is held out from model training but not human-adjudicated or field-collected.

- pilot-v2: 48/180 correct (26.67%), macro F1 across 60 labels 0.2322; 44 raw model classes. Warm prediction median 1.033 ms, p95 1.555 ms. Out-of-scope false accepts: 19/19.
- grouped-60-v1: 117/180 correct (65.00%), macro F1 across 60 labels 0.6408; 60 raw model classes. Warm prediction median 1.034 ms, p95 1.580 ms. Out-of-scope false accepts: 19/19.

The pilot also produced ARRIVALS_AT_STATION, outside the canonical taxonomy; those errors remain in the full confusion matrix. The first integrity check caught that an initially fixed-size confusion matrix omitted these predictions; the matrix now retains extra predicted labels without changing any questions, scoring expectations or models.

No retraining, deployment selection, promotion or classifier-threshold tuning occurred. The out-of-scope result applies to raw forced-choice predict, not the guarded conversation runtime. The 60-class candidate improves on the pilot here but 65% held-out accuracy and absent raw abstention do not establish deployment readiness. Model hashes, source checksums, all predictions, per-class precision/recall/F1 and confusion matrices are in evaluation/english-svm-v1/results.json. Reproduce with the existing English venv; no voice library or TensorFlow is loaded.

## Remaining limitations

56 handlers are partial data integrations, not a claim of comprehensive operator data or unrestricted natural-language understanding. No new live feed, authenticated booking API, policy schema, indoor route map, PostgreSQL verification or graphical UI was introduced. Some questions intentionally clarify missing operator, station, selected service or clock time. Three agent-authored examples per intent are too few for dependable class-level field estimates. The lexical overlap audit cannot rule out all semantic exposure. Larger independently human-labelled evaluation and a separately validated abstention mechanism remain necessary before model approval.

Speech development remains postponed: no speech component was downloaded, installed, loaded or tested by this work. Existing model bytes and the model registry were preserved. The independent simulation laboratory was not changed.
