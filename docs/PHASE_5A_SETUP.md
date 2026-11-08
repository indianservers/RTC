# Offline operational data management

Run `start-rtc.ps1 -Production`, then open `http://127.0.0.1:8000/admin`. The launcher applies migrations and serves the built frontend locally. Keep the transient root capability private. Set `RTC_ADMIN_TOKEN` explicitly for a managed installation. Production defaults to publication-required mode; do not set `RTC_ALLOW_DEMO_DIRECT_WRITES=1` on an operational installation.

## Local access and independent review

Use **Access & approvals** as root to issue a named EDITOR and a separate APPROVER for selected operators. Copy each one-time capability to its authorized local user; only its hash is stored. Revoke access through that screen. Root can explicitly issue a global APPROVER to review shared station/geographic or initial operator configuration changes. An ordinary operator approver cannot edit global master definitions, provision users, approve its own draft, or alter another operator's data. Root cannot self-approve either.

Choose **Managing operator** and **Import / change source** before editing. Shared reference records are maintained by root and reviewed independently. Existing DEMO records remain DEMO. Creating a source or naming an import official does not establish official provenance; reviewed source metadata and authorized approval are required. GPS and other unavailable feeds stay unknown.

For initial APSRTC configuration, select **Stage APSRTC configuration** in Overview. It creates an unpublished operator/category-name bundle from the project request only. Validate and have a different globally authorized reviewer approve it. No schedules, fares, facilities, seat inventory or platform facts are generated. If APSRTC already exists, maintain its categories through the normal editor.

## Import and publication

1. Download the CSV template and JSON schema for the selected resource in **Data Imports**. Replace fictional example values and local reference IDs; do not treat format examples as valid operational data.
2. Upload UTF-8 CSV or one-sheet XLSX. CSV with BOM is supported. XLSX formulas, external links, unsupported files, oversized ZIP expansion and malformed headers are rejected locally.
3. Map nonstandard column names explicitly. Default mode is insert-only. To update existing rows, select update mode and supply `record_id`; disappearance from the file never deletes a record.
4. Validate and inspect row errors and before/after preview. Invalid bundles remain unpublished and leave live records unchanged. Fix the source and create a corrected draft, or archive the invalid one. No partial commit is offered.
5. A separate approver reviews the validated revision. Authorized publication rechecks current data; stale or conflicting changes fail rather than silently overwrite newer records.
6. Verify using passenger search/enquiry with the relevant travel date. The Import Center links to verification and audit records. New aliases need no model retraining.
7. Request rollback only when eligible. It restores previous values or soft-deactivates newly created records, appends history, and refuses to overwrite later changes or break foreign-key dependencies.

Files are limited to 10 MB and 10,000 rows, XLSX expanded data to 40 MB/1,000 archive entries. Preview displays the first 100 changes; validation covers the full bundle. Exports are scoped CSV, maximum 10,000 records per export; spreadsheet formula-leading strings are escaped. Imports are synchronous local transactions, not resumable distributed jobs. Split larger datasets into dependency-ordered batches. API import timeout is three minutes; inspect history before retrying an interrupted request.

Use existing local IDs from master screens/exports for foreign keys. A route/stop or variant bundle can refer to explicit UUIDs within the same draft through `POST /api/v1/admin/data/changes`. Parent commands must precede dependent commands. The route editor creates these bundles automatically. Publish a new route before selecting it in a separate service draft.

## Editors and data semantics

Route & stop editor supports direction and ordered cumulative distances, separate arrival/departure elapsed minutes and explicit boarding/alighting permissions. New stops do not automatically permit boarding. Select at least two published stops to create a variant, or duplicate an existing variant. Editing stops does not imply a passing location is a boarding point.

Timetable editor edits service-specific elapsed offsets and can shift the complete schedule. Times exceeding 1,440 minutes represent later service days; the maximum is 10,079 minutes. Calendar preview uses actual weekdays, exceptions, effective windows and trips. Service copies retain configured schedules/calendars, without copying verified operational events.

Fare tables/rules and segment fares use Decimal, effective dates, operator/category scope and explicit surcharges. Fare Preview can calculate from a validated draft without publishing it. Conflicting rules are rejected; absent prices remain unknown. A trip-specific amount is an exact override, not an extra surcharge. Concession schemes/criteria are managed separately; preview does not assume a passenger qualifies.

Service Exceptions uses `exception_type`, `reason` and JSON `details`. Supported values: ADDED_SERVICE, CANCELLED_SERVICE, TEMPORARY_SUSPENSION, FESTIVAL_EXTRA, CHANGED_DEPARTURE, ROUTE_DIVERSION, PARTIAL_STOP_CANCELLATION, BOARDING_RESTRICTION. Check the generated schema and validation response for permitted details. Exceptions are dated in the service's local calendar. Operational platform/delay/stop observations require timezone-aware effective/expiry timestamps and source/verification metadata.

Data Quality queries current records. Its affected-record links open editors/import batches. **Issue resolution** maintains recorded source issues and the `resolved` flag through the same publication workflow; generated integrity findings disappear only after the underlying data is corrected. Audit History filters actual immutable change entries with batch, actor and before/after values.

## API and database operation

OpenAPI: `/docs`. Existing `/api/v1/admin/{resource}` CRUD is reused. New actions are under `/api/v1/admin/data/*` and `/api/v1/admin/imports/*`: templates, uploads, mapping, change sets, validation, approval, publication, archive, rollback, audit, previews, copies, scoped exports and local access. Root user tokens/hashes are excluded from exports.

Migrations 0011–0014 extend existing tables; no old migration needs editing. Back up the database before upgrading. SQLite uses a real BEGIN before validation savepoints and BEGIN IMMEDIATE for mutations; it serializes writers. PostgreSQL uses transaction/savepoint semantics plus a database-wide transaction advisory lock for publication/rollback. This deliberately serializes operational publications to detect stale edits safely; throughput under many simultaneous operators has not been load-certified. Readers continue using published tables while drafts remain JSON payloads in existing import batches.

To reproduce tests on a dedicated local PostgreSQL instance:

```powershell
$env:RTC_TEST_POSTGRES_URL='postgresql+psycopg://USER@127.0.0.1:PORT/rtc_phase5a_tests'
python scripts/verify_data_migrations.py
python -m pytest backend/tests/test_data_management.py -q
python -m pytest backend/tests -q
ruff check backend scripts training
python -m mypy backend/app --ignore-missing-imports
npm --prefix frontend run lint
npm --prefix frontend run build
Set-Location frontend
npm test
```

PostgreSQL tests require the explicit dedicated database name, create isolated random schemas and clean them afterward. Without that URL PostgreSQL cases are skipped; a skipped run is not PostgreSQL verification. Browser tests use temporary SQLite databases on ports 8020 (explicit demo compatibility) and 8021 (strict publication) and block non-local traffic. They never import into `rtc.db`.

The verification machine downloaded official [EDB PostgreSQL Windows binaries](https://www.enterprisedb.com/download-postgresql-binaries) for an isolated loopback-only test server; no Windows service or production PostgreSQL deployment is configured by this task. Model download/setup is separate from runtime. No speech work, model retraining, cloud APIs, CDN or telemetry was added.
