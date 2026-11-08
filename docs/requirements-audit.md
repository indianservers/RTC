# Requirement-by-requirement evidence register

PHASE 1 INCOMPLETE. Each original bullet or numbered requirement is retained below. Partial evidence does not close an acceptance criterion.

## Original line 21: - TGSRTC — Telangana
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 22: - TNSTC — Tamil Nadu
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 23: - MTC — Chennai
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 24: - KSRTC and other RTC operators
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 25: - Optionally private bus operators
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 38: - Python 3.12+
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 39: - FastAPI
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 40: - SQLAlchemy 2.x
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 41: - Alembic
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 42: - Pydantic v2
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 45: - PostgreSQL as the primary production database.
UNVERIFIED: PostgreSQL tests have not executed.

## Original line 46: - SQLite support for standalone offline kiosks.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 47: - Use a repository abstraction supporting both.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 48: - Avoid vendor-specific queries wherever practical.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 49: - Use timezone-aware datetime handling.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 52: - Pytest
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 53: - HTTPX
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 54: - Factory-based test fixtures
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 57: - Ruff
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 58: - Mypy
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 59: - Docker Compose
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 60: - Structured JSON logging
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 63: - No GPT, OpenAI, Gemini, Claude or cloud AI.
IMPLEMENTED by runtime source inspection; API test blocks socket.create_connection. Exhaustive network isolation remains unverified.

## Original line 64: - No external API calls.
IMPLEMENTED by runtime source inspection; API test blocks socket.create_connection. Exhaustive network isolation remains unverified.

## Original line 65: - No remote database dependencies.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 66: - No UI frameworks or frontend implementation in Phase 1.
IMPLEMENTED by runtime source inspection; API test blocks socket.create_connection. Exhaustive network isolation remains unverified.

## Original line 67: - No pretrained model downloads at runtime.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 68: - No fake responses or hardcoded RTC answers in backend logic.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 69: - No duplicated tables, services or APIs.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 70: - Use existing project structure if present; inspect before modifying.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 80: 1. states
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 81: 2. districts
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 82: 3. cities
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 83: 4. transport_operators
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 84: 5. operator_divisions
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 85: 6. depots
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 86: 7. bus_stations
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 87: 8. station_bays
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 88: 9. station_aliases
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 89: 10. city_aliases
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 92: - Use stable UUID primary keys for appropriate entities.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 93: - Provide human-readable operator and station codes.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 94: - Support multiple stations in one city.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 95: - Support common names and phonetic spellings.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 96: - Store local language names.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 97: - Do not assume all operators belong to one state.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 98: - Support inter-state routes.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 99: - Track active/inactive status.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 100: - Track latitude/longitude where available.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 101: - Support station-level timezones, defaulting to Asia/Kolkata for Indian stations.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 102: - Allow multiple operators to use the same physical bus station.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 107: - Vijayawada
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 108: - Bezawada
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 109: - విజయవాడ
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 110: - బెజవాడ
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 113: - Visakhapatnam
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 114: - Vizag
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 115: - విశాఖపట్నం
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 116: - వైజాగ్
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 119: - Tirupati
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 120: - Tirupathi
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 121: - తిరుపతి
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 124: - Tirumala
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 125: - తిరుమల
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 133: 1. bus_service_categories
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 134: 2. bus_type_aliases
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 135: 3. vehicle_types
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 136: 4. vehicles
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 137: 5. vehicle_amenities
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 138: 6. vehicle_seat_layouts
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 139: 7. vehicle_seats
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 142: - Pallevelugu
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 143: - Ultra Pallevelugu
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 144: - Express
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 145: - Ultra Deluxe
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 146: - Super Luxury
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 147: - Indra
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 148: - Amaravathi
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 149: - Dolphin Cruise
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 150: - Vennela
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 151: - Vennela Economy
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 152: - Saptagiri Express
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 153: - Green Saptagiri
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 154: - Metro Express
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 155: - Metro Luxury
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 156: - Star Liner
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 157: - Night Rider
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 158: - Garuda / Garuda Plus where applicable
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 163: - Branded service category
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 164: - Vehicle body/configuration
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 165: - AC or non-AC
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 166: - Sleeper or seater
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 167: - Electric or diesel
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 168: - Ordinary or limited-stop
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 169: - Reservation-enabled or non-reservation
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 174: - AC availability
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 175: - Sleeper/seater
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 176: - 2+2, 2+1 and other configurations
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 177: - Seating capacity
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 178: - Berth capacity
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 179: - Accessible seating
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 180: - Wheelchair support
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 181: - Luggage provision
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 182: - Charging facility
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 183: - Tracking availability
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 184: - Reservation eligibility
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 185: - Fare class
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 186: - Operator-specific classification
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 194: 1. routes
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 195: 2. route_variants
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 196: 3. route_stops
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 197: 4. route_aliases
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 198: 5. route_distance_data
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 201: - Direct routes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 202: - One-way routes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 203: - Opposite-direction routes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 204: - Circular routes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 205: - Express stop patterns
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 206: - Intermediate boarding and alighting points
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 207: - Different route variants between the same cities
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 208: - Multiple bus stands in a city
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 209: - Depot-origin services
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 210: - Inter-state routes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 213: - Sequence number
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 214: - Station/stop reference
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 215: - Distance from origin
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 216: - Scheduled offset
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 217: - Boarding permission
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 218: - Alighting permission
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 219: - Active status
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 229: 1. services
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 230: 2. service_calendars
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 231: 3. service_calendar_exceptions
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 232: 4. service_stop_times
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 233: 5. trips
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 234: 6. trip_stop_times
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 235: 7. trip_status_history
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 236: 8. extra_services
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 237: 9. service_disruptions
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 238: 10. platform_assignments
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 241: - Daily services
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 242: - Weekday-only services
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 243: - Weekend services
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 244: - Specific dates
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 245: - Festival specials
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 246: - Extra buses
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 247: - Seasonal services
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 248: - Temporary cancellations
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 249: - Delayed departures
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 250: - Changed platforms
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 251: - Route diversions
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 252: - Cross-midnight journeys
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 253: - Different departure times on different days
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 256: - Route = geographical path
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 257: - Service = recurring scheduled operation
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 258: - Trip = actual service occurrence on a particular date
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 270: 1. fare_tables
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 271: 2. fare_rules
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 272: 3. fare_stages
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 273: 4. trip_fare_overrides
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 274: 5. fare_concessions
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 275: 6. fare_concession_eligibility
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 276: 7. fare_history
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 279: - Origin-to-destination fares
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 280: - Intermediate boarding fares
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 281: - Service-category-based fares
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 282: - Distance-based fares
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 283: - Operator-specific pricing
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 284: - Child fares
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 285: - Senior citizen concessions where applicable
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 286: - Applicable women's travel schemes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 287: - Pass-based travel rules
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 288: - Temporary surcharges
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 289: - Special service fares
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 290: - Effective-from and effective-to dates
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 304: 1. trip_inventory
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 305: 2. seat_availability_snapshots
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 306: 3. reservation_channels
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 307: 4. booking_references where applicable
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 314: - Are two seats available?
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 315: - Does this bus support reservations?
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 316: - Is sleeper available?
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 317: - How many seats are currently known to be vacant?
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 320: - Available
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 321: - Not available
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 322: - Unknown
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 323: - Stale inventory
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 331: 1. vehicle_locations
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 332: 2. trip_delay_events
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 333: 3. operational_alerts
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 334: 4. data_sources
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 335: 5. data_import_batches
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 336: 6. data_quality_issues
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 337: 7. audit_logs
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 340: - Source
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 341: - Recorded timestamp
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 342: - Effective timestamp
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 343: - Freshness status
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 344: - Operator
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 345: - Affected trip/service
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 346: - Verification status
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 349: - Scheduled departure
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 350: - Estimated departure
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 351: - Actual departure
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 361: 1. nlp_intents
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 362: 2. nlp_utterances
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 363: 3. nlp_entity_types
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 364: 4. nlp_entity_aliases
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 365: 5. nlp_response_templates
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 366: 6. conversation_sessions
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 367: 7. conversation_messages
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 368: 8. conversation_context
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 369: 9. enquiry_execution_logs
PARTIAL: table exists in SQLAlchemy metadata and fresh SQLite migration. Cross-domain behavior and complete integrity requirements remain open.

## Original line 403: - Appropriate primary and foreign keys
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 404: - Unique constraints
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 405: - Database indexes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 406: - Check constraints
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 407: - Cascading policies
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 408: - Soft deletion where justified
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 409: - Created/updated timestamps
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 410: - Audit provenance
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 411: - Referential integrity
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 412: - Transaction management
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 413: - Schema migrations
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 416: - Duplicate stations
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 417: - Duplicate service numbers within applicable scope
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 418: - Invalid stop sequences
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 419: - Negative fares
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 420: - Invalid vehicle capacities
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 421: - Conflicting calendar exceptions
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 422: - Impossible temporal relationships
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 423: - Duplicate seat identifiers
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 424: - Invalid coordinates
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 436: 1. get_next_buses()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 437: 2. get_first_bus()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 438: 3. get_last_bus()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 439: 4. get_bus_fare()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 440: 5. get_available_bus_types()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 441: 6. get_service_details()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 442: 7. get_route_stops()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 443: 8. get_journey_duration()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 444: 9. get_arrival_time()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 445: 10. get_platform_assignment()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 446: 11. get_seat_availability()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 447: 12. get_service_status()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 448: 13. get_cheapest_services()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 449: 14. get_fastest_services()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 450: 15. get_direct_services()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 451: 16. get_connecting_services()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 452: 17. get_services_via_stop()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 453: 18. get_operator_services()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 454: 19. get_concessions()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 455: 20. get_station_facilities()
PARTIAL: working database-backed method in backend/app/enquiry.py; API coverage test passes. Complete typed responses and all filter combinations remain open.

## Original line 462: - Accept validated structured parameters.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 463: - Resolve station and operator IDs.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 464: - Return structured typed responses.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 465: - Include source and timestamp metadata where relevant.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 466: - Handle unknown data gracefully.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 467: - Support optional bus category and amenity filters.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 468: - Preserve correct dates and timezones.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 471: - Exclude departures already passed.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 472: - Include appropriate cross-midnight services.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 473: - Respect cancelled service instances.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 474: - Return chronological results.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 475: - Differentiate scheduled and estimated departures.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 478: - Clarify the operating-day boundary.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 479: - Do not accidentally return the next day's early-morning service.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 482: - Use actual origin and destination boarding stages.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 483: - Apply fare validity periods.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 484: - Return available fare classes and concession eligibility separately.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 487: - Respect stop sequences.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 488: - Require a realistic configurable minimum transfer window.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 489: - Avoid returning journeys that arrive after their connecting service departs.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 490: - Cap transfers and search complexity.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 519: - Consistent response envelopes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 520: - Typed validation errors
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 521: - Pagination
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 522: - Search limits
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 523: - Appropriate HTTP status codes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 565: - At least 100 demo scheduled services
IMPLEMENTED: idempotent 100-service fictional seed; test_seed_idempotent.

## Original line 566: - Multiple bus categories
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 567: - Different daily and weekly calendars
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 568: - Overnight services
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 569: - Intermediate stops
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 570: - Fare stages
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 571: - Scheduled journeys
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 572: - A few documented cancellations and platform changes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 573: - Multiple variants between selected destinations
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 582: - Operators
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 583: - Cities and stations
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 584: - Bus categories
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 585: - Routes and stops
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 586: - Schedules
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 587: - Fares
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 588: - Calendar exceptions
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 591: - Schema validation
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 592: - Duplicate detection
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 593: - Referential validation
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 594: - Dry-run preview
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 595: - Row-level errors
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 596: - Transaction rollback
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 597: - Import provenance
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 598: - Safe repeat imports
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 609: - Next bus
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 610: - Last bus
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 611: - First bus
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 612: - Fare calculation
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 613: - Bus-type filtering
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 614: - Route stop ordering
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 615: - Same-day services
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 616: - Tomorrow's services
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 617: - Overnight journeys
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 618: - Cancellations
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 619: - Platform changes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 620: - Unknown fare
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 621: - Unknown seat availability
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 622: - Service calendar exceptions
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 623: - Connecting journeys
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 624: - Duplicate imports
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 625: - Cross-operator routes
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 626: - Unicode Telugu aliases
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 627: - PostgreSQL and SQLite compatibility
UNVERIFIED: PostgreSQL tests have not executed.

## Original line 632: - 11:59 PM
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 633: - 12:00 AM
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 634: - 12:01 AM
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 643: - Origin station
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 644: - Destination station
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 645: - Departure date/time
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 646: - Operator
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 647: - Service category
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 648: - Route stops
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 649: - Service calendar lookup
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 694: 1. Complete working backend.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 695: 2. PostgreSQL and SQLite support.
UNVERIFIED: PostgreSQL tests have not executed.

## Original line 696: 3. All necessary migrations.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 697: 4. Seed data.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 698: 5. Fully implemented enquiry services.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 699: 6. REST API.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 700: 7. Import services.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 701: 8. Automated tests.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 702: 9. Database ER diagram (Mermaid or equivalent).
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 703: 10. Architecture documentation.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 704: 11. Example API requests/responses.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 705: 12. Working local startup instructions.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 706: 13. Database verification script.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 707: 14. Short Phase 1 completion report.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 713: - Migrations work on a fresh database.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 714: - Seed data loads successfully.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 715: - All core enquiry functions return valid results.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 716: - All major entities have necessary referential constraints.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 717: - The API runs without internet.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 718: - PostgreSQL and SQLite tests pass.
UNVERIFIED: PostgreSQL tests have not executed.

## Original line 719: - There are no hardcoded passenger answers.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 720: - Date and time boundary tests pass.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 721: - Demo data is clearly distinguished from verified data.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 722: - Import validation and rollback work.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 723: - The backend can support an NLP model without restructuring its core API.
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 738: - Files created/modified
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 739: - Schema implemented
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 740: - Enquiry APIs completed
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 741: - Tests executed and results
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 742: - Known limitations
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.

## Original line 743: - Phase 2 integration readiness
OPEN/PARTIAL: not independently established against full requirement; README lists implemented capabilities and remaining gaps.
