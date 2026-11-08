# Journey planner usage

Install runtime requirements and optional test tools with `python -m pip install -r requirements-test.txt`. Run the existing migrations and seed commands described in README; no new schema migration is required for these changes.

The four POST endpoints are `/api/v1/journeys/search`, `/api/v1/journeys/compare`, `/api/v1/journeys/replan` and `/api/v1/journeys/missed-bus`. OpenAPI describes JourneyConstraints, typed itineraries, legs, transfers and response metadata. Search accepts origin/destination station IDs, codes, exact names or existing aliases; unresolved/inactive stations return422. Different stands are distinct locations. Compare uses the same search input with a different ranking; replan performs a new DB search. Caller-supplied itinerary facts are never trusted.

Example search body (use real locally present station identifiers and dates):

```json
{"origin":"DEMO0","destination":"DEMO2","earliest_departure":"2026-11-08T19:00:00+05:30","horizon_hours":48,"max_transfers":2,"minimum_transfer_minutes":15,"maximum_wait_minutes":120,"maximum_total_wait_minutes":180,"filters":{"max_fare":"800.00"},"ranking":"EARLIEST_ARRIVAL","limit":20}
```

All example identifiers/data are fictional. Supported rankings: EARLIEST_ARRIVAL, EARLIEST_DEPARTURE, LOWEST_FARE, SHORTEST_DURATION, FEWEST_TRANSFERS, MINIMUM_WAIT and PREFERRED_BUS_CATEGORY. `preferred_category` is a soft name preference; `filters.category` is a hard category constraint. `filters.ac`, sleeper, accessible, operator and other existing enquiry filters apply to every leg. Price/time filters are checked against complete journeys. `require_verified_seats=true` requires fresh available inventory for every exact segment; default false permits unknown availability without claiming seats are confirmed. Passenger count otherwise does not imply a booking or multiply per-passenger fare totals.

A missed-bus body contains `search` (the constraints), `missed_service_id`, `missed_service_date` and `explicitly_missed:true`. The boarding station comes from search.origin. The missed service must have a valid local onward boarding segment. Its scheduled time passing alone is insufficient to invoke recovery. The response includes recommendation journey IDs for next direct, fastest connection, lowest known fare and next compatible service, where found among returned candidates.

Responses include applied filters, search horizon end, candidate/expansion counts, partial-search flag, pagination, stable IDs, Decimal fare strings, separate known subtotal/total status, actual stop IDs, service date and optional actual trip ID, sources, operational/GPS status, departure/arrival kind, platforms and warnings. Freshness uses the request's earliest_departure as the observation cutoff; callers requiring a distinct observation snapshot time need a future contract extension. Future travel planning does not establish future live status. Fare totals are per passenger; concessions/surcharges remain an existing FareEngine limitation.

English conversation: "How can I reach Tirupati?" invokes the journey planner. "Cheapest instead", "Tomorrow" and numbered option selection reuse journey context and re-query records. Explicit maximum-transfer/wait phrases and "don't change buses" are recognized. Leg-scoped category requirements are explicitly rejected with clarification. Detailed selected-leg dialogue and natural-language missed-bus recovery remain unfinished.

Run `python -m pytest -q`, `python -m ruff check backend scripts training`, `python -m mypy backend/app training/generation training/validation training/preparation training/english --ignore-missing-imports` and `python scripts/benchmark_journeys.py`. The benchmark creates/disposes temporary SQLite fixtures. It blocks Python outbound socket calls; API tests allow loopback only for Windows asyncio plumbing. This is not OS-level firewall verification or a PostgreSQL test claim.
