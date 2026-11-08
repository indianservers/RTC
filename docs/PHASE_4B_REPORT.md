# Phase 4B implementation and verification

Verified on 8 November 2026 in the existing Windows checkout. The production application runs at http://127.0.0.1:8000 using `./start-rtc.ps1 -Production`. English text only; this delivery adds no voice, cloud inference, payments or ticket-booking integration.

## Screens improved

Passenger chat now has actual context-aware follow-ups, selected-service tracking, clarification station choices, retry, scroll-to-latest, confirmed context clearing and automatic kiosk expiry. In-flight replies cannot repopulate a reset display. Historical cards collapse and do not continually poll.

Service cards expose known fare, dates, category, source and operational freshness. Planner retains hard constraints and supports four rankings, paginated results and backend-validated two/three-journey comparison. Unknown fares cannot win a fare comparison; partial known subtotals are identified. Comparison shows differences and only awards known comparable dimension badges.

Service details have Overview, Route & Stops, Fares, Amenities and Operational Status tabs with keyboard navigation. Stop times are labelled as scheduled recurring-route offsets. Reference concessions include criteria/source without asserting eligibility or applying discounts. Unverified amenities are not presented as confirmed.

Administration includes database-wide search/sort/filter/pagination, record drawers, validated forms and confirmation dialogs. Unsupported write operations stay read-only. Data Quality audits actual records. Diagnostics presents actual inference/context/executor output. System Status distinguishes local connectivity, approved model/fallback state, sources and demo inventory.

## Components and design

Existing PageTitle, StationPicker, BusCard, JourneyCard, AdminTable and Empty components provide the requested PageHeader, StationSelector, ServiceCard, DataTable and EmptyState roles; duplicate aliases were avoided. Shared additions: SearchField, FilterBar, FareBadge, StatusIndicator, RouteTimeline, ContextualActions, LoadingSkeleton, ErrorState, ConfirmDialog, RecordDrawer and JourneyComparison. Centralized colors, borders, radius/shadow and typography retain the navy/near-white/teal system. Admin routes remain lazy-loaded.

## API integration

Existing conversation/message/reset, journeys/search/compare, admin CRUD, CSV imports, health and enquiry APIs drive the UI. Existing list responses retain data/offset/limit and gain total/search/sort/filter support. Protected UI metadata/catalog adapters expose real permissions/reference records. Added protected `/api/v1/admin/ui/data-quality` for read-only SQL validation. Service detail metadata includes operational expiry; current data is masked stale at its deadline. Actual execution traces identify JourneyPlanner.search or ExecutionPlanner.project when applicable. No migration or database table was replaced.

## Executed verification

- `python -m pytest -q`: **1,459 passed**, one Starlette/httpx deprecation warning, 240.01 seconds. Raw log: `models/benchmarks/phase4b-final-backend-pytest.txt`. This checkout also contains concurrent independent model work included in collection; the count is the actual run, not a claim that all tests were added in Phase 4B.
- Production Playwright suite: **35 passed**, zero failures/skips/flaky tests, 31.82 seconds. Actual API and temporary SQLite records; test report `docs/phase4b-playwright.json`. Covers requested categories plus reset races, unknown-fare comparison, pagination, row errors and precise operational expiry.
- `ruff check backend scripts training`: **passed** on final recheck. Earlier transient failures in concurrent training edits were resolved before this check.
- `python -m mypy backend/app --ignore-missing-imports`: **passed**, 47 source files. This is the repository-documented configuration. Unconfigured Mypy without that flag reports a missing joblib stub.
- `npm --prefix frontend run lint` and `npm --prefix frontend run build`: **passed**, including TypeScript. Build: passenger JS 427.27 kB (134.88 gzip), lazy admin JS 442.47 kB (125.91 gzip), CSS 40.78 kB (9.87 gzip).
- npm audit snapshot: **zero vulnerabilities**, `docs/phase4b-npm-audit.json`.
- Real production launch/migrations and manual browser verification: comparison, ordered stops, authenticated Data Quality, mobile kiosk; no browser errors observed. Screenshots: `phase4b-comparison.png`, `phase4b-service.png`, `phase4b-data-quality.png`, `phase4b-mobile-kiosk.png`.
- Browser tests block non-local requests; test backend rejects external socket connections. Local assets and inference paths run with offline environment settings. This is application-level network enforcement, not an OS firewall certification.

## Known limitations and unfinished coverage

- FareRule records lack expiry fields. Data Quality reports that audit as unavailable and separately checks dated segment tariffs. Rejected CSV rows are returned to the caller but are not persisted as a row-history table; only stored QualityIssue records can be audited later. These two requested historical checks remain limited by the preserved schema.
- Only the existing local administrator capability/role is supported. Enterprise identities and granular multi-role authorization are not implemented. Admin reference dropdowns currently fetch up to 100 choices; unsupported administrative domains remain read-only.
- Recurring route offsets remain the original enquiry engine timing basis; all possible ServiceStopTime override semantics and multi-timezone presentation are not added. UI display targets the Asia/Kolkata deployment.
- Data quality evaluates selected local coverage/validity rules, not comprehensive national operational correctness. Unknown versions, last-import timestamps and unverified amenities remain unknown where the database does not record evidence.
- Kiosk reset clears passenger display/context capability; it does not implement deletion of retained server conversation history. Backend reset failure is surfaced while prior text is immediately hidden.
- SQLite was exercised. This UI delivery does not claim a new successful PostgreSQL test run, OS-wide internet isolation, exhaustive assistive-technology certification or production readiness of all earlier model/backend phases.
- Runtime data remain demonstration data until an operator supplies and verifies real records. GPS/platform/inventory are never inferred from timetable data.

The final running health endpoint reports database READY and deterministic fallback READY, but overall DEGRADED because the statistical model is NOT_APPROVED. Active approved model name/version are null; the UI does not promote or invent an approved classifier.

Phase 4B functional UI delivery is implemented and regression-tested, with the explicit schema/permission/engine limitations above. Phase 4C, Telugu and voice were not started. No automatic Git commit or push was performed for this request.
