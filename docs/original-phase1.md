# RTC Offline Conversational AI System
## PHASE 1 OF 6 — Enterprise Database Architecture & Core Enquiry Engine

You are a senior software architect, database engineer, transport-domain specialist and Python backend developer.

Build Phase 1 of a production-grade, completely offline, multilingual RTC Bus Enquiry System.

**IMPORTANT: Phase 1 must be fully implemented, tested and operational before proceeding to Phase 2.**

Do not implement the passenger UI, admin UI, speech recognition, text-to-speech or AI model training in this phase.

---

# 1. PROJECT OBJECTIVE

Develop the backend foundation for an intelligent RTC bus stand enquiry system.

Initial operator: APSRTC, Andhra Pradesh.

Future operators:
- TGSRTC — Telangana
- TNSTC — Tamil Nadu
- MTC — Chennai
- KSRTC and other RTC operators
- Optionally private bus operators

The architecture must support multiple states, transport corporations, depots, stations, languages, service classifications and fare structures without requiring database redesign.

The engine must eventually understand real-time conversations in Telugu, English, Tanglish and mixed-language speech.

All passenger answers must come from a structured database.

Never invent bus timings, prices, availability, locations, discounts or platform assignments.

# 2. STRICT TECHNOLOGY REQUIREMENTS

Backend:
- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic v2

Database:
- PostgreSQL as the primary production database.
- SQLite support for standalone offline kiosks.
- Use a repository abstraction supporting both.
- Avoid vendor-specific queries wherever practical.
- Use timezone-aware datetime handling.

Testing:
- Pytest
- HTTPX
- Factory-based test fixtures

Developer tools:
- Ruff
- Mypy
- Docker Compose
- Structured JSON logging

Strict restrictions:
- No GPT, OpenAI, Gemini, Claude or cloud AI.
- No external API calls.
- No remote database dependencies.
- No UI frameworks or frontend implementation in Phase 1.
- No pretrained model downloads at runtime.
- No fake responses or hardcoded RTC answers in backend logic.
- No duplicated tables, services or APIs.
- Use existing project structure if present; inspect before modifying.

# 3. DATABASE ARCHITECTURE

Design normalized database tables grouped into the following domains.

## A. Organization and Geography

Create:

1. states
2. districts
3. cities
4. transport_operators
5. operator_divisions
6. depots
7. bus_stations
8. station_bays
9. station_aliases
10. city_aliases

Important:
- Use stable UUID primary keys for appropriate entities.
- Provide human-readable operator and station codes.
- Support multiple stations in one city.
- Support common names and phonetic spellings.
- Store local language names.
- Do not assume all operators belong to one state.
- Support inter-state routes.
- Track active/inactive status.
- Track latitude/longitude where available.
- Support station-level timezones, defaulting to Asia/Kolkata for Indian stations.
- Allow multiple operators to use the same physical bus station.

Examples of aliases:

Vijayawada:
- Vijayawada
- Bezawada
- విజయవాడ
- బెజవాడ

Visakhapatnam:
- Visakhapatnam
- Vizag
- విశాఖపట్నం
- వైజాగ్

Tirupati:
- Tirupati
- Tirupathi
- తిరుపతి

Tirumala:
- Tirumala
- తిరుమల

IMPORTANT: Tirupati and Tirumala are different places and must never be merged.

## B. Bus Type and Vehicle Classification

Create:

1. bus_service_categories
2. bus_type_aliases
3. vehicle_types
4. vehicles
5. vehicle_amenities
6. vehicle_seat_layouts
7. vehicle_seats

Support APSRTC categories such as:
- Pallevelugu
- Ultra Pallevelugu
- Express
- Ultra Deluxe
- Super Luxury
- Indra
- Amaravathi
- Dolphin Cruise
- Vennela
- Vennela Economy
- Saptagiri Express
- Green Saptagiri
- Metro Express
- Metro Luxury
- Star Liner
- Night Rider
- Garuda / Garuda Plus where applicable

Treat these as configurable reference data, not a hardcoded exhaustive list.

Important distinction:
- Branded service category
- Vehicle body/configuration
- AC or non-AC
- Sleeper or seater
- Electric or diesel
- Ordinary or limited-stop
- Reservation-enabled or non-reservation

A service category must not automatically imply every amenity or vehicle property.

Store:
- AC availability
- Sleeper/seater
- 2+2, 2+1 and other configurations
- Seating capacity
- Berth capacity
- Accessible seating
- Wheelchair support
- Luggage provision
- Charging facility
- Tracking availability
- Reservation eligibility
- Fare class
- Operator-specific classification

Ensure bus type comparisons can work across operators.

## C. Route and Stop Management

Create:

1. routes
2. route_variants
3. route_stops
4. route_aliases
5. route_distance_data

Support:
- Direct routes
- One-way routes
- Opposite-direction routes
- Circular routes
- Express stop patterns
- Intermediate boarding and alighting points
- Different route variants between the same cities
- Multiple bus stands in a city
- Depot-origin services
- Inter-state routes

Every route stop must have:
- Sequence number
- Station/stop reference
- Distance from origin
- Scheduled offset
- Boarding permission
- Alighting permission
- Active status

Validate stop ordering and distance consistency.

Do not assume a service stops at every station it passes.

## D. Schedules and Service Operations

Create:

1. services
2. service_calendars
3. service_calendar_exceptions
4. service_stop_times
5. trips
6. trip_stop_times
7. trip_status_history
8. extra_services
9. service_disruptions
10. platform_assignments

Support:
- Daily services
- Weekday-only services
- Weekend services
- Specific dates
- Festival specials
- Extra buses
- Seasonal services
- Temporary cancellations
- Delayed departures
- Changed platforms
- Route diversions
- Cross-midnight journeys
- Different departure times on different days

Separate:
- Route = geographical path
- Service = recurring scheduled operation
- Trip = actual service occurrence on a particular date

Never model all three as one table.

Use the correct service date and timezone when calculating "next bus", "first bus", "last bus" and "tomorrow morning".

Ensure correct handling of schedules crossing midnight.

## E. Fare Management

Create:

1. fare_tables
2. fare_rules
3. fare_stages
4. trip_fare_overrides
5. fare_concessions
6. fare_concession_eligibility
7. fare_history

Support:
- Origin-to-destination fares
- Intermediate boarding fares
- Service-category-based fares
- Distance-based fares
- Operator-specific pricing
- Child fares
- Senior citizen concessions where applicable
- Applicable women's travel schemes
- Pass-based travel rules
- Temporary surcharges
- Special service fares
- Effective-from and effective-to dates

All concession schemes must be configurable, date-effective and operator-specific.

Do not assume any particular passenger is eligible for free travel or a discount.

Use Decimal for currency calculations.

Avoid floating-point arithmetic for fares.

## F. Seat and Reservation Data

Create:

1. trip_inventory
2. seat_availability_snapshots
3. reservation_channels
4. booking_references where applicable

Phase 1 is enquiry-only.

Do not implement payment processing or a reservation transaction engine.

Support queries such as:
- Are two seats available?
- Does this bus support reservations?
- Is sleeper available?
- How many seats are currently known to be vacant?

Clearly distinguish:
- Available
- Not available
- Unknown
- Stale inventory

Do not interpret unknown availability as zero seats.

## G. Operational Status and Data Quality

Create:

1. vehicle_locations
2. trip_delay_events
3. operational_alerts
4. data_sources
5. data_import_batches
6. data_quality_issues
7. audit_logs

Every operational update must retain:
- Source
- Recorded timestamp
- Effective timestamp
- Freshness status
- Operator
- Affected trip/service
- Verification status

Distinguish:
- Scheduled departure
- Estimated departure
- Actual departure

A scheduled bus must never be described as "arriving in 5 minutes" unless a verified real-time estimate exists.

No real GPS integration is required in Phase 1.

## H. NLP Preparation

Create:

1. nlp_intents
2. nlp_utterances
3. nlp_entity_types
4. nlp_entity_aliases
5. nlp_response_templates
6. conversation_sessions
7. conversation_messages
8. conversation_context
9. enquiry_execution_logs

Prepare for 40+ enquiry intents.

Examples:
NEXT_BUS
FIRST_BUS
LAST_BUS
GET_FARE
GET_BUS_TYPES
BUS_AVAILABILITY
GET_PLATFORM
GET_ROUTE
GET_STOPS
GET_DURATION
GET_ARRIVAL
GET_DELAY
GET_CANCELLATION
GET_SEAT_AVAILABILITY
GET_CHEAPEST_SERVICE
GET_FASTEST_SERVICE
GET_CONNECTING_BUSES
GET_CONCESSIONS
GET_STATION_FACILITIES
GET_LUGGAGE_RULES
GET_BOOKING_OPTIONS

Include Telugu, English and Tanglish aliases.

Do not implement machine learning training in Phase 1.

# 4. DATABASE DESIGN QUALITY

Implement:
- Appropriate primary and foreign keys
- Unique constraints
- Database indexes
- Check constraints
- Cascading policies
- Soft deletion where justified
- Created/updated timestamps
- Audit provenance
- Referential integrity
- Transaction management
- Schema migrations

Use proper constraints for:
- Duplicate stations
- Duplicate service numbers within applicable scope
- Invalid stop sequences
- Negative fares
- Invalid vehicle capacities
- Conflicting calendar exceptions
- Impossible temporal relationships
- Duplicate seat identifiers
- Invalid coordinates

Use normalized relational design.

Avoid unnecessary tables if a simpler normalized structure achieves the same purpose.

Do not create a giant table containing every bus property.

# 5. CORE ENQUIRY ENGINE

Implement fully operational Python services:

1. get_next_buses()
2. get_first_bus()
3. get_last_bus()
4. get_bus_fare()
5. get_available_bus_types()
6. get_service_details()
7. get_route_stops()
8. get_journey_duration()
9. get_arrival_time()
10. get_platform_assignment()
11. get_seat_availability()
12. get_service_status()
13. get_cheapest_services()
14. get_fastest_services()
15. get_direct_services()
16. get_connecting_services()
17. get_services_via_stop()
18. get_operator_services()
19. get_concessions()
20. get_station_facilities()

Do not simply write empty functions.

Implement actual SQLAlchemy queries with filtering, ordering and pagination.

Every function should:
- Accept validated structured parameters.
- Resolve station and operator IDs.
- Return structured typed responses.
- Include source and timestamp metadata where relevant.
- Handle unknown data gracefully.
- Support optional bus category and amenity filters.
- Preserve correct dates and timezones.

For next bus:
- Exclude departures already passed.
- Include appropriate cross-midnight services.
- Respect cancelled service instances.
- Return chronological results.
- Differentiate scheduled and estimated departures.

For last bus:
- Clarify the operating-day boundary.
- Do not accidentally return the next day's early-morning service.

For fare:
- Use actual origin and destination boarding stages.
- Apply fare validity periods.
- Return available fare classes and concession eligibility separately.

For connections:
- Respect stop sequences.
- Require a realistic configurable minimum transfer window.
- Avoid returning journeys that arrive after their connecting service departs.
- Cap transfers and search complexity.

# 6. REST API — BACKEND ONLY

Build versioned APIs under /api/v1.

Examples:

GET /operators
GET /stations
GET /stations/search
GET /bus-types
GET /routes
GET /services
GET /enquiry/next-bus
GET /enquiry/first-bus
GET /enquiry/last-bus
GET /enquiry/fare
GET /enquiry/bus-types
GET /enquiry/route
GET /enquiry/availability
GET /enquiry/connections
GET /enquiry/platform
GET /enquiry/status
GET /enquiry/facilities

Provide OpenAPI documentation through FastAPI.

Use:
- Consistent response envelopes
- Typed validation errors
- Pagination
- Search limits
- Appropriate HTTP status codes

All enquiry endpoints must work without any AI model.

Prepare admin CRUD APIs but do not implement any admin frontend.

Protect mutation endpoints with local authentication and roles.

Do not expose unrestricted database operations.

# 7. SEED DATA

Provide an idempotent seed mechanism.

Create realistic but clearly labelled FICTIONAL demonstration data.

Include major Andhra Pradesh locations such as:

Vijayawada
Guntur
Tirupati
Tirumala
Nellore
Ongole
Kavali
Rajahmundry
Visakhapatnam
Kakinada
Kurnool
Kadapa
Anantapur
Eluru
Srikakulam
Vizianagaram
Machilipatnam
Bhimavaram
Srisailam
Annavaram

Include Hyderabad as an interstate destination.

Create:
- At least 100 demo scheduled services
- Multiple bus categories
- Different daily and weekly calendars
- Overnight services
- Intermediate stops
- Fare stages
- Scheduled journeys
- A few documented cancellations and platform changes
- Multiple variants between selected destinations

No demo record must be represented as official APSRTC data.

Include a dataset_source indicator and label all fabricated operational data as DEMO.

# 8. IMPORT AND DATA MAINTENANCE

Implement robust offline CSV import services for:
- Operators
- Cities and stations
- Bus categories
- Routes and stops
- Schedules
- Fares
- Calendar exceptions

Include:
- Schema validation
- Duplicate detection
- Referential validation
- Dry-run preview
- Row-level errors
- Transaction rollback
- Import provenance
- Safe repeat imports

Generate example import templates.

Design the import architecture so approved RTC data providers can be integrated later.

Do not build web scrapers or connect external services.

# 9. TESTING

Build automated tests for:
- Next bus
- Last bus
- First bus
- Fare calculation
- Bus-type filtering
- Route stop ordering
- Same-day services
- Tomorrow's services
- Overnight journeys
- Cancellations
- Platform changes
- Unknown fare
- Unknown seat availability
- Service calendar exceptions
- Connecting journeys
- Duplicate imports
- Cross-operator routes
- Unicode Telugu aliases
- PostgreSQL and SQLite compatibility

Add API integration tests.

Test boundary times such as:
- 11:59 PM
- 12:00 AM
- 12:01 AM

Use deterministic clocks in tests.

No reliance on the machine's current time.

# 10. PERFORMANCE

Create indexes for:
- Origin station
- Destination station
- Departure date/time
- Operator
- Service category
- Route stops
- Service calendar lookup

Aim for fast local enquiry responses.

Provide a benchmark script for commonly used queries.

Do not add Redis unless measurements demonstrate a need.

Avoid unnecessary complexity and large infrastructure dependencies.

# 11. FILE STRUCTURE

Use a clean modular structure similar to:

rtc-offline/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      repositories/
      services/
      enquiry/
      imports/
      nlp/
      security/
    alembic/
    tests/
  data/
    seed/
    import_templates/
  scripts/
  docs/
  docker-compose.yml
  .env.example
  README.md

Adapt if an existing repository structure is better.

# 12. FINAL DELIVERABLES

Deliver:

1. Complete working backend.
2. PostgreSQL and SQLite support.
3. All necessary migrations.
4. Seed data.
5. Fully implemented enquiry services.
6. REST API.
7. Import services.
8. Automated tests.
9. Database ER diagram (Mermaid or equivalent).
10. Architecture documentation.
11. Example API requests/responses.
12. Working local startup instructions.
13. Database verification script.
14. Short Phase 1 completion report.

# 13. ACCEPTANCE CRITERIA

Phase 1 is complete only when:

- Migrations work on a fresh database.
- Seed data loads successfully.
- All core enquiry functions return valid results.
- All major entities have necessary referential constraints.
- The API runs without internet.
- PostgreSQL and SQLite tests pass.
- There are no hardcoded passenger answers.
- Date and time boundary tests pass.
- Demo data is clearly distinguished from verified data.
- Import validation and rollback work.
- The backend can support an NLP model without restructuring its core API.

Run tests and fix failures before declaring completion.

# FINAL INSTRUCTION

Do not stop after writing a plan.

Inspect the repository and begin implementing Phase 1 immediately.

Prioritize database integrity, correct timetable calculations, extensibility and long-term maintainability over superficial code volume.

Do not implement Phase 2, Phase 3 or Phase 4 prematurely.

At completion, summarize:
- Files created/modified
- Schema implemented
- Enquiry APIs completed
- Tests executed and results
- Known limitations
- Phase 2 integration readiness