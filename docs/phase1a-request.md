# RTC Offline AI – Detailed Database Schema

Phase 1A — Database Architecture

We will design a production-grade, operator-independent RTC database that supports APSRTC initially, followed by TGSRTC, TNSTC, MTC Chennai, KSRTC and other transport operators.

The database must support not only bus schedules and fares, but also natural-language enquiries, bus classifications, intermediate stops, ticket availability, platform assignments, operational changes and future offline AI training.

Recommended database: PostgreSQL 16+ for the central server, with SQLite support for standalone offline kiosks.

## 1. Core database principles

- One database, multiple operators: No separate database for each RTC.
- Separate geography from operations: A city, bus station, route, scheduled service, dated trip and physical bus are different entities.
- Database-driven NLP: Telugu, English, Tanglish and local synonyms come from master tables.
- Historical accuracy: Store effective dates, schedules, fares and operational changes.
- Completely offline: The enquiry engine must work without external services.
- No fabricated responses: Unknown timings, fares and availability must remain unknown.
- Extensibility: New states, bus categories, stations and services should be added through data rather than code changes.

## 2. Database domains

| Domain                   | Main purpose                                             |
| ------------------------ | -------------------------------------------------------- |
| A. Geography & operators | States, cities, stations, depots, operator jurisdictions |
| B. Bus classification    | Express, Super Luxury, AC, sleeper, amenities, vehicles  |
| C. Routes & stops        | Source, destination, route variants, intermediate stops  |
| D. Scheduling            | Recurring services, departure calendars, dated trips     |
| E. Fare management       | Fare stages, prices, concessions and validity            |
| F. Seat availability     | Reservations, seats, availability snapshots              |
| G. Live operations       | GPS, arrival estimates, delays, cancellations, platforms |
| H. NLP & conversations   | Intent definitions, aliases, templates, context          |
| I. Data administration   | Imports, provenance, validation, auditing                |

# 3. Detailed relational schema

The following defines the logical schema. Use UUID identifiers, foreign keys, unique constraints, indexes and timezone-aware timestamps where appropriate. Common `created_at`, `updated_at` and audit columns can be standardized across tables rather than repeated everywhere.

## A. Geography and RTC operators

### A1. `states`

| Column         | Type               | Description      |
| -------------- | ------------------ | ---------------- |
| `id`           | UUID PK            | State identifier |
| `code`         | VARCHAR(10) UNIQUE | AP, TS, TN, KA   |
| `name_en`      | VARCHAR(100)       | State name       |
| `name_native`  | VARCHAR(150)       | స్థానిక పేరు     |
| `country_code` | CHAR(2)            | IN               |
| `timezone`     | VARCHAR(60)        | Asia/Kolkata     |
| `is_active`    | BOOLEAN            | Active state     |

### A2. `districts`

`id`, `state_id` FK, `code`, `name_en`, `name_native`, `is_active`.

District codes should be unique within a state and must not be assumed globally unique.

### A3. `cities`

`id`, `state_id` FK, `district_id` FK nullable, `name_en`, `name_native`, `latitude`, `longitude`, `is_active`.

A city can contain multiple bus stands and several possible boarding points.

### A4. `transport_operators`

| Column                 | Type               | Description            |
| ---------------------- | ------------------ | ---------------------- |
| `id`                   | UUID PK            | Operator               |
| `code`                 | VARCHAR(20) UNIQUE | APSRTC, TGSRTC         |
| `name`                 | VARCHAR(200)       | Corporation name       |
| `short_name`           | VARCHAR(50)        | Display name           |
| `headquarters_city_id` | UUID FK nullable   | Headquarters           |
| `website`              | TEXT nullable      | Informational metadata |
| `default_timezone`     | VARCHAR(60)        | Default timezone       |
| `is_active`            | BOOLEAN            | Operator status        |

An operator can serve multiple states. Do not limit the operator to one state using a mandatory `state_id`.

### A5. `operator_service_areas`

`operator_id` FK, `state_id` FK, `service_area_type`, `effective_from`, `effective_to`.

Tracks states or regions served by an operator.

### A6. `operator_divisions`

`id`, `operator_id` FK, `code`, `name`, `is_active`.

### A7. `depots`

`id`, `operator_id` FK, `division_id` FK nullable, `code`, `name`, `city_id` FK, `address`, `is_active`.

A depot manages vehicles and operations; it is not automatically a passenger bus station.

### A8. `bus_stations`

| Column         | Type                   | Description             |
| -------------- | ---------------------- | ----------------------- |
| `id`           | UUID PK                | Station identifier      |
| `code`         | VARCHAR(30)            | Operator/system code    |
| `city_id`      | UUID FK                | City                    |
| `name_en`      | VARCHAR(200)           | Vijayawada PNBS         |
| `name_native`  | VARCHAR(200)           | విజయవాడ పీఎన్‌బీఎస్     |
| `station_type` | VARCHAR(30)            | TERMINAL / STAND / STOP |
| `address`      | TEXT                   | Station address         |
| `latitude`     | DECIMAL(10,7) nullable | Latitude                |
| `longitude`    | DECIMAL(10,7) nullable | Longitude               |
| `timezone`     | VARCHAR(60)            | Station-local timezone  |
| `is_active`    | BOOLEAN                | Status                  |

Use a separate `operator_station_access` relationship if multiple RTC operators share the same station.

### A9. `station_bays`

`id`, `station_id` FK, `bay_code`, `bay_name`, `floor_or_zone`, `accessible`, `is_active`.

Examples: Platform 1, Platform 2, Bay 10, Local Bus Bay.

### A10. `place_aliases`

| Column             | Type         | Description                       |
| ------------------ | ------------ | --------------------------------- |
| `id`               | UUID PK      | Alias identifier                  |
| `entity_type`      | ENUM         | STATE / DISTRICT / CITY / STATION |
| `entity_id`        | UUID         | Referenced place                  |
| `alias_text`       | VARCHAR(250) | Bezawada                          |
| `normalized_alias` | VARCHAR(250) | bezawada                          |
| `language_code`    | VARCHAR(12)  | te, en, te-Latn                   |
| `is_primary`       | BOOLEAN      | Preferred alias                   |

Implement the polymorphic `entity_id` with enforceable integrity—prefer separate typed alias tables or a unified places registry rather than an unchecked generic UUID.

Example alias records

| Canonical place   | Aliases                                   |
| ----------------- | ----------------------------------------- |
| Vijayawada        | Vijayawada, Bezawada, విజయవాడ, బెజవాడ     |
| Visakhapatnam     | Visakhapatnam, Vizag, వైజాగ్, విశాఖపట్నం  |
| Tirupati          | Tirupati, Tirupathi, తిరుపతి              |
| Tirumala          | Tirumala, తిరుమల                          |
| Rajamahendravaram | Rajahmundry, Rajamahendravaram, రాజమండ్రి |
| Kadapa            | Kadapa, Cuddapah, కడప                     |

Never merge Tirupati and Tirumala. The NLP engine must distinguish the two.

## B. Bus categories, vehicles and amenities

### B1. `bus_service_categories`

| Column            | Type                 | Description                       |
| ----------------- | -------------------- | --------------------------------- |
| `id`              | UUID PK              | Category                          |
| `operator_id`     | UUID FK nullable     | Null for shared category taxonomy |
| `code`            | VARCHAR(40)          | SUPER_LUXURY                      |
| `name_en`         | VARCHAR(120)         | Super Luxury                      |
| `name_native`     | VARCHAR(120)         | సూపర్ లగ్జరీ                      |
| `description`     | TEXT                 | Category details                  |
| `service_tier`    | VARCHAR(30)          | ORDINARY / EXPRESS / PREMIUM      |
| `fare_class_code` | VARCHAR(40) nullable | Default fare classification       |
| `is_active`       | BOOLEAN              | Status                            |

Seed APSRTC categories as configurable operator records, without assuming every historically named category is currently active.

### B2. `bus_type_aliases`

`id`, `category_id` FK, `alias_text`, `normalized_alias`, `language_code`.

Examples: `super luxury`, `superluxury`, `SL`, `సూపర్ లగ్జరీ`.

### B3. `vehicle_types`

| Column             | Type         | Description                 |
| ------------------ | ------------ | --------------------------- |
| `id`               | UUID PK      | Vehicle configuration       |
| `code`             | VARCHAR(50)  | AC_SLEEPER_2_1              |
| `name`             | VARCHAR(120) | AC Sleeper 2+1              |
| `ac_type`          | VARCHAR(20)  | AC / NON_AC                 |
| `layout_type`      | VARCHAR(20)  | SEATER / SLEEPER / MIXED    |
| `seating_capacity` | SMALLINT     | Number of seats             |
| `berth_capacity`   | SMALLINT     | Number of berths            |
| `seat_layout_code` | VARCHAR(30)  | 2+1, 2+2                    |
| `fuel_type`        | VARCHAR(20)  | DIESEL / CNG / ELECTRIC     |
| `accessible`       | BOOLEAN      | Accessibility configuration |

### B4. `vehicles`

`id`, `operator_id` FK, `depot_id` FK nullable, `vehicle_type_id` FK, `registration_number`, `fleet_number`, `manufacture_year`, `active_status`.

### B5. `amenities`

`id`, `code`, `name_en`, `name_native`, `description`.

Examples: AC, charging port, wheelchair boarding, luggage compartment, reclining seats.

### B6. `vehicle_amenities`

`vehicle_id` FK, `amenity_id` FK, `available`, `verified_at`.

### B7. `vehicle_seats`

`id`, `vehicle_id` FK, `seat_number`, `seat_kind`, `deck`, `row_number`, `position_code`, `accessible`, `is_active`.

Use unique `(vehicle_id, seat_number)`.

A bus service category does not guarantee a specific seat layout. Actual seat properties come from the vehicle or assigned configuration.

## C. Route and intermediate-stop management

### C1. `routes`

| Column                   | Type         | Description                   |
| ------------------------ | ------------ | ----------------------------- |
| `id`                     | UUID PK      | Route identity                |
| `operator_id`            | UUID FK      | Primary operating corporation |
| `route_code`             | VARCHAR(50)  | Operator route code           |
| `origin_station_id`      | UUID FK      | Route origin                  |
| `destination_station_id` | UUID FK      | Route destination             |
| `route_name`             | VARCHAR(250) | Display name                  |
| `is_active`              | BOOLEAN      | Status                        |

### C2. `route_variants`

`id`, `route_id` FK, `variant_code`, `variant_name`, `direction_code`, `total_distance_km`, `is_active`.

This is important where two buses travel between the same cities but take different paths.

### C3. `route_stops`

| Column                     | Type             | Description         |
| -------------------------- | ---------------- | ------------------- |
| `id`                       | UUID PK          | Stop record         |
| `variant_id`               | UUID FK          | Route variant       |
| `station_id`               | UUID FK          | Stop                |
| `stop_sequence`            | INTEGER          | Stop order          |
| `distance_from_origin_km`  | DECIMAL(9,2)     | Cumulative distance |
| `arrival_offset_minutes`   | INTEGER nullable | Relative arrival    |
| `departure_offset_minutes` | INTEGER nullable | Relative departure  |
| `boarding_allowed`         | BOOLEAN          | Can board           |
| `alighting_allowed`        | BOOLEAN          | Can alight          |

Stops must be sorted by sequence, not alphabetically.

Example route: Vijayawada → Nellore

Vijayawada PNBS

Origin

Guntur

Ongole

Kavali

Nellore

Destination

Illustrative route for schema explanation, not a verified current RTC service.

### C4. `route_aliases`

`id`, `route_id` FK, `alias_text`, `normalized_alias`, `language_code`.

### C5. `route_distance_sources`

`id`, `variant_id` FK, `distance_km`, `source_id` FK, `verified_at`.

## D. Timetables, services and dated trips

This is the most important operational part of the database.

### D1. `services`

| Column                           | Type          | Description               |
| -------------------------------- | ------------- | ------------------------- |
| `id`                             | UUID PK       | Recurring service         |
| `operator_id`                    | UUID FK       | RTC operator              |
| `service_number`                 | VARCHAR(40)   | Operator service number   |
| `route_variant_id`               | UUID FK       | Route taken               |
| `category_id`                    | UUID FK       | Bus category              |
| `origin_departure_time`          | TIME          | Scheduled local departure |
| `destination_arrival_day_offset` | SMALLINT      | 0, 1, 2 etc.              |
| `reservation_supported`          | BOOLEAN       | Reservation policy        |
| `operating_status`               | VARCHAR(20)   | ACTIVE / SUSPENDED        |
| `effective_from`                 | DATE          | Schedule validity         |
| `effective_to`                   | DATE nullable | Schedule end              |

Service numbers may repeat under different operational scopes or valid periods. Design the uniqueness constraint accordingly.

### D2. `service_calendars`

`id`, `service_id` FK, `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday`, `valid_from`, `valid_to`.

### D3. `service_calendar_exceptions`

`id`, `service_id` FK, `service_date`, `exception_type`, `reason`.

Exception types: ADDED, REMOVED.

Use uniqueness on service/date and define precedence over regular calendar rules.

### D4. `service_stop_times`

`id`, `service_id` FK, `route_stop_id` FK, `arrival_offset_minutes`, `departure_offset_minutes`, `pickup_allowed`, `dropoff_allowed`.

Use elapsed offsets to correctly model journeys that cross midnight.

### D5. `trips`

| Column                   | Type                 | Description                            |
| ------------------------ | -------------------- | -------------------------------------- |
| `id`                     | UUID PK              | Actual dated service                   |
| `service_id`             | UUID FK              | Recurring service                      |
| `service_date`           | DATE                 | Operating date                         |
| `vehicle_id`             | UUID FK nullable     | Assigned bus                           |
| `planned_departure_at`   | TIMESTAMPTZ          | Planned departure                      |
| `estimated_departure_at` | TIMESTAMPTZ nullable | Revised estimate                       |
| `actual_departure_at`    | TIMESTAMPTZ nullable | Real departure                         |
| `trip_status`            | VARCHAR(30)          | SCHEDULED / DELAYED / CANCELLED / etc. |
| `source_id`              | UUID FK nullable     | Operational source                     |
| `status_updated_at`      | TIMESTAMPTZ          | Freshness timestamp                    |

### D6. `trip_stop_times`

`id`, `trip_id` FK, `route_stop_id` FK, `scheduled_arrival_at`, `scheduled_departure_at`, `estimated_arrival_at`, `estimated_departure_at`, `actual_arrival_at`, `actual_departure_at`, `stop_status`.

This allows the system to answer: "Has the bus already left Ongole?" rather than just knowing the original departure time.

### D7. `trip_status_events`

`id`, `trip_id` FK, `event_type`, `old_status`, `new_status`, `event_at`, `reason`, `source_id` FK.

Append events rather than overwriting operational history.

### D8. `service_disruptions`

`id`, `operator_id` FK, `service_id` FK nullable, `trip_id` FK nullable, `disruption_type`, `description`, `starts_at`, `ends_at`, `verified_at`.

## E. Fare management

### E1. `fare_tables`

`id`, `operator_id` FK, `name`, `currency_code`, `valid_from`, `valid_to`, `status`.

### E2. `fare_rules`

| Column                   | Type                 | Description        |
| ------------------------ | -------------------- | ------------------ |
| `id`                     | UUID PK              | Fare rule          |
| `fare_table_id`          | UUID FK              | Applicable tariff  |
| `category_id`            | UUID FK nullable     | Bus class          |
| `origin_station_id`      | UUID FK              | Boarding station   |
| `destination_station_id` | UUID FK              | Alighting station  |
| `base_fare`              | DECIMAL(12,2)        | Fare               |
| `additional_charge`      | DECIMAL(12,2)        | Additional charges |
| `total_fare`             | DECIMAL(12,2)        | Applicable total   |
| `valid_from`             | TIMESTAMPTZ          | Starts             |
| `valid_to`               | TIMESTAMPTZ nullable | Ends               |

For distance/stage-based fares, add `fare_stage_rules` with stage boundaries, distance bands and calculation method. Avoid requiring every possible boarding/alighting combination to be stored explicitly.

### E3. `trip_fare_overrides`

`id`, `trip_id` FK, `origin_station_id` FK, `destination_station_id` FK, `fare_amount`, `reason`, `valid_from`, `valid_to`.

### E4. `concession_schemes`

`id`, `operator_id` FK, `scheme_code`, `name`, `eligibility_description`, `discount_type`, `discount_value`, `valid_from`, `valid_to`, `is_active`.

### E5. `concession_applicability`

`scheme_id` FK, `category_id` FK nullable, `route_id` FK nullable, `state_id` FK nullable, `eligibility_rule_json`, `priority`.

Store eligibility conditions explicitly. Do not infer a person's eligibility merely from asking about a concession.

### E6. `fare_history`

`id`, `fare_rule_id` FK, `previous_value`, `new_value`, `changed_at`, `reason`, `changed_by`.

## F. Seat and reservation enquiries

### F1. `trip_inventory`

`id`, `trip_id` FK, `capacity`, `reservable_capacity`, `available_count`, `held_count`, `sold_count`, `availability_status`, `source_id`, `last_updated_at`.

Use a distinct `UNKNOWN` state rather than returning zero seats when no reliable information exists.

### F2. `seat_availability_snapshots`

`id`, `trip_id` FK, `origin_station_id` FK, `destination_station_id` FK, `seat_class`, `available_count`, `recorded_at`, `source_id`.

Availability is segment-dependent. A seat may be occupied for part of the journey but vacant for another segment.

### F3. `reservation_channels`

`id`, `operator_id` FK, `channel_name`, `channel_type`, `is_active`.

### F4. `reservation_enquiry_references`

`id`, `trip_id` FK nullable, `reservation_channel_id` FK, `reference_code` nullable, `recorded_at`.

No payment, passenger identity storage or booking execution is needed in Phase 1.

## G. Bus status, GPS and platforms

### G1. `vehicle_locations`

`id`, `vehicle_id` FK, `trip_id` FK nullable, `latitude`, `longitude`, `speed_kmh`, `heading`, `observed_at`, `received_at`, `source_id` FK.

### G2. `trip_delay_events`

`id`, `trip_id` FK, `affected_stop_id` FK nullable, `delay_minutes`, `reason`, `observed_at`, `verified_at`, `source_id` FK.

### G3. `platform_assignments`

`id`, `trip_id` FK, `station_id` FK, `bay_id` FK, `effective_from`, `effective_to`, `assignment_status`, `source_id` FK.

### G4. `operational_alerts`

`id`, `operator_id` FK, `severity`, `alert_type`, `message_en`, `message_native`, `starts_at`, `ends_at`, `source_id`.

### G5. `station_facilities`

`id`, `station_id` FK, `facility_type`, `name`, `location_description`, `accessible`, `is_available`, `last_verified_at`.

### G6. `station_contact_points`

`id`, `station_id` FK, `contact_type`, `label`, `contact_value`, `opening_hours`, `last_verified_at`.

Supports enquiries about helpdesks, lost property, emergency contact and station information.

## H. NLP, training data and conversational intelligence

These tables will be particularly important for our fine-tuned MuRIL model and the lightweight TensorFlow model we will benchmark in Phase 2.

### H1. `nlp_intents`

| Column                | Type               | Description        |
| --------------------- | ------------------ | ------------------ |
| `id`                  | UUID PK            | Intent ID          |
| `intent_code`         | VARCHAR(80) UNIQUE | NEXT_BUS           |
| `display_name`        | VARCHAR(150)       | Next available bus |
| `description`         | TEXT               | Intent definition  |
| `required_slots_json` | JSON               | Required entities  |
| `optional_slots_json` | JSON               | Optional entities  |
| `is_active`           | BOOLEAN            | Enabled            |

### H2. `nlp_utterances`

| Column            | Type        | Description                    |
| ----------------- | ----------- | ------------------------------ |
| `id`              | UUID PK     | Training example               |
| `intent_id`       | UUID FK     | Expected intent                |
| `utterance_text`  | TEXT        | Passenger question             |
| `language_code`   | VARCHAR(12) | te / en / te-Latn / mixed      |
| `normalized_text` | TEXT        | Normalized query               |
| `dataset_split`   | VARCHAR(12) | TRAIN / VALIDATION / TEST      |
| `source_type`     | VARCHAR(30) | SYNTHETIC / HUMAN / TRANSCRIPT |
| `quality_status`  | VARCHAR(20) | REVIEWED / PENDING             |
| `is_active`       | BOOLEAN     | Training eligibility           |

### H3. `nlp_entity_types`

`id`, `entity_code`, `name`, `description`.

Examples: ORIGIN, DESTINATION, BUS_CATEGORY, DATE, TIME, PASSENGER_COUNT, AMENITY, PLATFORM, SERVICE_NUMBER.

### H4. `nlp_entity_annotations`

`id`, `utterance_id` FK, `entity_type_id` FK, `start_offset`, `end_offset`, `surface_text`, `canonical_value`, `review_status`.

These annotations let us train and evaluate named entity recognition later instead of relying only on dictionaries.

### H5. `nlp_entity_aliases`

`id`, `entity_type_id` FK, `canonical_entity_id` nullable, `canonical_value`, `alias_text`, `normalized_alias`, `language_code`, `priority`, `is_active`.

Aliases should be linked to validated entities when possible. Station names should resolve to actual station or city identifiers, not arbitrary strings.

### H6. `nlp_response_templates`

| Column                       | Type        | Description                         |
| ---------------------------- | ----------- | ----------------------------------- |
| `id`                         | UUID PK     | Template                            |
| `intent_id`                  | UUID FK     | Matching intent                     |
| `language_code`              | VARCHAR(12) | te / en                             |
| `response_status`            | VARCHAR(30) | SUCCESS / NO_RESULTS / UNKNOWN_DATA |
| `template_text`              | TEXT        | Answer pattern                      |
| `required_placeholders_json` | JSON        | Valid response variables            |
| `is_active`                  | BOOLEAN     | Enabled                             |

Example Telugu response template:

```
{destination} కు వెళ్లే తదుపరి {bus_type} బస్సు
{departure_time} కు బయలుదేరుతుంది.
ప్లాట్‌ఫామ్ నంబర్ {platform_number}.
```

The response renderer must use only verified database values, escape unsafe text and handle missing fields without inventing placeholders.

### H7. `conversation_sessions`

`id`, `station_id` FK nullable, `operator_id` FK nullable, `language_code`, `started_at`, `last_activity_at`, `session_status`, `expires_at`.

### H8. `conversation_messages`

`id`, `session_id` FK, `sequence_number`, `speaker`, `message_text`, `detected_intent_id` FK nullable, `confidence`, `created_at`.

Avoid storing raw audio by default. Keep conversation data only for the configured retention period.

### H9. `conversation_context`

| Column                   | Type                 | Description                |
| ------------------------ | -------------------- | -------------------------- |
| `session_id`             | UUID PK/FK           | Session                    |
| `origin_station_id`      | UUID FK nullable     | Current source             |
| `destination_station_id` | UUID FK nullable     | Current destination        |
| `travel_date`            | DATE nullable        | Requested travel day       |
| `time_preference`        | VARCHAR(50) nullable | Morning, evening           |
| `bus_category_id`        | UUID FK nullable     | Selected category          |
| `ac_preference`          | BOOLEAN nullable     | AC filter                  |
| `sleeper_preference`     | BOOLEAN nullable     | Sleeper filter             |
| `passenger_count`        | SMALLINT nullable    | Requested seats            |
| `last_intent_id`         | UUID FK nullable     | Previous intent            |
| `last_trip_id`           | UUID FK nullable     | Current referenced trip    |
| `context_json`           | JSON                 | Additional validated slots |
| `updated_at`             | TIMESTAMPTZ          | Last update                |

### H10. `enquiry_execution_logs`

`id`, `session_id` FK nullable, `intent_id` FK nullable, `execution_status`, `duration_ms`, `result_count`, `data_source_id` FK nullable, `created_at`.

Do not log unrestricted passenger text or personal identifiers unnecessarily.

## I. Imports, validation and administration

### I1. `data_sources`

`id`, `operator_id` FK nullable, `source_name`, `source_type`, `trust_level`, `is_official`, `is_demo`, `last_verified_at`.

### I2. `data_import_batches`

`id`, `source_id` FK, `entity_type`, `filename`, `checksum`, `import_status`, `total_rows`, `successful_rows`, `failed_rows`, `started_at`, `completed_at`.

### I3. `data_quality_issues`

`id`, `batch_id` FK nullable, `entity_type`, `record_id` nullable, `issue_code`, `severity`, `description`, `resolution_status`, `created_at`.

### I4. `admin_users`

`id`, `username`, `password_hash`, `is_active`, `created_at`.

### I5. `admin_roles`

`id`, `role_code`, `description`.

### I6. `admin_user_roles`

`user_id` FK, `role_id` FK, `operator_id` FK nullable.

### I7. `audit_logs`

`id`, `actor_user_id` FK nullable, `entity_type`, `entity_id`, `operation`, `old_values_json`, `new_values_json`, `changed_at`.

Sensitive values must be redacted from audit logs.

# 4. Important database relationships

Conceptual operational relationship

RTC Operator

Route → Route Variant → Ordered Stops

Recurring Service + Calendar

Dated Trip + Assigned Vehicle

Fares

Seats

Live Status

RTC Enquiry Query Engine

The NLP system extracts structured parameters and calls the same enquiry engine. It does not generate its own bus facts.

## 5. Essential constraints and indexes

| Table                         | Constraint / index                                            |
| ----------------------------- | ------------------------------------------------------------- |
| `transport_operators`         | Unique operator code                                          |
| `bus_stations`                | Unique station code within its namespace                      |
| `place_aliases`               | Normalized alias lookup; allow ambiguities across places      |
| `bus_service_categories`      | Unique operator/category code                                 |
| `vehicles`                    | Unique registration number where applicable                   |
| `route_stops`                 | Unique variant + sequence; indexed station lookup             |
| `service_calendar_exceptions` | Unique service + date                                         |
| `service_stop_times`          | Unique service + route stop                                   |
| `trips`                       | Unique service + operating date, with exception policy        |
| `trip_stop_times`             | Unique trip + route stop                                      |
| `fare_rules`                  | Prevent conflicting active rules at the same specificity      |
| `platform_assignments`        | Prevent overlapping active assignments for the same trip/stop |
| `nlp_intents`                 | Unique intent code                                            |
| `conversation_messages`       | Unique session + sequence number                              |

For station search, maintain normalized Unicode aliases and suitable indexes. PostgreSQL can use trigram indexes; SQLite can use precomputed normalized search keys and an appropriate FTS implementation. Keep both paths functionally equivalent.

Crucially, the system must support boarding at intermediate stations. A service originating in Vijayawada and terminating in Nellore may still be relevant to a passenger boarding at Guntur, provided boarding is permitted and the stop time is valid.

## 6. Data rules the engine must enforce

| Scenario                                   | Correct database behaviour                                         |
| ------------------------------------------ | ------------------------------------------------------------------ |
| Passenger asks for next bus at 11:55 PM    | Consider remaining departures and next-day services                |
| Passenger says "Vizag"                     | Resolve through aliases to Visakhapatnam                           |
| Passenger says "Tirumala"                  | Do not substitute Tirupati without explicit route/connection logic |
| Passenger asks "AC buses only"             | Filter by actual service/vehicle configuration                     |
| Bus is delayed                             | Show scheduled and estimated times separately                      |
| Platform is unknown                        | Return `UNKNOWN`, not Platform 1                                   |
| Fare expired yesterday                     | Do not use as today's applicable fare                              |
| Bus has 40 seats but no inventory feed     | Do not claim 40 seats are available                                |
| Bus passes through Ongole without stopping | Do not offer boarding at Ongole                                    |
| Passenger asks "last bus"                  | Apply the correct service day and cutoff policy                    |
| Passenger asks for cheapest bus            | Compare fares for the same valid travel segment                    |
| Operator data has not been refreshed       | Show the data source and last verified time                        |

## 7. Example database enquiry output

For a next-bus enquiry, the backend should return a standardized structure.

```

{
  "intent": "NEXT_BUS",
  "query": {
    "origin": "Vijayawada PNBS",
    "destination": "Nellore",
    "bus_type": "SUPER_LUXURY",
    "travel_date": "2026-11-08"
  },
  "results": [
    {
      "service_number": "DEMO-102",
      "operator": "APSRTC",
      "category": "Super Luxury",
      "scheduled_departure": "2026-11-08T14:30:00+05:30",
      "estimated_departure": null,
      "arrival": "2026-11-08T20:00:00+05:30",
      "fare": {
        "amount": 450.00,
        "currency": "INR",
        "status": "DEMO"
      },
      "platform": null,
      "platform_status": "UNKNOWN",
      "availability": "UNKNOWN",
      "data_source": "DEMO",
      "last_verified_at": null
    }
  ]
}

```

All numbers, timings and fares in this example are fictional demonstration values.

## 8. Implementation requirements for Codex

The schema above should be implemented incrementally, not by deleting the existing 10 tables reported in the Phase 1 README.

Codex should first inspect the actual existing SQLAlchemy models and migration history, then prepare a compatibility matrix and create additive Alembic migrations.

The correct implementation sequence is:

1. Geography, operators, stations and aliases.
2. Bus classifications, vehicles, routes and stops.
3. Services, calendars, dated trips and stop times.
4. Fares, concessions, inventory and operational data.
5. NLP reference tables, conversations and administrative auditing.
6. Constraints, indexes, migration tests and database verification.

Phase 1A acceptance standard: every foreign key must resolve; all migrations must work on fresh and existing databases; SQLite and PostgreSQL must pass equivalent schema tests; seed data must be clearly marked DEMO; and the schema must support the 25 original enquiries without changing its core structure.

This is the database foundation I would finalize before proceeding with Phase 1B — the actual enquiry query engine.