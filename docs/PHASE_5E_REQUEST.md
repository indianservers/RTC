# RTC SMART ENQUIRY — PHASE 5E
## Complete Offline Reliability, Local Network Synchronization, Kiosk Deployment and Recovery

You are a principal systems architect, site reliability engineer, Python backend engineer, database reliability specialist, Windows/Linux deployment engineer and React full-stack developer.

Continue in the EXISTING RTC Smart Enquiry repository.

Previous development includes:
- RTC database and enquiry engine
- Offline English NLP model
- Conversation memory and dialogue intelligence
- Journey planning
- Passenger UI and admin interface
- Operational control center
- Data import and publication
- Conversation error recovery

Your task is to prepare the application for reliable continuous operation at real RTC bus stands.

This is an infrastructure and reliability phase, not a UI redesign.

## NON-NEGOTIABLE REQUIREMENTS

- 100% offline runtime.
- English text only.
- No GPT, LLM APIs, cloud services or external inference.
- No microphone, voice recognition or TTS.
- Preserve existing database, migrations and model files.
- Preserve existing passenger and admin interfaces.
- No duplicate application frameworks.
- No fake health checks or fabricated benchmark results.
- No public internet dependency.
- All operational answers must come from verified local data.
- Support both Windows development and Linux deployment where practical.

Inspect the actual repository before modifying anything.

---

# 1. COMPLETE INFRASTRUCTURE AUDIT

Inspect:

- Application startup sequence
- FastAPI runtime
- React production build
- PostgreSQL connection handling
- SQLite standalone support
- NLP model loading
- Conversation storage
- Session expiry
- Database migrations
- Background operations
- WebSocket connections
- Operational event notifications
- Logging
- Configuration
- Authentication
- Backup procedures
- Existing deployment scripts

Identify:
- Single points of failure
- Insecure defaults
- Runtime internet dependencies
- Missing recovery mechanisms
- Unbounded memory usage
- Database connection leaks
- Model-loading failures
- State synchronization problems

Create an infrastructure gap report.

Do not rewrite working modules unnecessarily.

# 2. DEFINE TWO DEPLOYMENT MODES

Implement configuration-driven deployment modes.

## MODE A — Central LAN Server

Architecture:

Local server:
- PostgreSQL
- FastAPI backend
- Trained English NLP model
- Conversation manager
- Operational event service
- Static React build

Clients:
- Passenger kiosk browsers
- Staff terminals
- Dispatcher terminals
- Admin workstations

All clients communicate through the local network.

No cloud connection is required.

The central server is the authoritative source for schedules, fares and operational changes.

## MODE B — Standalone Kiosk

Architecture:

Single local computer:
- SQLite database
- FastAPI
- NLP model
- React frontend
- Local session storage

The kiosk works without LAN or public internet.

Use a clearly documented configuration switch.

Do not silently fall back from a disconnected central LAN server to unrelated or stale local data.

# 3. ONE-COMMAND STARTUP

Create reliable startup scripts.

Windows:
start-rtc.ps1

Linux:
start-rtc.sh

Requirements:
- Detect Python environment.
- Validate required dependencies.
- Validate database connectivity.
- Validate model readiness.
- Verify required configuration.
- Start backend.
- Serve locally built frontend.
- Display application URL.
- Report clear errors.
- Prevent duplicate server instances.
- Write local structured logs.

Do not download packages or models during startup.

Do not automatically modify the database schema without an explicit controlled migration procedure.

# 4. PRODUCTION PROCESS MANAGEMENT

For Linux:
- Provide systemd service definitions.
- Automatic restart on process failure.
- Configurable resource limits.
- Graceful shutdown.
- Persistent logs.
- Explicit dependency ordering.

For Windows:
- Provide a documented service or task-scheduler startup option.
- Support automatic launch after system reboot.
- Handle graceful service shutdown.
- Prevent duplicate application instances.

Do not require the development server in production.

Use an appropriate production ASGI server configuration.

# 5. OFFLINE FRONTEND

Build and package React assets locally.

Verify:
- No external JavaScript.
- No remote CSS.
- No Google Fonts.
- No CDN icons.
- No third-party analytics.
- No remote error reporting.
- No network-dependent authentication.

All visible assets must load with internet access disabled.

Test production builds, not only the Vite development server.

# 6. OFFLINE NLP MODEL MANAGEMENT

Use the active trained English NLP model.

Requirements:
- Local model path.
- Version verification.
- Label-map compatibility.
- Lazy or controlled startup loading.
- Deterministic fallback where appropriate.
- Clear degraded status.
- No runtime downloads.
- No remote inference.

If the model fails:
- Keep essential deterministic enquiries available when supported.
- Log the failure locally.
- Show appropriate system health status.
- Never silently substitute fabricated predictions.

Do not restart the application endlessly when an optional model is unavailable.

# 7. CONVERSATION SESSION RELIABILITY

Ensure:
- Unique session IDs.
- Per-terminal isolation.
- Per-passenger reset.
- Configurable idle timeout.
- Expired session cleanup.
- No cross-session context leakage.
- Stable result selection within a valid session.
- Safe recovery after API retry.
- Atomic context updates.
- Protection against duplicate message submission.

Kiosk mode:
- Clear previous passenger context after inactivity.
- Remove prior passenger chat from the display.
- Reset selected journeys.
- Clear pending clarifications.
- Return to welcome screen.

Personal browser mode may retain an active session according to configured policy.

# 8. DATABASE RELIABILITY

For PostgreSQL:
- Connection pooling.
- Pool health checks.
- Transaction boundaries.
- Statement timeouts.
- Graceful failure handling.
- Recovery after temporary database outage.
- Explicit migration strategy.

For SQLite:
- Foreign key enforcement.
- Busy timeout.
- Appropriate WAL settings.
- Safe concurrent read/write patterns.
- Transaction handling.
- Corruption detection where available.

Do not assume SQLite and PostgreSQL have identical concurrency characteristics.

# 9. LOCAL EVENT SYNCHRONIZATION

Implement or strengthen local event broadcasting.

Events:
- Timetable published.
- Fare updated.
- Platform changed.
- Trip cancelled.
- Delay recorded.
- Service reinstated.
- Station information updated.

Clients must:
- Reconnect automatically.
- Detect missed events.
- Re-fetch authoritative state.
- Avoid duplicate processing.
- Reject outdated event versions.

Use WebSocket or SSE based on existing architecture.

Do not introduce an external message broker for a small single-server deployment unless necessary.

# 10. STANDALONE SNAPSHOT SUPPORT

For standalone mode, build versioned local data snapshots.

Snapshot contents:
- Operators
- Stations
- Aliases
- Bus categories
- Routes
- Services
- Calendars
- Stop times
- Fares
- Approved operational information

Include:
- Snapshot version
- Created timestamp
- Source
- Checksums
- Dataset schema version
- Validity period
- Import provenance

Allow verified snapshot import from a local file or authorized LAN source.

Do not mix DEMO records with official production records without explicit environment separation.

# 11. SYNCHRONIZATION CONFLICT POLICY

When reconnecting standalone kiosks:

Define clear authority:
- Central server owns published timetable/fare masters.
- Authorized dispatchers own approved operational events within their scope.
- Passenger conversation sessions remain local/private.
- Kiosk caches are not authoritative.

Use:
- Version numbers
- Idempotency keys
- Change manifests
- Conflict detection
- Controlled reconciliation

Do not blindly apply last-write-wins to operational events.

If a conflict cannot be resolved safely, flag it for administrator review.

# 12. BACKUP AND RESTORE

Implement automated local backup procedures.

Support:
- PostgreSQL backups.
- SQLite consistent backups.
- Model registry export.
- Configuration backup excluding exposed secrets.
- Published dataset manifests.
- Operational event history.

Provide:
- Backup schedule configuration.
- Backup retention policy.
- Backup integrity verification.
- Restore to isolated test environment.
- Recovery instructions.

Never assume a backup is valid just because the file exists.

# 13. SECURITY HARDENING

Implement:
- Backend-enforced admin authorization.
- Operator and station scoping.
- Strong local credentials.
- Password hashing.
- Session expiration.
- CSRF protection where applicable.
- Safe CORS configuration.
- Input validation.
- Import file-size limits.
- Rate limiting.
- Safe logging.
- Secret management.

For LAN deployments:
- Document local TLS options.
- Restrict service exposure to trusted networks.
- Avoid exposing admin endpoints publicly.
- Configure firewall rules.

Do not expose private database credentials in frontend bundles.

# 14. SYSTEM HEALTH MONITORING

Implement health endpoints:

/health/live
/health/ready
/health/dependencies

Monitor:
- API process health
- Database connectivity
- Model readiness
- Available disk space
- Memory usage
- Error rate
- Enquiry latency
- Active sessions
- Background task status
- Last successful data publication
- Event delivery status

Avoid expensive model loading on every health request.

Expose detailed diagnostics only to authorized administrators.

# 15. LOCAL OBSERVABILITY

Use structured local logs.

Include:
- Timestamp
- Correlation ID
- Component
- Error code
- Processing duration
- Model version
- Dataset version
- Data source
- Severity

Avoid retaining personal passenger information unnecessarily.

Support configurable log rotation and retention.

Do not use cloud telemetry.

# 16. PERFORMANCE AND CONCURRENCY

Benchmark:
- 1 concurrent kiosk
- 5 concurrent kiosks
- 10 concurrent kiosks
- 25 concurrent kiosks
- 50 concurrent kiosks where hardware permits

Test representative queries:
- Next bus
- Fare
- Route stops
- Connecting journey
- Multi-turn follow-up
- Selected service enquiry

Measure:
- P50 latency
- P95 latency
- P99 latency
- Requests per second
- Error rate
- CPU usage
- Memory usage
- Model inference latency
- Database query latency

Report actual server hardware and test environment.

Do not invent benchmark metrics.

# 17. FAILURE RECOVERY TESTS

Simulate:
1. API process crash.
2. Database temporarily unavailable.
3. Browser refresh.
4. Kiosk restart.
5. LAN disconnection.
6. Missed WebSocket events.
7. Duplicate message retry.
8. Expired conversation session.
9. Corrupted model checkpoint.
10. Missing model file.
11. Disk space warning.
12. Invalid snapshot.
13. Interrupted snapshot import.
14. Concurrent dispatcher updates.
15. Failed backup.
16. Restore to a new local environment.

Verify safe recovery.

Do not silently drop operational updates or falsely claim synchronization success.

# 18. END-TO-END OFFLINE ACCEPTANCE

On a real local installation:

1. Disconnect public internet.
2. Start the RTC server.
3. Open passenger interface.
4. Ask "Next bus to Nellore?"
5. Select a service.
6. Ask "What is the fare?"
7. Open dispatcher terminal.
8. Change the selected service's platform.
9. Confirm passenger enquiry uses the updated platform.
10. Restart backend.
11. Reconnect passenger terminal.
12. Verify appropriate session recovery or expiry.
13. Create a database backup.
14. Restore backup into an isolated environment.
15. Verify data integrity.
16. Run all regression tests.

Document actual observations.

Do not claim a complete offline certification if OS-level network isolation was not tested.

# 19. DELIVERABLES

Deliver:

1. Central LAN deployment mode.
2. Standalone kiosk deployment mode.
3. Windows startup scripts.
4. Linux startup scripts.
5. Production process management.
6. Offline frontend packaging.
7. Local NLP model loading.
8. Session reliability.
9. Database recovery handling.
10. Local event synchronization.
11. Versioned snapshots.
12. Conflict detection.
13. Backup and restore scripts.
14. Security hardening.
15. Local health dashboard.
16. Logging and diagnostics.
17. Concurrency benchmarks.
18. Failure recovery tests.
19. Deployment documentation.
20. Phase 5E completion report.

Run the actual application and relevant tests.

Report:
- Files changed
- Deployment modes verified
- Startup commands
- Backup/restore results
- Offline verification results
- Benchmark measurements
- Security limitations
- Remaining blockers

If major acceptance criteria remain unfinished, report:

PHASE 5E INCOMPLETE

Do not begin Phase 6 or voice development automatically.

Begin implementation immediately in the existing repository.