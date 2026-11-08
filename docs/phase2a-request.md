# RTC OFFLINE AI — PHASE 2A
## Complete Intent Taxonomy, Slot Definitions and NLP Training Foundation

Continue in the EXISTING RTC Offline AI repository.

OBJECTIVE:
Establish the complete English RTC enquiry intent taxonomy before generating thousands of training examples.

Do not train a model in this phase.
Do not implement UI.
Do not generate the complete training corpus yet; that is Phase 2B.

## 1. Register 60 canonical enquiry intents

Implement the following categories and exact codes:

TIMINGS:
NEXT_BUS, FIRST_BUS, LAST_BUS, BUSES_BETWEEN, DEPARTURES_AFTER, DEPARTURES_BEFORE, BUS_AT_TIME, ARRIVAL_TIME, JOURNEY_DURATION, BUSES_OPERATING_TODAY, SERVICE_FREQUENCY, SPECIAL_DAY_SCHEDULE.

BUS TYPES:
AVAILABLE_BUS_TYPES, AC_BUS_AVAILABILITY, NON_AC_BUS_AVAILABILITY, SLEEPER_AVAILABILITY, SEATER_AVAILABILITY, ELECTRIC_BUS_AVAILABILITY, BUS_AMENITIES, SERVICE_CATEGORY_COMPARISON, ACCESSIBLE_BUS_AVAILABILITY, BUS_CAPACITY.

ROUTES:
DIRECT_BUS, ROUTE_STOPS, BUS_VIA_LOCATION, INTERMEDIATE_STOP, BOARDING_POINT, ALIGHTING_POINT, CONNECTING_BUSES, ALTERNATIVE_ROUTES, ROUTE_DISTANCE, DESTINATION_REACHABILITY.

FARES AND BOOKINGS:
GET_FARE, CHEAPEST_BUS, FASTEST_BUS, FARE_COMPARISON, SEAT_AVAILABILITY, RESERVATION_SUPPORTED, BOOKING_OPTIONS, BOOKING_STATUS, CANCELLATION_POLICY, REFUND_POLICY, CONCESSION_ENQUIRY, LUGGAGE_RULES.

OPERATIONS:
LIVE_BUS_STATUS, BUS_DELAY, BUS_CANCELLATION, BUS_PLATFORM, ESTIMATED_ARRIVAL, BUS_DEPARTED_STATUS, BUS_ARRIVED_STATUS, SERVICE_DISRUPTION, PLATFORM_CHANGE, SERVICE_NUMBER_LOOKUP.

STATION ASSISTANCE:
STATION_FACILITIES, STATION_HELPDESK, LOST_PROPERTY, OPERATOR_CONTACT, STATION_NAVIGATION, COMPLAINT_GUIDANCE.

## 2. Reconcile existing intents

Inspect the existing NLP database, Python enums, enquiry services and API contracts.

Create a mapping from existing codes to canonical codes.

Preserve backwards compatibility.

Avoid duplicate labels with the same meaning.

Do not remove existing data or API functionality.

## 3. Define an intent registry

For every intent, store:

- Canonical intent code
- Intent group
- Display name
- Exact definition
- Positive query examples
- Similar but different intents
- Required slots
- Optional slots
- Applicable database enquiry function
- Clarification conditions
- Supported result status
- Whether live data is required
- Whether current backend functionality supports it
- Response template identifier

Define supported capabilities honestly:
IMPLEMENTED
PARTIAL
UNSUPPORTED

An intent can be recognized even if its operational data is unavailable, but must not fabricate an answer.

## 4. Define entity types

Implement a structured entity taxonomy:

ORIGIN_CITY
DESTINATION_CITY
ORIGIN_STATION
DESTINATION_STATION
VIA_STATION
TRANSFER_STATION
BOARDING_STATION
ALIGHTING_STATION
BUS_CATEGORY
VEHICLE_TYPE
AC_PREFERENCE
SLEEPER_PREFERENCE
AMENITY
ACCESSIBILITY_REQUIREMENT
OPERATOR
SERVICE_NUMBER
ROUTE_NUMBER
VEHICLE_NUMBER
PLATFORM
TRAVEL_DATE
DATE_RANGE
TIME
TIME_RANGE
TIME_PERIOD
TIME_RELATION
PASSENGER_COUNT
SEAT_COUNT
FARE_AMOUNT
FARE_LIMIT
CURRENCY
CONCESSION_TYPE
RESERVATION_REFERENCE

Also model negative and exclusion constraints.

## 5. Required and optional slots

Define slots per intent.

Examples:

NEXT_BUS:
Required:
- destination (unless resolved through context)

Optional:
- origin
- date
- operator
- bus category
- AC preference
- departure time threshold

GET_FARE:
Required:
- origin
- destination or selected service with valid boarding/alighting segment

Optional:
- category
- travel date
- passenger type
- concession scheme

BUS_PLATFORM:
Required:
- selected trip or sufficiently specific service/date/station combination

Optional:
- origin
- destination

CONNECTING_BUSES:
Required:
- origin
- destination
- travel date or next-available policy

Optional:
- maximum transfers
- transfer time
- bus category
- fare limit

Define appropriate clarification prompts when required slots are absent.

## 6. Define dialogue acts separately

Register:
GREETING
THANKS
AFFIRMATION
NEGATION
CORRECTION
REPEAT_REQUEST
CLARIFICATION_REPLY
CHANGE_DESTINATION
CHANGE_DATE
CHANGE_BUS_TYPE
RESET_CONVERSATION
HELP
OUT_OF_SCOPE
UNINTELLIGIBLE

The dialogue classifier may identify a dialogue act and one or more RTC intents in the same utterance.

Never force every statement into a single RTC intent.

## 7. Multi-intent composition

Design structured representations for:

"Next bus to Nellore and fare?"
→ NEXT_BUS + GET_FARE

"Is the bus late, and which platform?"
→ BUS_DELAY + BUS_PLATFORM

"Cheapest AC sleeper tomorrow?"
→ CHEAPEST_BUS with AC and SLEEPER constraints

"Which is the fastest bus, and does it stop at Ongole?"
→ FASTEST_BUS + INTERMEDIATE_STOP

Define entity sharing and execution dependencies.

Avoid unnecessary independent database queries when a common trip result can be reused.

## 8. Intent ambiguity matrix

Create a machine-readable confusion/ambiguity matrix.

Pay attention to:

NEXT_BUS vs FIRST_BUS
LAST_BUS vs DEPARTURES_BEFORE
ARRIVAL_TIME vs ESTIMATED_ARRIVAL
BUS_AT_TIME vs DEPARTURES_AFTER
BUS_VIA_LOCATION vs INTERMEDIATE_STOP
DIRECT_BUS vs DESTINATION_REACHABILITY
GET_FARE vs FARE_COMPARISON
CHEAPEST_BUS vs CONCESSION_ENQUIRY
BUS_DELAY vs LIVE_BUS_STATUS
BUS_PLATFORM vs PLATFORM_CHANGE
BOOKING_STATUS vs SEAT_AVAILABILITY

Define positive and negative distinctions.

## 9. Sample queries

Create 5–10 independently written English examples for each intent as an initial taxonomy verification set.

Do not generate the full 200+ examples per intent in this phase.

Ensure examples are realistic Indian bus stand questions.

Include examples referring to APSRTC bus categories, stops and intermediate boarding locations.

These initial examples must not automatically become the independent Phase 2D test set.

## 10. Database and API integration

Store the taxonomy using existing NLP database tables where possible.

Expose or reuse:

GET /api/v1/nlp/intents
GET /api/v1/nlp/intents/{code}
GET /api/v1/nlp/entities

Provide internal typed lookup functions.

No need for a new UI or separate administrative application.

## 11. Validation

Implement automated tests that verify:

- Exactly 60 canonical enquiry intents
- Unique codes
- No duplicate canonical meanings
- Every intent has defined slots
- Every intent has an execution capability status
- Every intent has positive examples
- Every intent has required clarification rules
- Existing legacy codes still resolve
- Dialogue acts are distinct from enquiry intents
- Multi-intent representations are valid
- No unsupported intent is falsely marked implemented

## 12. Deliverables

Create or update:

docs/NLP_INTENT_CATALOG.md
docs/NLP_INTENT_AMBIGUITIES.md
docs/NLP_ENTITY_SCHEMA.md
training/config/intent_registry.yaml
training/config/entity_registry.yaml
training/config/dialogue_acts.yaml
training/datasets/phase2a_seed_examples.jsonl

Reuse existing paths if the repository already has equivalent files.

## 13. Final verification

Run taxonomy validation.
Run backend regression tests.
Run Ruff and Mypy.
Verify the entire process works offline.

Report:
- Total registered intents
- Intent groups
- Dialogue acts
- Entity types
- Examples created
- Implemented vs unsupported enquiry functions
- Test results
- Outstanding gaps

Do not claim Phase 2A complete if the taxonomy is inconsistent.

Do not start Phase 2B, model training, speech orchestration or UI development.

Begin implementation immediately.