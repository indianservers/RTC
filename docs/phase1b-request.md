# RTC OFFLINE AI — PHASE 1B
## Complete Core Enquiry, Search & Route Intelligence Engine

You are a senior transport systems architect, Python backend engineer, algorithm specialist and database optimization expert.

Continue development in the existing RTC Offline AI repository.

Phase 1A established the database architecture. Your task is to develop the complete operational enquiry engine using the existing database.

Do not recreate existing tables, models, routes, APIs or migrations unless necessary.

Inspect the actual repository before modifying anything.

IMPORTANT:
- No frontend or UI in this phase.
- No AI model training.
- No cloud services or external API calls.
- No GPT or generative models.
- No fabricated answers.
- All enquiry results must come from the local database.
- Complete the implementation, not just the architecture.

---

# 1. BUILD A CENTRAL ENQUIRY ENGINE

Create one central service:

`RTCEnquiryEngine`

It must support structured input and return normalized results.

Example:

```python
engine.enquire(
    intent="NEXT_BUS",
    origin="Vijayawada",
    destination="Tirupati",
    travel_date="2026-11-08",
    filters={
        "ac": True,
        "sleeper": False,
        "category": "SUPER_LUXURY"
    }
)
```

Support both station IDs and aliases.

The engine must be independent of:
- Frontend
- Voice recognition
- AI model
- Transport operator
- Language

Expose reusable query methods that Phase 2 NLP and Phase 3 voice systems can invoke.

# 2. IMPLEMENT AT LEAST 40 ENQUIRY INTENTS

Group the enquiry engine into the following functional areas.

## A. Departure and Arrival Enquiries

1. NEXT_BUS
2. FIRST_BUS
3. LAST_BUS
4. BUSES_BETWEEN
5. DEPARTURES_AFTER
6. DEPARTURES_BEFORE
7. ARRIVALS_AT_STATION
8. ARRIVAL_TIME
9. JOURNEY_DURATION
10. BUSES_OPERATING_TODAY

Handle date boundaries and services crossing midnight.

For example:

"Tomorrow morning first bus to Tirupati."

Tomorrow refers to the station-local calendar date.

"Today's last bus" must use a configurable operating-day boundary and must never accidentally select tomorrow's last bus.

## B. Bus Type & Amenity Enquiries

11. AVAILABLE_BUS_TYPES
12. AC_BUS_AVAILABILITY
13. NON_AC_AVAILABILITY
14. SLEEPER_BUS_AVAILABILITY
15. SEATER_BUS_AVAILABILITY
16. BUS_AMENITIES
17. SERVICE_CATEGORY_COMPARISON
18. ELECTRIC_BUS_AVAILABILITY

Filters must combine correctly.

Example:

"Show only AC sleeper services leaving after 8 PM."

The system must return trips satisfying all applicable filters.

Do not assume that every bus belonging to a branded category has identical facilities.

## C. Route and Stop Enquiries

19. DIRECT_BUS_AVAILABILITY
20. ROUTE_STOPS
21. BUS_VIA_LOCATION
22. INTERMEDIATE_STOP
23. BOARDING_POINT
24. ALIGHTING_POINT
25. CONNECTING_BUSES
26. ALTERNATIVE_ROUTES

The engine must support boarding and alighting at intermediate stops.

Validate boarding/alighting permissions and stop sequence.

Do not offer connections that depart before the passenger arrives.

## D. Fare and Availability

27. TICKET_FARE
28. CHEAPEST_BUS
29. FASTEST_BUS
30. SEAT_AVAILABILITY
31. RESERVATION_SUPPORTED
32. CONCESSION_ELIGIBILITY
33. FARE_COMPARISON
34. LUGGAGE_RULES

Fare calculations must respect:
- Travel date
- Fare validity
- Operator
- Bus category
- Boarding and alighting stage
- Relevant surcharge
- Passenger concession rules

Never treat unavailable fare information as zero fare.

## E. Operational Enquiries

35. BUS_LIVE_STATUS
36. BUS_DELAY
37. BUS_CANCELLATION
38. BUS_PLATFORM
39. SERVICE_DISRUPTION
40. STATION_FACILITIES

Where verified real-time information is unavailable, return structured UNKNOWN or NOT_AVAILABLE status.

Never claim that a scheduled departure is a live-confirmed arrival.

Additionally implement:
- LOST_PROPERTY_CONTACT
- STATION_HELPDESK
- OPERATOR_CONTACT
- SERVICE_NUMBER_LOOKUP

# 3. ADVANCED SEARCH ENGINE

Build a search service capable of combining:

- Origin
- Destination
- Date
- Time window
- Operator
- Service category
- AC preference
- Sleeper preference
- Electric vehicle preference
- Boarding point
- Intermediate stop
- Minimum/maximum fare
- Maximum journey duration
- Reservation eligibility
- Seat availability
- Accessibility requirements

Support filtering, sorting, pagination and result limits.

Sort options:
- Earliest departure
- Earliest arrival
- Lowest fare
- Shortest journey
- Fewest transfers
- Service category
- Operator

Do not silently interpret missing values as zero or false.

A service with unknown fare must not be ranked as the cheapest.

# 4. STATION & ENTITY RESOLUTION

Create a reusable resolver:

`StationResolver`

Accept:
- Canonical names
- Common names
- Telugu names
- Tanglish transliterations
- Abbreviations
- Station codes
- City names

Examples:
- Bezawada → Vijayawada
- Vizag → Visakhapatnam
- Rajahmundry → Rajamahendravaram
- Tirupathi → Tirupati

Differentiate:
- City-level destination
- Specific bus station
- Nearby transit stop
- Similar names

For a city-level enquiry, search eligible stations serving that city.

If an alias matches multiple candidates, return DISAMBIGUATION_REQUIRED with candidates.

Never silently select an ambiguous station.

Use indexed normalized aliases and bounded fuzzy matching.

# 5. ROUTE INTELLIGENCE

Implement two route search methods.

## Direct service search

Search trips where:
- Origin is a permitted boarding stop.
- Destination is a later permitted alighting stop.
- Service runs on the requested date.
- Service is not cancelled.
- Date/time filters are satisfied.

A service must not be excluded merely because the passenger is boarding somewhere other than the service's original terminal.

## Connecting service search

Implement bounded time-dependent route search.

Requirements:
- Maximum transfers configurable; default 2.
- Minimum connection time configurable.
- Service calendars must be respected.
- Account for cross-midnight and next-day transfers.
- Prevent cycles and duplicate itineraries.
- Respect boarding and alighting permissions.
- Reject impossible transfer windows.
- Include transfer station and waiting duration.
- Limit candidate expansion for predictable CPU/memory consumption.

Return candidate itineraries with:
- Legs
- Transfer stations
- Departure and arrival
- Travel duration
- Waiting duration
- Total journey duration
- Fare breakdown where known
- Availability information where known

Prioritize correctness and explainability over complex ML optimization.

# 6. TIMETABLE CALCULATION ENGINE

Create:

`TimetableEngine`

Handle:
- Daily services
- Selected weekdays
- Calendar exceptions
- Extra services
- Temporary suspensions
- Overnight services
- Cross-midnight stop times
- Different operating-day definitions
- Local timezones
- Platform schedule changes
- Estimated/actual time overrides

Use timezone-aware datetimes internally.

Store and retain both the operating service date and exact departure timestamp.

Explicitly define whether "last bus today" refers to the calendar day or an operator-defined service day, and allow callers to choose.

Avoid datetime comparisons between naive and timezone-aware objects.

# 7. FARE INTELLIGENCE

Create:

`FareEngine`

Support:
- Fixed route fares
- Stop-to-stop fares
- Stage-based fares
- Distance-based fares
- Operator-specific tariffs
- Category-specific tariffs
- Date-effective pricing
- Trip-specific overrides
- Applicable surcharges
- Concession eligibility

Use Decimal throughout.

Return a breakdown:

```json
{
  "base_fare": 400,
  "surcharge": 25,
  "discount": 0,
  "total": 425,
  "currency": "INR",
  "fare_status": "KNOWN",
  "source": "DEMO"
}
```

Example values are fictional.

When fare data is missing, report UNKNOWN and identify the missing component if possible.

Do not infer concession eligibility from language, age assumptions or passenger appearance.

# 8. OPERATIONAL STATUS ENGINE

Create:

`OperationalStatusEngine`

Determine:
- Scheduled status
- Delayed status
- Cancelled status
- Arrived status
- Departed status
- Platform assignment
- Estimated arrival/departure
- Last verified timestamp

Implement freshness thresholds.

For example:
- GPS older than configured threshold → STALE
- No GPS record → UNKNOWN
- Scheduled time exists but no GPS → SCHEDULED_ONLY

Do not infer that a bus has arrived solely because its scheduled arrival time is in the past.

Use authoritative local trip events when present.

# 9. RESULTS AND RESPONSE CONTRACTS

Return consistent structured objects.

Include:
- Intent code
- Query interpretation
- Matched stations
- Applied filters
- Matching services
- Timetable details
- Fare details
- Operational data
- Data source
- Freshness status
- Warnings
- Confidence or ambiguity information
- Pagination metadata

Use explicit enums such as:
- KNOWN
- UNKNOWN
- STALE
- UNAVAILABLE
- NOT_APPLICABLE
- DEMO

Do not overload null, zero and false.

All query results must be serializable to JSON and easy for an NLP response-template engine to consume.

# 10. QUERY VALIDATION

Reject or clarify:
- Origin equals destination when not supported.
- Invalid dates.
- Nonexistent station IDs.
- Unsupported bus categories.
- Negative passenger counts.
- Contradictory filters.
- Excessively broad searches.
- Invalid transfer limits.
- Invalid time windows.

Use structured errors rather than unhandled exceptions.

# 11. REST API

Expose the engine through /api/v1/enquiry endpoints.

Provide:
- Unified enquiry endpoint
- Direct specialized endpoints
- Station resolution endpoint
- Bus-category lookup
- Route lookup
- Timetable lookup
- Fare lookup
- Status lookup

Every endpoint must use the same underlying enquiry service.

Do not duplicate business logic in API route handlers.

Include Pydantic request/response schemas and OpenAPI examples.

# 12. PERFORMANCE

Optimize the database query layer.

Avoid scanning every service for every request.

Use:
- Indexed station references
- Calendar candidate filtering
- Efficient stop-sequence joins
- Indexed departure retrieval
- Bounded graph traversal
- Efficient operator/category predicates

Add benchmark scenarios with at least:
- 100 services
- 1,000 services
- 10,000 synthetic services

Measure:
- Average query latency
- P50
- P95
- P99
- Memory usage
- Database query count

Use fixed data and hardware settings for reproducible comparisons.

Do not introduce Redis unless actual measurements justify it.

# 13. TESTING

Implement comprehensive tests covering:

1. Next bus from origin
2. Next bus from intermediate stop
3. Last bus at midnight
4. First bus tomorrow
5. Overnight journeys
6. Weekly service calendars
7. Added and removed service exceptions
8. Direct route search
9. One-transfer journeys
10. Two-transfer journeys
11. Missed connections
12. Wrong-direction travel
13. AC/sleeper filters
14. Unknown category
15. Cheapest bus with missing fares
16. Fare validity expiration
17. Concession rules
18. Unknown seat availability
19. Cancellation
20. Verified delay
21. Stale GPS
22. Platform reassignment
23. Multilingual station aliases
24. Ambiguous city names
25. Cross-operator journeys
26. Empty results
27. Invalid filters
28. Duplicate service numbers
29. Fuzzy spelling corrections
30. Query result pagination

Run tests against SQLite and PostgreSQL where configured.

Use frozen clocks and deterministic fixtures.

# 14. ACCEPTANCE CRITERIA

Phase 1B is complete only when:

- All enquiry functions are implemented.
- Direct and connecting routes work.
- Intermediate boarding works.
- All timetable edge cases pass.
- Fare calculations are accurate for seeded scenarios.
- Unknown information is never fabricated.
- The system handles multiple operators.
- APIs return consistent results.
- Tests pass on supported databases.
- Benchmark reports are generated.
- The engine operates without internet.
- No passenger or admin UI has been introduced.

# 15. DELIVERABLES

Provide:
1. Complete Python enquiry engine.
2. Search and station-resolver services.
3. Timetable calculation engine.
4. Route and connection search.
5. Fare calculation engine.
6. Operational status engine.
7. Typed API contracts.
8. REST endpoints.
9. Automated tests.
10. Benchmark scripts and measured results.
11. API usage examples.
12. Documentation of all supported intents.
13. Completion report with any unresolved limitations.

Do not stop at scaffolding or placeholder methods.

Complete the actual implementation, run the tests and fix failures.

At the end, explicitly report whether Phase 1B is COMPLETE or INCOMPLETE.

Do not start NLP training, speech processing or UI development yet.