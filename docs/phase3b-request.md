# RTC OFFLINE AI — PHASE 3B
## Advanced Route Planning, Connecting Services & Journey Optimization

You are a senior transport network algorithms engineer, Python backend architect, graph-search specialist and conversational AI engineer.

Continue development in the EXISTING RTC Offline AI repository.

Previous phases:
- Phase 1: Database, services, timetables, fares and enquiry APIs.
- Phase 2: English NLP model, intent recognition and database-grounded responses.
- Phase 3A: Advanced text conversation, multi-turn context, corrections and result selection.

Your objective is to implement a production-grade, offline, time-dependent RTC journey planning engine.

The system must understand direct and connecting bus journeys, optimize routes, handle missed buses, and present practical alternatives.

## ABSOLUTE REQUIREMENTS

- English text only for now.
- No microphone, speech recognition or TTS development.
- No graphical passenger UI.
- No GPT, cloud models or external routing services.
- All journey results must come from local database records.
- No invented transport services, timings, fares or GPS statuses.
- Preserve existing schema and enquiry APIs.
- Inspect the existing repository before implementation.
- Reuse existing route search code where present.
- Do not duplicate working modules.
- Implement real algorithms, not hardcoded demonstration journeys.

---

# 1. AUDIT CURRENT ROUTE CAPABILITIES

Inspect:
- Routes
- Route variants
- Ordered stops
- Recurring services
- Service calendars
- Calendar exceptions
- Trip instances
- Scheduled stop times
- Fare engine
- Direct route finder
- Existing connecting route finder
- Conversation context
- Station aliases
- Operational alerts
- Existing route tests

Identify:
- What is implemented
- What is incomplete
- Incorrect date/time logic
- Inefficient query paths
- Unsupported transfer scenarios
- Missing indexes or constraints

Create an implementation gap matrix.

Do not rewrite correct existing services unnecessarily.

---

# 2. TIME-DEPENDENT TRANSPORT GRAPH

Implement a journey planner using a time-dependent directed network.

Important:

A bus route is not merely a connection between cities.

A valid journey requires:
- Specific trip
- Boarding stop
- Alighting stop
- Stop order
- Boarding permission
- Alighting permission
- Service operating date
- Actual scheduled stop times
- Transfer feasibility
- Service cancellation status

Use actual trip stop times or generate validated dated instances from recurring service calendars.

Do not treat all edges as available at every time.

Build a configurable search horizon, such as the next 48 hours.

Prevent unbounded database queries or graph expansion.

---

# 3. DIRECT JOURNEY SEARCH

Implement or improve:

find_direct_journeys()

Input:
- Origin
- Destination
- Earliest departure
- Latest departure, optional
- Arrival deadline, optional
- Bus category filters
- Operator filters
- Accessibility requirements
- Passenger count, optional

Validate:
- Boarding stop precedes alighting stop.
- Both stops belong to the same trip.
- Boarding and alighting are permitted.
- Trip operates on the selected date.
- Trip is not cancelled.
- Passenger's segment is valid.
- Timing requirements are satisfied.

Support boarding at intermediate stops.

Return complete stop-to-stop journey details.

---

# 4. CONNECTING JOURNEY SEARCH

Implement:

find_connecting_journeys()

Support:
- One transfer
- Two transfers
- Configurable maximum transfers
- Cross-midnight transfers
- Multiple operators
- Intermediate boarding
- Intermediate alighting
- Different service categories
- Arrival deadline
- Departure time window
- Accessibility constraints
- Bounded total waiting time

Use a suitable bounded algorithm:
- Time-dependent Dijkstra
- Connection Scan Algorithm
- Multi-criteria label-setting

Choose according to the existing database design and benchmark evidence.

Document the chosen algorithm and its trade-offs.

Do not use ordinary shortest-path algorithms over an untimed station graph when service departure times matter.

## Transfer rules

Require:
- First journey arrives before connecting departure.
- Minimum transfer time is satisfied.
- Maximum transfer waiting time is respected.
- Both trips operate on their respective service dates.
- The transfer station is valid.
- Platform/boarding station transfers are feasible.

If changing between different bus stands in the same city:
- Require explicit local transfer time and transport assumptions.
- Do not treat two bus stands as the same physical location.
- Do not silently assume zero-minute transfer time.

Never invent a local taxi/shuttle connection.

Exclude impossible transfers.

---

# 5. JOURNEY DATA CONTRACT

Return a structured itinerary.

Example:

{
  "journey_id": "generated-stable-id",
  "origin": "Vijayawada PNBS",
  "destination": "Tirumala",
  "departure_at": "2026-11-08T20:00:00+05:30",
  "arrival_at": "2026-11-09T06:30:00+05:30",
  "transfer_count": 1,
  "total_duration_minutes": 630,
  "total_wait_minutes": 40,
  "fare_status": "KNOWN",
  "total_fare": 780,
  "currency": "INR",
  "source": "DEMO",
  "legs": [
    {
      "service_id": "DEMO-101",
      "origin": "Vijayawada PNBS",
      "destination": "Tirupati",
      "boarding_at": "2026-11-08T20:00:00+05:30",
      "alighting_at": "2026-11-09T05:30:00+05:30",
      "category": "Super Luxury",
      "fare": 680
    },
    {
      "service_id": "DEMO-205",
      "origin": "Tirupati",
      "destination": "Tirumala",
      "boarding_at": "2026-11-09T06:10:00+05:30",
      "alighting_at": "2026-11-09T06:30:00+05:30",
      "category": "Express",
      "fare": 100
    }
  ]
}

All example IDs, timings, fares and durations are fictional.

Validate totals programmatically.

Never derive total fare by treating unknown components as zero.

---

# 6. MULTI-CRITERIA JOURNEY OPTIMIZATION

Implement these ranking modes:

EARLIEST_ARRIVAL
EARLIEST_DEPARTURE
LOWEST_FARE
SHORTEST_DURATION
FEWEST_TRANSFERS
MINIMUM_WAIT
PREFERRED_BUS_CATEGORY

Support Pareto-optimal candidates where practical.

Do not assume one itinerary is universally best.

Different passengers prioritize different outcomes.

Ranking requirements:
- Compare journeys satisfying the same origin/destination/date constraints.
- Exclude unknown fares from verified cheapest rankings.
- Exclude unknown arrival times from fastest rankings.
- Respect user-specified filters.
- Preserve stable ordering for equal scores.

Provide deterministic tie-breaking rules.

---

# 7. MISSED-BUS RECOVERY

Implement:

find_alternatives_after_missed_bus()

Inputs:
- Missed trip
- Boarding station
- Current or specified time
- Destination
- Passenger preferences

Return:
- Next direct service
- Fastest valid connection
- Lowest known fare alternative
- Next available compatible service

Do not assume a passenger missed the bus merely because its scheduled departure time has passed.

Use explicit user statement or verified actual departure information.

For example:

"I missed the 8 PM Vizag bus."

The planner must search valid departures after the specified missed service/time.

---

# 8. DISRUPTION-AWARE REPLANNING

Handle:
- Cancelled trips
- Delayed departure
- Delayed arrival
- Missed connection due to verified delay
- Platform change
- Unavailable boarding stop
- Temporary route suspension
- Stale operational data

Implement:

replan_journey()

Only use verified operational changes where available.

If data is stale, distinguish confirmed information from uncertainty.

Do not fabricate an estimated delay.

---

# 9. FARE-AWARE ROUTING

Reuse the existing FareEngine.

Calculate fare per journey leg using:
- Origin stop
- Destination stop
- Operator
- Category
- Travel date
- Fare rule
- Applicable surcharges
- Valid concessions when eligibility is provided

Use Decimal for money.

Support:
- Per-leg fare breakdown
- Total known fare
- Partial fare availability
- Fare comparison
- Cheapest route among known total fares

If one leg has unknown fare, total journey fare must be UNKNOWN or PARTIAL.

Do not assume that two-leg journeys receive a through-ticket discount unless such a fare product exists in the database.

---

# 10. PASSENGER CONSTRAINTS

Support:

"Only AC buses."

"Maximum one transfer."

"Under 800 rupees."

"Reach by 8 AM tomorrow."

"Leave after 9 PM."

"No sleeper."

"Don't change buses."

"Prefer Super Luxury."

"Wheelchair-accessible services only."

"Maximum waiting time 30 minutes."

Use a typed constraint object.

Distinguish hard requirements from soft preferences.

Hard constraints must never be violated for a recommended itinerary.

If no matching journey exists, explain which filters prevented results and offer relaxation options without silently changing them.

---

# 11. CONVERSATIONAL INTEGRATION

Reuse the existing Phase 3A conversation state.

Examples:

Passenger:
"How can I reach Tirumala tonight?"

Engine:
Returns direct or connecting journeys.

Passenger:
"Show the fastest."

Engine:
Ranks the same eligible journeys by arrival.

Passenger:
"Cheapest instead."

Engine:
Re-ranks by known total fare.

Passenger:
"Only AC until Tirupati."

Engine:
Applies the specified constraint to the correct journey leg.

Passenger:
"What about tomorrow?"

Engine:
Recalculates the journey for the new date.

Passenger:
"Second option."

Engine:
Selects the second displayed itinerary.

Maintain:
- Original enquiry
- Active constraints
- Candidate itineraries
- Selected itinerary
- Selected leg
- Ranking preference
- Clarification state

When date or destination changes, invalidate old journey results and recalculate.

Do not reuse stale trip IDs.

---

# 12. ROUTE COMPARISON EXPLANATIONS

Provide short, factual descriptions.

Examples:

"Option 1 arrives earlier but requires one transfer at Tirupati."

"Option 2 is cheaper by ₹120 and has no transfers."

"The direct service departs later but avoids changing buses."

Only make comparisons supported by known values.

Do not invent reasons for delays, traffic conditions or operational restrictions.

---

# 13. REST API

Reuse or extend existing routes:

POST /api/v1/journeys/search
POST /api/v1/journeys/compare
POST /api/v1/journeys/replan
POST /api/v1/journeys/missed-bus

Return:
- Applied filters
- Candidate itineraries
- Journey legs
- Transfer details
- Fare status
- Operational status
- Data source
- Freshness
- Warnings
- Search horizon
- Pagination or result limits

Do not duplicate the existing enquiry API business logic.

Validate resource limits and input values.

---

# 14. PERFORMANCE OPTIMIZATION

Benchmark search on synthetic networks with:
- 100 services
- 1,000 services
- 10,000 services
- 50,000 services where resources permit

Measure:
- Search latency
- Number of candidate connections
- Memory usage
- Database query count
- P50/P95/P99 latency

Use:
- Indexed stop-times
- Bounded date windows
- Pruned transfer expansions
- Dominance filtering
- Cached static route structure where justified

Avoid loading an entire national network into memory for each enquiry.

Do not introduce external routing APIs.

---

# 15. COMPREHENSIVE TESTING

Create at least 250 deterministic journey-planning scenarios.

Cover:

1. Direct route
2. One transfer
3. Two transfers
4. Intermediate boarding
5. Intermediate alighting
6. Wrong stop direction
7. Same-station transfer
8. Different-bus-stand transfer
9. Minimum transfer time
10. Maximum waiting time
11. Cross-midnight journey
12. Calendar exceptions
13. Festival extra services
14. Cancelled service
15. Delayed first leg
16. Missed connection
17. Unknown GPS
18. Stale departure estimate
19. Cheapest known fare
20. Partially unknown fare
21. Arrival deadline
22. AC-only filter
23. Sleeper-only filter
24. Accessibility requirements
25. Missed-bus recovery
26. Route replanning
27. Same-origin/destination validation
28. Multi-operator connections
29. Contradictory constraints
30. No route available

Include property-based tests for itinerary invariants.

Verify:
- Every leg uses a valid trip.
- Stops are in the correct order.
- Transfers are physically and temporally feasible.
- Cancellations are respected.
- Dates and timezones are valid.
- Fare totals are mathematically correct where known.
- Unknown data remains unknown.
- Ranking is deterministic.

---

# 16. FILE STRUCTURE

Extend existing modules rather than duplicating them.

Suggested structure:

backend/app/journey/
  planner.py
  graph_builder.py
  connection_search.py
  direct_search.py
  ranking.py
  fare_aggregation.py
  replan.py
  constraints.py
  schemas.py

backend/app/api/
  journeys.py

backend/tests/journey/
  test_direct.py
  test_connections.py
  test_timezones.py
  test_fares.py
  test_replanning.py
  test_constraints.py

docs/
  JOURNEY_PLANNER.md
  ROUTING_ALGORITHMS.md
  PHASE_3B_REPORT.md

Adapt names to actual repository organization.

---

# 17. ACCEPTANCE CRITERIA

Phase 3B is complete only when:

1. Direct services are found correctly.
2. One- and two-transfer journeys work.
3. Intermediate boarding and alighting work.
4. Calendar rules and overnight services work.
5. Transfer feasibility is validated.
6. Cheapest/fastest/fewest-transfer rankings work.
7. Unknown fares do not distort rankings.
8. Missed-bus alternatives work.
9. Disruption-aware replanning works with available data.
10. The NLP conversation manager can invoke the planner.
11. APIs return validated itineraries.
12. Automated tests pass.
13. Offline execution is verified.
14. Existing Phase 1–3A functionality remains operational.

Do not claim production readiness on synthetic fixtures alone.

---

# 18. FINAL DELIVERABLES

Deliver:

1. Time-dependent journey planner.
2. Direct and connecting route search.
3. Multi-criteria ranking.
4. Missed-bus recovery.
5. Disruption-aware replanning.
6. Fare-aware journey comparison.
7. Conversation integration.
8. Journey planning APIs.
9. Automated tests.
10. Performance benchmarks.
11. Algorithm documentation.
12. Phase 3B completion report.

Run real tests and benchmarks.

Do not stop at architecture diagrams, TODOs or placeholder functions.

Do not implement UI or voice.

Report actual test results, measured latency and unresolved limitations.

Begin implementation in the existing repository immediately.