# RTC OFFLINE AI — PHASE 5A
## Enterprise RTC Data Management, Imports & Timetable Administration

You are a senior transport operations architect, database engineer, data-quality specialist, Python backend engineer and React full-stack developer.

Continue development in the EXISTING RTC Offline AI repository.

Previous phases:
- Phase 1: Database architecture and enquiry services.
- Phase 2: English NLP model and conversation engine.
- Phase 3: Advanced conversation and journey planning.
- Phase 4: Passenger interface, administration and usability optimization.

Your task is to build a production-grade RTC operational data management system.

Initial operator: APSRTC.
Future operators: TGSRTC, TNSTC, MTC and other regional transport corporations.

## NON-NEGOTIABLE REQUIREMENTS

- English text only.
- No voice or Telugu AI development.
- No GPT, cloud AI or external data dependencies.
- Fully offline runtime.
- Preserve existing database models and migrations.
- Reuse existing admin components and APIs.
- No duplicate tables or endpoints.
- All imported data must be validated.
- Do not use fictional operational records as official RTC data.
- Maintain audit history and source provenance.
- Do not automatically publish incomplete or invalid data.

---

# 1. AUDIT EXISTING DATA MANAGEMENT

Inspect existing:
- Operators
- Stations
- Station aliases
- Bus categories
- Vehicles
- Routes
- Route stops
- Services
- Calendars
- Stop times
- Fares
- Platform assignments
- Operational events
- Import services
- Admin APIs
- Admin UI
- Data quality functionality

Create an implementation gap matrix.

Reuse existing functionality.

Do not recreate working modules.

## 2. CENTRAL RTC DATA MANAGEMENT

Create or improve an operator-scoped data management interface.

Navigation:

Overview
Operators & Depots
Stations & Bays
Bus Types
Routes & Stops
Services
Timetables
Fares & Concessions
Platforms
Service Exceptions
Operational Updates
Data Imports
Data Quality
Audit History

Use a professional, compact enterprise UI.

Support:
- Search
- Sorting
- Filtering
- Pagination
- Add
- Edit
- View
- Deactivate
- Duplicate detection
- Bulk actions where safe
- Import/export
- Validation
- Audit history

All write operations must enforce backend authorization.

## 3. IMPORT CENTER

Build a unified Import Center.

Support:
- CSV
- XLSX using a locally installed parser
- UTF-8 multilingual station names
- Multiple operators
- Large file processing
- Dry-run preview
- Row-level validation
- Duplicate detection
- Import mapping
- Import history
- Rollback where supported

Use a staged import workflow:

UPLOAD
→ MAP COLUMNS
→ VALIDATE
→ PREVIEW CHANGES
→ APPROVE
→ COMMIT
→ VERIFY

Do not commit invalid data.

Do not silently overwrite records.

## 4. STANDARD IMPORT TEMPLATES

Provide downloadable templates for:

1. Operators
2. Depots
3. Cities and stations
4. Station aliases
5. Bus categories
6. Routes
7. Route stops
8. Services
9. Service calendars
10. Stop-wise timetables
11. Fare tables
12. Fare stages
13. Concessions
14. Platforms
15. Operational events

Include:
- Required columns
- Optional columns
- Data types
- Example values
- Validation rules
- Code mappings
- Operator scope

Use clearly labelled fictional examples.

Generate templates from schema definitions so documentation and validation remain consistent.

## 5. STATION AND ALIAS MANAGEMENT

Support:
- Multiple stations in a city
- Station codes
- Telugu/English names in data
- Common spellings
- Historical names
- Tanglish aliases
- Duplicate detection
- Active/inactive stations
- Boarding restrictions
- Station bays

Preserve Tirupati and Tirumala as distinct locations.

Do not merge stations based only on fuzzy similarity.

## 6. BUS CATEGORY MANAGEMENT

Support configurable service classifications:

- Pallevelugu
- Express
- Ultra Deluxe
- Super Luxury
- Indra
- Amaravathi
- Dolphin Cruise
- Vennela
- Vennela Economy
- Saptagiri services
- Metro Express
- Metro Luxury
- Electric services
- Additional operator categories

Maintain separate characteristics for:
- Branded category
- AC/non-AC
- Sleeper/seater
- Vehicle configuration
- Reservation eligibility
- Amenities
- Accessibility

Do not assume every bus of a named category has identical facilities.

## 7. ROUTE MANAGEMENT

Build a route editor supporting:
- Origin
- Destination
- Route variants
- Ordered intermediate stops
- Stop sequence
- Distance
- Arrival/departure offsets
- Boarding permissions
- Alighting permissions
- Route direction
- Operator
- Active status

Provide:
- Add stop
- Remove stop
- Reorder stops
- Duplicate route variant
- Route validation
- Route preview

Prevent invalid stop sequences and negative distances.

Do not automatically treat a passing-through location as a boarding stop.

## 8. SERVICE AND TIMETABLE MANAGEMENT

Create a professional service editor.

Support:
- Service number
- Operator
- Route variant
- Bus category
- Depot
- Operating days
- Departure time
- Stop-wise schedules
- Overnight journeys
- Effective dates
- Reservation eligibility
- Special services
- Seasonal services
- Calendar exceptions
- Vehicle assignments where available

Provide:
- Service list
- Service detail
- Timetable editing
- Copy an existing service
- Bulk schedule updates
- Calendar preview
- Schedule validation

Handle cross-midnight journeys using absolute dates or validated elapsed offsets.

Do not calculate stop times using naive same-day assumptions.

## 9. FARE MANAGEMENT

Implement:
- Fare table creation
- Fare stage management
- Category-specific fare rules
- Origin/destination fares
- Date-effective pricing
- Trip-specific overrides
- Surcharges
- Concession schemes
- Fare history

Use Decimal.

Reject:
- Negative fares
- Invalid stages
- Conflicting active fare rules
- Invalid effective dates

Show a fare calculation preview before publishing changes.

## 10. PLATFORM MANAGEMENT

Support:
- Station
- Bay/platform
- Assigned trip
- Assignment time
- Platform changes
- Assignment source
- Last verified timestamp

Do not invent platform assignments.

Allow authorized operators to update platform information offline.

Record every change.

## 11. SERVICE EXCEPTIONS

Implement:
- Added service
- Cancelled service
- Temporarily suspended service
- Festival extra trip
- Changed departure
- Route diversion
- Partial stop cancellation
- Temporary boarding restriction

Require:
- Reason
- Effective date/time
- Operator
- User/source
- Audit history

Ensure passenger enquiries reflect approved changes immediately after publication.

## 12. DATA VALIDATION ENGINE

Validate:
- Duplicate operator codes
- Duplicate station codes
- Conflicting aliases
- Invalid route stop sequences
- Invalid calendar exceptions
- Missing service categories
- Missing timetable entries
- Negative or conflicting fares
- Invalid date ranges
- Impossible arrival/departure order
- Invalid platform references
- Missing foreign keys
- Overlapping effective records
- Unsupported operator references

Classify issues:

CRITICAL
HIGH
MEDIUM
LOW

Prevent publication when critical integrity errors exist.

## 13. DATA PUBLICATION WORKFLOW

Use:

DRAFT
→ VALIDATED
→ APPROVED
→ PUBLISHED
→ ARCHIVED

Support role-based approval.

Do not allow one operator's staff to alter another operator's records unless specifically authorized.

Ensure passenger enquiry APIs read published records only, except in explicitly configured demo/testing environments.

## 14. VERSIONING AND ROLLBACK

Maintain:
- Import batch ID
- Source checksum
- Record version
- Changed fields
- Previous values
- New values
- Effective timestamp
- Publishing user
- Approval user
- Rollback eligibility

For imports:
- Support dry-run.
- Preserve prior version.
- Apply changes transactionally.
- Provide a safe rollback mechanism.

Do not automatically delete records when they disappear from an import unless full-replacement semantics were explicitly approved.

## 15. DATA QUALITY DASHBOARD

Show actual database metrics:

- Total stations
- Total routes
- Active services
- Services missing fares
- Services missing stop times
- Unknown bus categories
- Conflicting calendars
- Missing platform assignments
- Stale updates
- Failed imports
- Unpublished changes

Provide:
- Filters
- Severity
- Affected records
- Suggested corrective action
- Owner/operator
- Resolution tracking

Metrics must be calculated from actual stored records.

## 16. NLP INTEGRATION

After publishing:
- New station aliases must become searchable.
- Updated bus types must become recognizable.
- Updated schedules must appear in passenger enquiries.
- Updated fares must be used for correct travel dates.
- Cancelled trips must be excluded from normal available services.
- Platform changes must appear in relevant enquiries.

Invalidate affected caches safely.

Do not require model retraining merely to add new station aliases or timetable data.

## 17. API REQUIREMENTS

Reuse existing admin APIs where possible.

Provide scoped endpoints for:
- Master data
- Imports
- Validation
- Publication
- Rollback
- Data quality
- Audit history

Enforce:
- Authentication
- Authorization
- Operator scoping
- Input validation
- Pagination
- Safe errors
- Request size limits
- Import limits

Do not expose destructive administrative operations to passenger users.

## 18. OFFLINE OPERATIONS

The entire data-management workflow must run locally.

No:
- CDN
- External API
- Cloud import processing
- Remote validation
- External telemetry

Support both local PostgreSQL installations and standalone SQLite where the required features are available.

Document differences in transactional and concurrency capabilities.

## 19. TESTING

Create comprehensive tests for:

1. Valid CSV import
2. Valid XLSX import
3. Invalid file type
4. Invalid headers
5. Missing required fields
6. Duplicate station
7. Duplicate service
8. Invalid route sequence
9. Invalid stop times
10. Overnight schedules
11. Calendar exceptions
12. Invalid fare
13. Overlapping fare validity
14. Platform reassignment
15. Service cancellation
16. Import dry-run
17. Import rollback
18. Partial import rejection
19. Publication approval
20. Operator permission isolation
21. Audit history
22. Cache invalidation
23. Alias search after import
24. Timetable query after update
25. Fare query after update
26. Passenger enquiry sees published records only
27. Demo provenance preservation
28. Large import handling

Run integration tests against the actual database.

Do not only mock repository methods.

## 20. FINAL ACCEPTANCE

Phase 5A is complete only when:

- Operational master data can be maintained.
- CSV/XLSX imports work.
- Validation and previews are functional.
- Approved changes publish correctly.
- Passenger enquiries reflect published data.
- Unauthorized updates are blocked.
- Audit history is preserved.
- Rollback works for supported operations.
- Data quality reports use real records.
- Existing NLP and enquiry functionality remains intact.
- The system runs entirely offline.
- Frontend and backend tests pass.

## 21. DELIVERABLES

Deliver:
1. Complete Import Center.
2. Data management screens.
3. Route and timetable editors.
4. Fare management.
5. Service exception management.
6. Approval/publication workflow.
7. Versioning and rollback.
8. Data quality dashboard.
9. Audit history.
10. Import templates.
11. Automated tests.
12. Updated documentation.
13. Phase 5A completion report.

Run the application and verify that imported data actually appears in passenger enquiries.

Report:
- Files created/modified
- Working import types
- Validation rules implemented
- Tests passed/failed
- Known limitations
- Any schema changes

Do not stop after creating UI mockups or documentation.

Begin implementation in the existing repository immediately.