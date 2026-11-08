# RTC OFFLINE AI — PHASE 5B
## Real-Time Bus Stand Operations, Dispatcher Console & Passenger Status Integration

You are a senior transport operations architect, backend engineer, event-driven systems specialist, database engineer and React full-stack developer.

Continue development in the EXISTING RTC Offline AI repository.

Previous phases:
- Phase 1: Database and core enquiry engine.
- Phase 2: English NLP and conversation intelligence.
- Phase 3: Journey planning and advanced enquiries.
- Phase 4: Passenger app and admin interface.
- Phase 5A: RTC data import, validation, approval and publication.

Your task is to build a fully functioning, locally operated Bus Stand Operations Control Center.

The system must manage real operational events and immediately expose those updates to passenger enquiry APIs.

## NON-NEGOTIABLE REQUIREMENTS

- English text only.
- No voice, microphone, speech recognition or TTS.
- No GPT or cloud AI services.
- No external transport APIs.
- All operations must work on the local database.
- Use existing React, FastAPI and SQLAlchemy infrastructure.
- Preserve existing migrations and API compatibility.
- Reuse operational tables and modules where available.
- No duplicate trip-status or platform-assignment systems.
- All operational changes must be authorized and audited.
- No invented GPS positions or actual arrival times.
- Clearly distinguish DEMO from verified operator data.

Do not assume earlier phases are complete. Inspect the actual repository before implementing.

---

# 1. AUDIT EXISTING OPERATIONAL FUNCTIONALITY

Inspect:
- Trip status models
- Dated trip instances
- Scheduled stop times
- Operational events
- Platform assignments
- Delay records
- Service disruptions
- Source provenance
- Admin authorization
- Passenger enquiry APIs
- WebSocket infrastructure
- Admin UI components

Create a concise gap matrix.

Reuse existing implementations.

Do not create conflicting representations of trip status.

# 2. OPERATIONS CONTROL CENTER

Create a main admin page:

Operations Control Center

Include:
- Current bus stand selector
- Operator selector
- Service date selector
- Arrivals tab
- Departures tab
- Delayed services tab
- Cancelled services tab
- Platform board tab
- Disruptions tab
- Event history tab

Show genuine database-derived counts:
- Scheduled arrivals
- Scheduled departures
- Delayed trips
- Cancelled trips
- Arrived trips
- Departed trips
- Platform assignments awaiting confirmation

Use compact layouts with searchable, sortable tables.

Use visual indicators without relying solely on color.

# 3. LIVE ARRIVAL AND DEPARTURE BOARD

Create a professional digital bus stand board.

Columns:
- Service number
- Destination/origin
- Bus category
- Scheduled time
- Estimated time
- Actual time
- Platform
- Status
- Last update

Support:
- Search
- Operator filtering
- Time-window filtering
- Category filtering
- Station filtering
- Automatic local refresh
- WebSocket updates
- Manual refresh fallback

Do not infer arrival merely because scheduled time has passed.

If no operational event exists, show SCHEDULED or UNKNOWN according to the actual data.

# 4. TRIP STATUS STATE MACHINE

Implement or strengthen:

TripOperationalStateMachine

Supported states:

SCHEDULED
BOARDING
READY
DELAYED
ARRIVED_AT_STOP
DEPARTED_FROM_STOP
IN_TRANSIT
COMPLETED
CANCELLED
SUSPENDED

Use a trip-level state and stop-level events as appropriate.

Not every state is globally mutually exclusive.

For example, a trip may be delayed and currently boarding.

Use a validated operational state model, avoiding a single simplistic enum when orthogonal dimensions are necessary.

Implement transition rules.

Examples:
- Scheduled → Boarding
- Boarding → Departed
- Scheduled → Cancelled
- Delayed → Boarding
- Arrived at intermediate stop → Departed from that stop

Prevent contradictory transitions and invalid event ordering.

Allow authorized corrections with recorded reason and audit history.

# 5. DISPATCHER QUICK ACTIONS

For each relevant trip, provide:

- Assign platform
- Change platform
- Mark boarding
- Mark arrived
- Mark departed
- Set revised ETA
- Report delay
- Add delay reason
- Cancel trip
- Suspend trip
- Reinstate service
- Add operational notice
- Correct previous update

Use fast dialogs and context-aware actions.

Require appropriate confirmation for disruptive changes.

All mutation APIs must be authenticated and operator/station scoped.

# 6. PLATFORM MANAGEMENT

Create a platform assignment console.

Support:
- Platform list
- Active assignments
- Upcoming assignments
- Platform occupancy status
- Assignment conflicts
- Platform reassignments
- Change history

Validate overlapping assignments.

Distinguish:
- Planned platform
- Dispatcher-confirmed platform
- Actual boarding platform if recorded

Do not claim a platform is confirmed merely because an initial schedule suggests one.

When reassigned:
- Store previous and new platform.
- Record the actor and reason.
- Update the passenger departure board.
- Invalidate affected cached enquiry results.
- Publish a local event.

# 7. DELAY AND ETA MANAGEMENT

Support:
- Scheduled arrival/departure
- Revised estimated arrival/departure
- Actual arrival/departure
- Delay duration
- Delay reason
- Confidence/source
- Verification time
- Freshness status

Dispatcher may manually enter a revised ETA.

Never automatically generate an ETA based only on historical averages and present it as verified.

If ETA estimation is later implemented, label it as PREDICTED with its method and confidence.

Allow updates at intermediate stops where applicable.

# 8. CANCELLATION AND REINSTATEMENT

Implement:
- Trip cancellation
- Cancellation reason
- Timestamp
- Affected boarding points
- Reinstatement with authorized approval
- Event history
- Passenger-facing status

Cancelled trips must not appear as available departures.

They may appear in a separate cancelled-services result when specifically requested.

When a trip is reinstated, validate its timetable, platform and other affected operational fields.

# 9. SERVICE DISRUPTIONS

Create a disruption management page.

Support:
- Road closure
- Route diversion
- Station closure
- Stop suspension
- Festival crowd management
- Weather-related suspension
- Service interruption
- Other operator-defined operational events

Fields:
- Operator
- Affected routes/services/trips/stations
- Start time
- End time
- Severity
- Description
- Verification status
- Publishing user
- Data source

Only approved disruptions should appear in standard passenger enquiries.

Do not infer weather or traffic conditions without locally verified input.

# 10. EVENT-SOURCED AUDIT HISTORY

Use append-only operational events where feasible.

Each event must include:
- Event ID
- Trip/stop reference
- Event type
- Previous value
- New value
- Actor
- Operator
- Station
- Source
- Occurred time
- Recorded time
- Reason
- Idempotency key

Use transactional updates for current-state projections.

Avoid losing historical events when current state changes.

Protect against duplicate operator submissions.

# 11. LOCAL REAL-TIME UPDATES

Implement local WebSocket or suitable Server-Sent Events infrastructure.

Publish events for:
- Trip status change
- Delay update
- Platform change
- Cancellation
- Reinstatement
- Disruption publication

Client applications must:
- Reconnect after temporary local connection loss.
- Avoid duplicate events.
- Re-fetch authoritative state after reconnect.
- Ignore stale/out-of-order events using version numbers.
- Display an appropriate disconnected state.

Use the local network only.

Do not require Redis or cloud message brokers for a single-server setup.

# 12. PASSENGER ENQUIRY INTEGRATION

Update existing RTC enquiry services to consume operational projections.

Examples:

"Has the Tirupati bus arrived?"
→ Check verified stop arrival events.

"Is the Nellore bus delayed?"
→ Compare scheduled and approved estimated departure.

"Which platform is my bus on?"
→ Return the latest valid platform assignment.

"Has the Vizag bus already left?"
→ Check actual departure event where available.

"Is the 8 PM service cancelled?"
→ Return the relevant trip cancellation status.

If no verified operational information exists, respond with an explicit UNKNOWN or SCHEDULED_ONLY status.

Do not use the current clock alone to infer that a bus has departed.

# 13. JOURNEY PLANNER INTEGRATION

When a trip is cancelled:
- Exclude it from available journey recommendations.
- Recalculate connecting journeys when requested.

When a verified delay affects a connection:
- Recheck transfer feasibility.
- Avoid recommending connections that are no longer possible.

When the event is stale or incomplete:
- Preserve uncertainty and warn accordingly.

Reuse Phase 3B planning logic.

# 14. PASSENGER ANNOUNCEMENT TEMPLATES

Generate text announcements for:
- Delayed service
- Platform change
- Cancellation
- Boarding started
- Arrival
- Departure
- Service reinstatement

Use locally configured English templates.

Example:

"Attention passengers: Service {service_number} to {destination} will now depart at {estimated_time} from Platform {platform}."

Only insert verified operational fields.

If a required value is unknown, use a safe alternative template rather than inventing it.

Do not add voice output.

Allow authorized dispatcher review before publishing announcements.

# 15. AUTHORIZATION AND SAFETY

Implement backend-enforced roles such as:
- Operations Viewer
- Dispatcher
- Station Supervisor
- Operator Administrator
- System Administrator

Restrict mutations by:
- Operator
- Station
- Role
- Trip scope

Record actor identity for every operation.

Protect critical actions from accidental double submission.

Use optimistic concurrency control or version checking for simultaneous updates.

# 16. REST API

Reuse existing APIs or implement appropriate endpoints.

Suggested:

GET /api/v1/operations/board
GET /api/v1/operations/trips
GET /api/v1/operations/trips/{id}
POST /api/v1/operations/trips/{id}/events
POST /api/v1/operations/trips/{id}/platform
POST /api/v1/operations/trips/{id}/delay
POST /api/v1/operations/trips/{id}/cancel
POST /api/v1/operations/trips/{id}/reinstate
GET /api/v1/operations/events
GET /api/v1/operations/disruptions

Use typed requests and responses.

Do not duplicate existing routes with different names.

# 17. DATA QUALITY CHECKS

Validate:
- Actual departure earlier than recorded arrival at the same stop
- Conflicting status events
- Stale ETA
- Duplicate event IDs
- Platform assignment conflicts
- Invalid station/trip references
- Unauthorized station update
- Cancellation followed by invalid active-state transitions
- Impossible stop event order
- Missing provenance

Flag suspicious data for correction rather than silently rewriting history.

# 18. OFFLINE REQUIREMENTS

The Operations Control Center must work when the public internet is unavailable.

All components:
- Local React assets
- Local FastAPI backend
- Local database
- Local event transport
- Local authentication
- Local audit storage

No:
- Cloud services
- External push notifications
- Remote analytics
- Third-party realtime servers

Verify offline functionality.

# 19. AUTOMATED TESTING

Implement tests covering:

1. Board displays scheduled trips.
2. Dispatcher updates a trip.
3. Delay event changes ETA.
4. Platform change updates passenger response.
5. Cancellation excludes available journey.
6. Reinstatement revalidates service.
7. Arrival event updates status.
8. Departure event updates status.
9. Intermediate stop events work.
10. Invalid transitions are rejected.
11. Duplicate events are idempotent.
12. Concurrent updates detect conflicts.
13. Operator isolation is enforced.
14. Station isolation is enforced.
15. Audit history is preserved.
16. Stale ETA is identified.
17. Missing GPS remains unknown.
18. Out-of-order events are handled.
19. WebSocket update refreshes clients.
20. Client reconnect restores authoritative data.
21. Connection search respects cancellation.
22. Passenger NLP enquiry returns updated status.
23. Invalid platform assignments are rejected.
24. Operational notices require approval.
25. Offline operation works.

Run actual database integration tests.

Add Playwright tests for dispatcher and passenger workflows.

# 20. END-TO-END ACCEPTANCE SCENARIO

Using labelled demonstration data:

1. Start the local RTC app.
2. Open Operations Control Center.
3. Select Vijayawada PNBS.
4. Open one scheduled Nellore service.
5. Mark it delayed.
6. Enter revised departure time.
7. Change platform.
8. Save approved events.
9. Open passenger enquiry.
10. Ask whether the service is delayed.
11. Verify revised departure and platform are shown.
12. Ask whether the service has departed.
13. Verify no false actual-departure claim is made.
14. Mark it departed through dispatcher console.
15. Repeat passenger enquiry.
16. Verify the actual departure status is reflected.
17. Inspect audit history.
18. Verify every change has an actor, timestamp and source.

All sample operational details must be labelled DEMO.

# 21. FINAL DELIVERABLES

Deliver:

1. Operations Control Center.
2. Arrival/departure board.
3. Trip status state machine.
4. Dispatcher quick actions.
5. Platform management.
6. Delay and ETA management.
7. Cancellation and reinstatement.
8. Disruption management.
9. Append-only operational events.
10. Local WebSocket updates.
11. Passenger enquiry integration.
12. Journey planner integration.
13. Announcement templates.
14. Authorization and audit history.
15. Automated tests.
16. Offline verification.
17. Phase 5B completion report.

Run the application and test the workflows.

Do not stop at creating UI pages, schemas or documentation.

At completion report:
- Files created/modified
- Working operational actions
- Passenger APIs integrated
- Tests executed and results
- Known limitations
- Data integrity issues resolved

If major acceptance criteria remain incomplete, report PHASE 5B INCOMPLETE.

Do not begin Phase 5C or voice development.

Begin implementation in the existing repository immediately.