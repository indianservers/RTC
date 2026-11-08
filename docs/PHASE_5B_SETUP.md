# Local Bus Stand Operations Control Center

Run the migrations and production bundle through `start-rtc.ps1 -Production`. Operations console: `http://127.0.0.1:8000/admin/operations`; passenger board: `http://127.0.0.1:8000/board`. Existing passenger search/chat routes remain unchanged. Use the root capability printed by the local launcher; tokens must stay private.

## Provision staff and reference data

In **Access & approvals**, root selects an operator and creates an Operations Viewer, Dispatcher or Station Supervisor with explicit authorized stations. An Operator Administrator can be explicitly granted all stations of its named operator by leaving its station selection empty. A master-data EDITOR/APPROVER is not an operations role. A station grant for one operator never authorizes updates to another operator's trip.

Master stations, bays, services, calendars and sources still use Phase 5A validation/independent approval/publication. Create an active local source for the operator before dispatching. Source names and a verified flag do not convert DEMO data into official data. Verified operational records mean the named local actor entered an observation under that source, not that an external GPS/weather/traffic service confirmed it.

Root can stage a clearly fictional demonstration fixture using `scripts/verify_dispatcher_live.py` with `RTC_ADMIN_TOKEN` in its process environment. This script explicitly creates DEMO master data through Phase 5A review, provisions temporary named staff, runs the operational/NLP acceptance, revokes the temporary capabilities and retains DEMO records/audit as evidence. It is not an official-data seed and must not be used to create real-world operational facts. Existing sample station name is Vijayawada, not a certified physical PNBS identifier.

## Console workflow

Choose bus stand, operator, service date and board filters. **Service date is the trip's origin date**; an overnight intermediate stop may display the following calendar day. The board uses full timezone-aware timestamps, displayed in the selected station's timezone. Scheduled times in the past never prove arrival/departure.

Select **Dispatch** to open quick actions. Choose a local source and enter a reason. Observation time defaults to now; enter an earlier observation only when genuinely recorded. Event expiry is explicit. Future actual movement is rejected. Each action shows confirmation before submission. A saved action appears immediately in passenger queries and propagates to open boards through local invalidation.

For ETA/delay, enter delay minutes or a timezone-aware revised arrival/departure through the UI. Estimates are manually reported, not predictions and not actual movement. Stale estimates are not current facts. Do not select an actual boarding platform unless boarding there was observed. A dispatcher-confirmed assignment alone remains distinct from observed boarding.

Platform reservations use the entered effective/expiry interval. Overlapping confirmed reservations are rejected even for another operator's trip. Choose realistic intervals; the system does not infer automatic bay release from an assumed departure. Physical occupancy remains UNKNOWN without a dedicated actual occupancy observation.

Cancellation/suspension removes the trip from normal journey recommendations. Reinstatement is two steps: a dispatcher requests it; a different supervisor approves after timetable/platform validation. A departed trip cannot be cancelled as though it never ran; publish a service interruption notice instead. Corrections require a supervisor, reason and the latest event ID at that station. They append history and supersede derived observations; older events are not edited.

Disruptions and announcements also use request then different-supervisor publication. Pending requests and preview text are visible in the current-trip details. Use the request idempotency key for publication and the event ID for corrections. The UI and API support affected service/route/trip selection, explicit station IDs and start/end windows. Select the request from the approval dropdown; the latest 100 reference choices are offered, with paginated APIs available for larger data sets. Changing an operational fact invalidates a pending announcement whose preview would change.

Event history includes actor, source, occurred/recorded time, previous/new values, reason and version. On a version conflict, refresh the authoritative board, inspect new events and reopen the service; do not silently overwrite another dispatcher's action. Duplicate retries using the same idempotency key and identical request replay the original result; changing the request with that key returns conflict.

## APIs and realtime

OpenAPI: `/docs`. Board reads are public passenger information. Mutations, detailed trip state, platform console, event history and operational quality require a local capability and scope. The single event endpoint is `POST /api/v1/operations/trips/{id}/events`; its types are validated by `EventInput` and `TripOperationalStateMachine`. A dated schedule is materialized with `POST /api/v1/operations/trips`; this never infers actual movement.

Core command fields: `event_type`, `station_id`, `source_id`, `expected_version`, `idempotency_key`, timezone-aware `occurred_at`/`expires_at`, `reason`, and validated `details`. Event types and permitted detail fields are documented in `backend/app/dispatch.py`. PLATFORM takes `bay_id`; ETA/DELAYED take `estimated_arrival`, `estimated_departure` and/or `delay_minutes`. Notices include `disruption_type`, `severity`, `description`, optional affected ID lists and explicit `starts_at`/`ends_at`. Publication/correction targets use `target_event_id` as described above.

`/api/v1/operations/stream?station_id=...` is a same-origin WebSocket. It exposes only ledger revision/invalidation/heartbeat, not private pending payloads or actors. Clients refetch the authoritative REST board. Revisions are monotonic while the append-only database is retained; every reconnect resets the client's transport cursor and refetches state. The console retries with bounded backoff, closes missing-heartbeat connections and also polls every 15 seconds. Manual refresh remains available. This is a single-server local mechanism, without Redis or multi-server event fan-out.

The launcher intentionally binds to loopback. A LAN deployment needs explicit host/firewall/TLS configuration and forwarding of WebSocket upgrades through any local reverse proxy; it is not enabled automatically by this task. Public internet access is unnecessary. Python wheels, npm packages and `websockets` must be provisioned before offline installation; normal runtime installs nothing.

## Verification

```powershell
$env:RTC_TEST_POSTGRES_URL='postgresql+psycopg://USER@127.0.0.1:PORT/rtc_phase5a_tests'
python scripts/verify_data_migrations.py --report docs/phase5b-migration-verification.json
python -m pytest backend/tests/test_dispatcher.py -q
python -m pytest backend/tests -q
ruff check backend scripts training
python -m mypy backend/app --ignore-missing-imports
npm --prefix frontend run lint
npm --prefix frontend run build
Set-Location frontend
npm test
```

The dedicated PostgreSQL database name is a safety requirement of the existing fixture. Each test creates/drops an isolated schema. Without that URL PostgreSQL cases skip; that is not PostgreSQL verification. Browser tests run actual FastAPI servers with temporary SQLite databases on 8020 and strict mode 8021. Operations tests use 8021 so their departure/cancellation events cannot corrupt unrelated compatibility-mode passenger fixtures on 8020.

The backend/frontend network guards block external application connections; no OS firewall isolation or packet-capture certification is claimed. The existing statistical intent candidate remains unapproved; deterministic English inference is used. No voice, microphone, TTS, model training, remote transport feed or cloud broker is part of Phase 5B.
