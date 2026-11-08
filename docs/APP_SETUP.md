# Run RTC Smart Enquiry locally

The passenger app is built and connected to the existing FastAPI backend. No cloud inference, microphone, payment or ticket-booking integration is included.

## Start on Windows

From the repository root:

```powershell
.\start-rtc.ps1
```

Development URLs: http://127.0.0.1:5173 for the app and http://127.0.0.1:8000/docs for the API. The script checks Python dependencies and local frontend packages, runs existing incremental migrations, starts both processes in hidden windows, reports readiness and waits until Ctrl+C. It performs no package downloads. Logs: data/runtime/*.log (Git-ignored). Default database: existing rtc.db, or DATABASE_URL when configured. The script does not seed or replace records by default.

For the already-built, single-process app:

```powershell
.\start-rtc.ps1 -Production
```

Open http://127.0.0.1:8000. Production mode uses only Python and frontend/dist; Node and node_modules are not required. SPA deep links work; unknown API paths still return JSON404, including on Windows. Stop an existing instance before starting another on the same port. Ctrl+C cleans up only the processes launched by this script.

Optional fictional demo setup on an empty local database:

```powershell
.\start-rtc.ps1 -InitializeDemo
```

This runs the existing idempotent seed/demo/NLP/taxonomy commands. It does not add the special browser-test services to your database. The original demonstration network does not connect every station pair. Choose a real supported boarding station; for example, the existing Tirumala → Nellore services are available in the standard seed. Unknown routes or missing operational data are displayed truthfully.

## Administrator access

Set RTC_ADMIN_TOKEN in the launcher environment to use your own local administrator credential. Otherwise the launcher generates a cryptographically random token for that run and prints it in the terminal. Enter that token at /admin. It is never bundled in JavaScript or stored in browser persistent storage; it remains in component memory until locking/reloading the admin interface. API authorization is enforced server-side for every admin read/write/import and diagnostic call. This is one local administrator role, not a multi-user account directory.

All conversation sessions created by the app have a random owner token, supplied to the existing ownership checks. Session ID, owner capability, messages and current stand are retained only in tab-scoped sessionStorage, so follow-ups survive reload. New conversation resets the server context and rotates the owner token. Do not treat a shared operating-system/browser account as separate authenticated people.

## One-time connected setup

Tested here with Python3.12.10, Node24.15.0 and npm11.12.1. Vite requires Node ^20.19.0 or >=22.12.0. Use the repository's Python environment if already configured.

```powershell
python -m pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
```

Browser test setup additionally requires `python -m pip install -r requirements-test.txt` and `cd frontend; npx playwright install chromium`. Downloads occur only during setup. English model packages/weights remain governed by the existing model documentation; the app does not download or promote a classifier.

## Offline deployment

On a connected staging machine, download Python wheels (`python -m pip download -r requirements.txt -d wheelhouse`) for the same OS/Python architecture and run the frontend install/build above. Copy backend, migrations, config, scripts, start-rtc.ps1, the chosen local DB and frontend/dist to the offline machine. Copy approved model files separately only if needed by that deployment. Install wheels with `python -m pip install --no-index --find-links wheelhouse -r requirements.txt`, then run `start-rtc.ps1 -Production`. Package installation and builds are separate from runtime.

For offline frontend development or rebuilding, provision the entire npm dependency/cache set during connected setup. Merely copying package-lock.json does not make `npm ci` usable without internet. Production needs no npm process, CDN, remote font, analytics or image server. All assets and API requests are local. The browser tests block every non-local request and the test backend blocks external socket connections; OS firewall isolation is not claimed.

## Connected pages and APIs

- /: actual POST conversation/message and conversation/reset; owned context maintained by backend. Bus/journey selection sends a numbered reply through the conversation API.
- /search and /journeys: existing POST journeys/search with hard constraints, known-fare ranking and direct/transfer controls. No client routing algorithm.
- /services/:id: thin /app/services/{id} adapter combines existing route-stop, fare, status and platform services with local reference metadata.
- /admin: existing allowlisted CRUD now stages changes for validation, independent approval and publication. Protected schema/reference metadata powers editable depots, calendars, fare rules, platforms and other managed resources. Import Center supports local CSV/XLSX, mapping, dry-run preview, audit and supported rollback.
- /admin/diagnostics: protected stateless NLP diagnostic adapter. Normal passenger APIs do not expose debug data; debug=true now requires an administrator token.
- /admin/status: actual NLP health and local DB inventory; deterministic fallback is explicitly distinguished from an approved statistical model. New staged batches carry timestamps; legacy import recency can remain unknown.

## Tests and troubleshooting

Run `npm run lint --prefix frontend`, `npm run build --prefix frontend`, `cd frontend; npm test`, `python -m pytest -q`, Ruff and Mypy as described in README. Browser tests serve the compiled app through FastAPI on ports 8020 and 8021 using separate temporary SQLite databases; they never mutate rtc.db. Both ports must be free. The network-off test intentionally permits loopback to the API and Windows asyncio socketpair plumbing. Real PostgreSQL reproduction requires the dedicated test URL described in PHASE_5A_SETUP.md.

If the connection indicator is unavailable, inspect backend-error.log. If admin is unavailable, check the launcher's token configuration. If no services match, verify the selected boarding station/date and local data, then explicitly relax filters. Lack of fare, seats or GPS never means zero fare, confirmed inventory or live tracking.

## Locally installed frontend libraries

- @radix-ui/react-dialog: ^1.3.1
- @radix-ui/react-slot: ^1.5.0
- @tailwindcss/vite: ^4.3.5
- @tanstack/react-query: ^5.107.1
- @tanstack/react-table: ^8.21.3
- clsx: ^2.1.1
- lucide-react: ^1.70.0
- react: ^19.3.1
- react-dom: ^19.3.1
- react-router-dom: ^7.18.5
- recharts: ^3.10.1
- tailwind-merge: ^3.7.0
- tailwindcss: ^4.3.5

Exact resolved versions are in frontend/package-lock.json. Local Radix-based components provide the permitted shadcn-compatible controls; no hosted component runtime is used.

## Phase 4B additions

Journey planner supports selecting two or three results for backend-validated comparison. Service details use accessible tabs. Kiosk touch mode enlarges controls and conversation expiry hides previous passenger data; clear/reset also calls the backend. Current operational cards mask verified data at the supplied expiry deadline. Historical cards do not poll.

Admin lists now search and sort across the database with server pagination. Data Quality is available at `/admin/data-quality`; System Status at `/admin/status`. Permission metadata keeps unsupported resources read-only. Data Quality explicitly identifies checks that cannot be performed with the current schema. See PHASE_4B_REPORT.md for actual tests and limitations.

## Phase 4C operation

Choose the kiosk idle timeout (2/5/10/15 minutes) above the station selector. Typing/enquiry activity renews it within server expiry. Drafts and interrupted enquiries remain in this browser tab for recovery, then clear on reset/expiry. Ambiguous station buttons use database station codes and continue the original question. Use the current result list for numeric selection; expired or changed departures require a new search.

Planner recovery buttons state exactly which restriction changes. Reset search clears the planner without submitting a new enquiry. Chat category recovery retains hard accessibility requirements. "What if I change at Kadapa?" sets a required local transfer station; no matching generated route means no result.

Admin forms warn before discarding edits. API error reference IDs can be matched in `data/runtime/requests.jsonl` (bounded local rotating JSONL; no raw conversation body). `RTC_REQUEST_LOG` overrides that path. `RTC_REQUESTS_PER_MINUTE` overrides the default 300 per-minute, per-process mutation limit; deploy a suitable kiosk limit rather than copying the test server's stress-test value.

Run `python scripts/verify_passenger_offline.py` from a Python environment containing the repository's scikit-learn/joblib dependencies (this machine: `.venv-english/Scripts/python.exe`). It verifies candidate technical loading with sockets blocked and never changes approval/active model selection. See PHASE_4C_REPORT.md and PHASE_4C_PERFORMANCE.md for current evidence and limits.


## Phase 5B operations

Open `/admin/operations` for dispatcher control and `/board` for the public local station board. Provision named staff and explicit station grants through Access & approvals. Sources, stations, bays and schedules still require Phase 5A publication. See PHASE_5B_SETUP.md for actions, review, source semantics, API/WebSocket operation and local PostgreSQL/offline test reproduction. PHASE_5B_REPORT.md records actual test results and deployment limits. No voice or external transport integration was added.
