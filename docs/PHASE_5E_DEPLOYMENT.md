# Local deployment and recovery

Runtime uses installed Python packages, the existing local English model registry, a locally built React bundle and the configured database. Startup never installs software, downloads weights, seeds records or migrates the database.

## Installation and controlled migration

Install dependencies and build assets during installation, then transfer the complete environment or an approved offline wheel/package bundle to the deployment machine. Pin the deployment environment from its tested installation; `requirements.txt` retains the repository's existing version ranges. Run `npm ci` and `npm run build` inside `frontend` during packaging. Production uses Uvicorn to serve FastAPI and these built files, not Vite.

Before an upgrade, stop incoming edits, create and verify a backup with the old compatible runtime, restore it into an isolated environment and test the migration there. Only then explicitly run `python -m alembic upgrade head` on the intended database with `PYTHONPATH=backend`. Initial empty-database setup also requires this explicit command. Load DEMO seeds only in a separate demonstration installation using the existing seed modules. Startup checks the actual Alembic head and refuses a mismatch.

## Configuration and startup

Select exactly one mode with `RTC_DEPLOYMENT_MODE`:

- `standalone`: `DATABASE_URL=sqlite:///rtc.db`; default bind is `127.0.0.1:8000`. The computer serves its own kiosk browser without LAN.
- `lan`: PostgreSQL is mandatory. Set `DATABASE_URL`, `RTC_TRUSTED_HOSTS`, bind/port and the private admin capability explicitly. Clients use this server as authority. A disconnected client never changes its backend URL or switches to SQLite.

Examples are in `deployment/standalone.env.example` and `deployment/lan.env.example`. They contain no working credentials. Export variables in the service environment. On Windows the launcher can read an ignored `config/runtime.private.json`, or a path supplied in `RTC_ENV_FILE`. It is a JSON string-to-string mapping of `RTC_*` keys and `DATABASE_URL`. Explicit environment variables take precedence. Protect this file with restrictive ACLs; do not put secrets in frontend configuration, Git, command history or logs. Generate random admin capabilities with `secrets.token_urlsafe(32)`. Existing staff capabilities are high-entropy tokens stored as SHA256 digests, not human passwords; this application does not add a password-login flow.

Windows: `powershell -NoProfile -File .\start-rtc.ps1 -Production`; preflight only: `start-rtc.ps1 -Check`. `RTC_PYTHON` selects an installed environment, otherwise `.venv/Scripts/python.exe` or the current Python is used.

Linux: `bash ./start-rtc.sh`; preflight only: `bash ./start-rtc.sh --check`. `RTC_PYTHON` selects the interpreter, otherwise `.venv/bin/python` or `python3` is used.

Both execute `scripts/serve_rtc.py`. One OS-held lock per checkout prevents duplicate instances and releases after a crash. A missing optional model results in explicit degraded deterministic service, not a restart loop. Existing model approval/checksum/label-map gates are preserved. No model was promoted in Phase 5E.

## Process management

Linux templates: `deployment/rtc.service`, `rtc-backup.service`, `rtc-backup.timer`. Install under `/etc/systemd/system`, create the dedicated `rtc` account, set `/opt/rtc` ownership and restrict `/etc/rtc/runtime.env`. Configure the installed Python path, resource limits and local PostgreSQL unit name. Enable persistent journald storage. The application service restarts on failure, limits restart bursts and has a 35-second stop timeout. The backup timer runs at 02:00 and retains 14 verified packages; adjust the timer and retention command in a unit override. Templates have not been executed on Linux in this Windows-only workspace.

Windows template: explicitly run `deployment/install-windows-task.ps1` from an elevated PowerShell after installation and ACL setup. It registers a SYSTEM startup task with bounded restart attempts and IgnoreNew instance policy. SYSTEM needs access to the configured interpreter/database/config/log directories. This task was not installed on the development host. Before a planned shutdown run `stop-rtc.ps1`: the local control file requests Uvicorn graceful shutdown, including active-request drain and DB disposal. Do not use Task Scheduler's force-stop as the normal graceful path. The underlying database remains transactionally recoverable after process failure.

## Backups and isolated restore

Run `python scripts/rtc_storage.py backup --directory data/backups`. SQLite uses the consistent backup API and checks integrity/FKs. PostgreSQL uses local `pg_dump --format=custom` and validates its catalog with `pg_restore --list`. Set `RTC_PG_BIN` to the installed PostgreSQL tools directory if they are not on PATH. DB credentials are passed through a child environment, never through password-bearing command-line URLs.

The completed package contains the DB (including operational audit history and private application data), registry export, an allowlisted nonsecret configuration export and a SHA256 manifest. Treat backups as sensitive: restrict filesystem ACLs, use approved encrypted storage where required and keep secrets/active model artifacts separately secured. Registry export is not a substitute for preserving model files. Incomplete packages stay unpublished and are removed on failure.

Verify: `python scripts/rtc_storage.py verify --directory PATH_TO_PACKAGE`.

SQLite restore: `python scripts/rtc_storage.py restore --directory PATH_TO_PACKAGE --target NEW_ISOLATED_DB_PATH`. The target must not exist. A verified staged file is published with an atomic exclusive hard link. Live DBs are never overwritten. Startup against the restored copy requires explicitly changing `DATABASE_URL`; test enquiries and integrity before directing passengers to it.

PostgreSQL restore: create a new empty database, set private `RTC_RESTORE_DATABASE_URL`, then run `python scripts/rtc_storage.py restore-postgres --directory PATH_TO_PACKAGE`. Restore runs in one transaction and refuses nonempty targets. Verify row counts, constraints and enquiries before a controlled cutover. Two actual local PostgreSQL databases were used to test backup and restore; catalog verification alone is not considered a successful restore.

Prune: `python scripts/rtc_storage.py prune --directory data/backups --retain 14`. Only verified `backup-*` packages under that directory are eligible. Schedule backup, verification and prune locally (systemd timer or Task Scheduler); do not assume package existence proves recoverability.

## Standalone snapshots and authority

Central published masters and scoped approved operational observations are authoritative. Passenger sessions, feedback, staff credentials and unpublished import payloads remain private to their installation. No kiosk cache can publish changes back to central masters automatically.

Export: `python scripts/rtc_storage.py snapshot --directory data/snapshots --environment demo --valid-hours 24`. Production exports require `RTC_SITE_ID` and reject DEMO rows; keep demonstration and official source databases separate. Snapshot export works from SQLite and PostgreSQL into a portable SQLite payload. It excludes private tables and unverified operational-record rows, includes public data-source records and safe batch provenance, and records source, schema, UUID version, creation/expiry and file checksums.

Transfer the package and a **separately trusted** SHA256 of `manifest.json` using an authorized local file or authenticated LAN file-transfer process. A checksum supplied by the same untrusted party is not authenticity verification. There is no anonymous HTTP snapshot-import endpoint or automatic network fetch.

New kiosk: run `restore` with `--manifest-sha256 TRUSTED_HASH` and a new target. Existing kiosk: stop the server, back up, obtain the current logical fingerprint with `fingerprint --directory PACKAGE --target KIOSK_DB`, then explicitly run `apply-snapshot --directory PACKAGE --target KIOSK_DB --manifest-sha256 TRUSTED_HASH --expected-current FINGERPRINT`. The application lock must be available.

Reconciliation runs one SQLite transaction, preserves local private tables, records snapshot import provenance/idempotency in the existing audit table, refuses changed target fingerprints/schema, older snapshots or changed authority, divergent local operational projections and orphaned private references. An already imported snapshot reports previously-applied without replaying it. Conflicts require dispatcher/administrator review; there is no last-write-wins merge. An interrupted import rolls back. Do not bypass a conflict by overwriting the database: use an isolated restore for review and an explicit maintenance/cutover decision.

## Health, logs and sessions

`/health/live` checks process reachability. `/health/ready` returns 503 when the DB cannot be reached; optional-model degradation is distinct from DB unavailability. `/health/dependencies` requires existing admin authorization and exposes actual DB connectivity, bounded request/error/latency samples, session counts, disk warning, process RSS, maintenance status, publication evidence and invalidation revision. Administration → System Status displays this evidence.

Managed runtime runs bounded session-expiry cleanup; expired passenger history, pending clarification and selected journey are cleared by existing expiry logic. Browser kiosk idle reset and owner-bound idempotent/versioned conversation updates are preserved. Personal sessions follow their existing configured policy. A backend restart preserves committed DB sessions until expiry; browser connection loss does not authorize fallback to another data source.

Local structured request logs rotate by size (`RTC_LOG_MAX_BYTES`, `RTC_LOG_BACKUPS`). They omit query strings, bodies, capabilities and DB URLs. Rotation is per process to avoid Windows file-sharing collisions. Apply an OS-level age policy to old per-process log families; file-count rotation does not remove every historical PID family. Service stdout/stderr should also use the OS log-retention policy.

Clients reconnect to the existing WebSocket and re-fetch authoritative state. Versioned invalidations include timetable/fare/master writes and dispatcher events; duplicates/outdated versions are ignored. They are invalidations, not a durable per-terminal acknowledgement queue. Chat explicitly shows connection state and asks passengers to refresh older answers by asking again; historical chat answers are not silently rewritten.

## LAN security and outstanding certification

Use a local TLS reverse proxy and an organization-issued/local CA certificate trusted by terminals. Bind the backend to loopback behind that proxy, permit only trusted LAN subnets at the firewall and keep PostgreSQL inaccessible to passenger terminals. Configure exact trusted hosts. Authentication is same-origin bearer authentication, not cookies; no permissive CORS or remote login provider is added. Never trust client-supplied forwarding headers by default. Restrict admin access at the proxy/firewall as well as with backend roles/scopes.

This workspace cannot install privileged firewall rules, reboot/service tests or Linux units. OS-level public-egress isolation, unattended restart and real multi-device LAN/TLS tests remain acceptance gates. Application socket-denial and browser blocked-external-request tests do not replace those gates. See `PHASE_5E_REPORT.md` before production deployment.
