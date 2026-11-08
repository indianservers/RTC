# Phase 3B implementation report

PHASE 3B INCOMPLETE. Functional journey planning, APIs, conversational integration, tests and scale measurements are implemented. Remaining constraints below prevent full acceptance or production-readiness claims. No UI, voice, cloud inference or external routing service was introduced. Previous Phase1/2/3A limitations remain in effect.

## Audit and implementation evidence

Requirement-by-requirement status, existing code evidence and remaining gaps are recorded in [phase3b-gap-matrix.json](phase3b-gap-matrix.json). Original request: [phase3b-request.md](phase3b-request.md). Algorithm details: [ROUTING_ALGORITHMS.md](ROUTING_ALGORITHMS.md). API examples/contracts: [JOURNEY_PLANNER.md](JOURNEY_PLANNER.md).

The old connection finder scanned up to100 arbitrary stations, repeatedly queried station pairs, had no per-transfer/cumulative wait bounds, and returned loosely structured paths. Existing calendar, exception, stop-order, cancellation, tariff and observed-departure checks were reused, rather than replaced with fictional graph edges. The route finder now expands reachable timed segments; typed itineraries validate mathematical and transfer invariants. Variant membership and fresh verified destination stop observations are now respected. Existing schema/migrations and the TimetableEngine operating-day API are retained; its compatibility is covered by a regression test.

Added seven ranking modes, deterministic ties, partial-fare handling, optional complete-path Pareto filtering, explicit missed-bus recovery recommendation IDs, fresh-search replanning, vehicle/operator/category/budget/arrival constraints and verified exact-segment seat filtering. Operational trip IDs remain null for calendar-derived schedule occurrences that have no dated Trip row; no operational record is fabricated.

Four typed POST endpoints: /api/v1/journeys/search, /compare, /replan, /missed-bus. Invalid or resource-exceeding searches return422 through existing consistent error handling. Response fields include validated legs/transfers, sources, operational/platform metadata, search bounds/stats and warnings. Compare and replan query local records again; clients cannot supply authoritative itinerary facts.

Connecting/reach conversation enquiries invoke the planner, retain constraints, itinerary IDs, candidate results and ranking, and permit numbered selection. Selection revalidates against fresh DB records. Date/destination/filter changes invalidate old itinerary state. A full dialogue regression covers journey enquiry, selection, cheapest follow-up and tomorrow recalculation. Maximum-transfer/wait phrases and direct-only preferences are supported within the existing deterministic English track.

## Verification

Final full suite: **1,381 passed, one dependency deprecation warning, in110.97seconds**. Log: models/benchmarks/phase3b-final-compatibility-pytest.txt. Targeted routing/dialogue coverage includes252 deterministic ranking/transfer/wait/date combinations plus focused tests and40 deterministic Hypothesis examples. Assertions check real service/stop IDs, date/order/permissions, calendar exceptions and festival additions, cancellations, verified/stale arrival changes, multi-operator connections, unknown GPS/fares, seat-segment freshness, hard vehicle constraints, fare engine equivalence, APIs, replan/recovery, stable ranking, variant membership and compatibility.

Ruff passed across backend/scripts/training; Mypy passed for52 source files across backend and training generation/validation/preparation/English modules. A dependency warning concerns Starlette TestClient/httpx deprecation. SQLite fixtures executed; no PostgreSQL compatibility execution claim is made. Python outbound socket calls are blocked during route tests/benchmarks; loopback socketpair plumbing is permitted for Windows in-process ASGI startup. No OS-level egress firewall isolation was executed.

## Measured scale results

- 100 services, 100 iteration(s): OK; median 11.725 ms; queries 14-14; RSS 82,399,232 bytes.
  Empirical P50 11.725 ms; P95 13.411 ms. P99 31.180 ms.
- 1,000 services, 30 iteration(s): OK; median 64.774 ms; queries 14-14; RSS 90,705,920 bytes.
  Empirical P50 64.774 ms; P95 90.235 ms. P99 omitted for insufficient samples.
- 10,000 services, 3 iteration(s): OK; median 687.925 ms; queries 14-14; RSS 127,426,560 bytes.
- 50,000 services, 1 iteration(s): Service resource limit exceeded; narrow the search; median 121.762 ms; queries 6-6; RSS 116,457,472 bytes.

These are synthetic same-corridor SQLite stress fixtures, not a branching national network, live service feed or concurrent-load benchmark. The100-service run has100 samples;1000 has30,10000 has3,50000 has1. The50000 result is a capacity refusal, not a completed journey search latency. Memory is whole-process RSS, not peak incremental planner allocation. CPU is percent of one logical core; short samples can exceed100% from timing granularity. Warm process/fresh SQLAlchemy Session per search. No model classification or speech is included.

Batching reduced this fixture from1806 queries /~555ms median at100 services and17593 queries /~6594ms at1000 to14 queries per completed fixture. Benchmarks use an explicit10000-service cap and20000-expansion budget; default public search caps are lower. All caches are request-scoped so daily DB modifications are read on subsequent requests. Raw current measurements: models/benchmarks/phase3b-routing.json; earlier benchmark logs preserve the optimization comparison.

## Unfinished requirements and risks

- No DB-defined inter-stand walking/shuttle transfer data exists. Different bus stands never connect implicitly. Per-platform transfer accessibility/time rules are absent.
- Leg-scoped constraints such as AC only until a particular station are unsupported and explicitly clarified. Selected-leg dialogue, broad itinerary reference handling and natural-language missed-bus invocation remain incomplete.
- Recovery requires an explicit missed statement; verified actual-departure-only admission is not implemented. Recovery recommendations are drawn from a returned page capped at100 candidates. Schedule-only time passing does not trigger recovery.
- Replan is a fresh constrained search, not targeted mutation/repair of an old itinerary. Generic verified disruption records are conservatively excluded by default, even if they are merely advisories. Structured individual-stop closures and differentiated suspension semantics need DB contracts. Stale stop observations fall back to schedule without a dedicated per-stop stale status in the itinerary; GPS freshness is separately labelled. Generic DelayEvent metadata alone does not generate stop-specific arrival/departure estimates, so detailed delay recovery requires verified stop-time observations.
- Existing FareEngine does not evaluate concession eligibility, surcharges or through-ticket products. Per-passenger segment tariffs and dated overrides are used, and unknown components remain unknown.
- Same-timezone Indian fixtures were tested. Route-origin timezone conventions, international/DST routes and a separate observation snapshot time require further validation. Current observation cutoff is earliest_departure, including future journey searches; this must not be interpreted as a future live status guarantee.
- Bounded search can truncate before global optimum. No dominance pruning during expansion; optional complete-path Pareto filtering rejects more than2000 candidates. Fifty-thousand-service corridor search is not supported. PostgreSQL query plans, composite freshness/calendar indexes, branching-network performance, concurrency, production data quality and OS firewall isolation remain unverified.
- No independent representative English accuracy or production-readiness conclusion follows from synthetic deterministic tests. Earlier Phase3A session ownership/concurrency limitations persist.

## Reproduce

Install `requirements-test.txt`; run `python -m pytest -q`, `python -m ruff check backend scripts training`, `python -m mypy backend/app training/generation training/validation training/preparation training/english --ignore-missing-imports`, and `python scripts/benchmark_journeys.py`. Benchmark fixtures are temporary; existing local data, migrations and seed records are preserved.
