# Phase 4C passenger stabilization report

Implemented in the existing checkout on 8 November 2026. Production app: http://127.0.0.1:8000. Start again with `./start-rtc.ps1 -Production`. This is an English text, local FastAPI/database application. No migrations, tables, seeds or working API families were replaced. Changes are not committed/pushed by this request.

## Outcome

Passenger chat now resumes structured station clarification, preserves destination during stop/transfer questions, offers result-specific supported follow-ups, retains interrupted enquiries for explicit retry and explains no-result restrictions. Bus selection revalidates current database eligibility. A refreshed empty list cannot leave old numeric references available. Current stand changes are applied to shared state after backend confirmation.

Kiosk settings support 2, 5, 10 and 15 minutes of idle time; typing and enquiries renew the deadline within the server expiry bound. Reset and expiry remove messages, selected context capability, unsent draft and interrupted-request markers from the display/tab storage. A late response cannot restore prior passenger data. Retained server history is not purged by UI reset.

Planner reset removes its restrictions explicitly without searching. No-result actions remove only the named restriction; direct-to-connecting recovery retains the others. An optional `transfer_station` field extends the existing journey constraints/API without duplicating endpoints. It resolves a unique local station and requires an actual transfer there before ranking/pagination. Direct-only and explicit change-at requests update transfer constraints deliberately. Hard accessibility restrictions survive category recovery.

Administration adds unsaved-close/cancel/link confirmation and a document-unload warning. Existing validated CRUD, permissions and read-only domains remain. Data Quality adds possible duplicate station names within a city, decreasing stop offsets/distances, and inactive/wrong-operator category references. It makes no automatic merges or unrecorded statistics.

Local request diagnostics use `data/runtime/requests.jsonl`, rotating at 2 MB with three backups (roughly 8 MB maximum). Every API response has an `X-Request-ID` and `Server-Timing` app duration. Entries contain timestamp, route template, method, status, duration, severity and category. Bodies, query strings, raw passenger text, owner tokens and admin credentials are excluded. UI failures expose the reference ID for local troubleshooting. The default per-process mutation rate limit remains 300/minute; the isolated stress test server sets 5000/minute. The limit is configurable through `RTC_REQUESTS_PER_MINUTE`.

## Verification

Final backend regression: **1,484 passed, 0 failed**, one existing Starlette/httpx deprecation warning, 206.44 seconds. Evidence: `models/benchmarks/phase4c-verified-backend-pytest.txt`. The shared checkout contains independent model work, which is included in this actual collected count.

The full production Playwright suite finished with **132 passed, 0 failed, 0 skipped, 0 flaky**, in 106.11 seconds, including more than 100 passenger scenarios. The date/enquiry matrix is transparent: 20 enquiry/filter/follow-up cases across today, tomorrow, +3 and +7 days. Additional tests cover A/B/C continuity, current numbering, ambiguity, actual ten-step acceptance, expired/missing references, filters, fares, unknown data, imports/admin authorization, failure/retry, interrupted reload, four viewport classes, idle renewal and offline requests. No successful timetable/fare replies are mocked. Failure/race tests intentionally delay or fail transport; they use actual responses when testing recovery. One scenario records performance. Final machine results are in `docs/phase4c-playwright.json`. After the final compact timeout-control/footer and narrow-screen follow-up/reset-display changes, the 9 mobile/kiosk/viewport/ten-step checks were rerun against the rebuilt production assets: 9 passed, 0 failed (13.4 seconds); the full-suite JSON was preserved. A final dedicated mobile-kiosk assertion also passed, requiring at least 200 px of conversation viewport after a real result (1 passed, 0 failed).

Commands executed: `python -m pytest -q --tb=short`, `ruff check backend scripts training`, `python -m mypy backend/app --ignore-missing-imports` (48 source files), `npm --prefix frontend run lint`, `npm --prefix frontend run build`, and `npm --prefix frontend test`. Ruff, configured Mypy, frontend lint, TypeScript and production build passed. Git whitespace checks passed. The npm audit from Phase 4B remains the latest dependency audit; this phase adds no packages and does not claim a new audit run.

The actual app was restarted with existing migrations and verified manually through its local browser: home, truthful no-direct-result recovery, real Vijayawada-to-Guntur service results and mobile layout. Screenshots are `docs/phase4c-desktop.png`, `docs/phase4c-results.png`, `docs/phase4c-mobile.png`. Browser errors were checked. The acceptance JSON stores the ten-step isolated DEMO contexts/results; its records are temporary and never inserted into rtc.db.

## Offline/model verification

Browser E2E rejects every non-local browser request. Its separate actual backend blocks external socket connections, uses a temporary seeded SQLite database and serves compiled local assets. This exercises the application with outbound connections blocked at its test boundary; it does not certify the Windows firewall or arbitrary host software.

`scripts/verify_passenger_offline.py` additionally blocked all socket connections before loading the registry-checksummed local SVM candidate and running five inference samples in `.venv-english`. Loading and inference passed; evidence is `docs/phase4c-offline-model.json`. The system Python lacks joblib; the provisioned model environment supplies it. This is a technical candidate smoke test, not accuracy evaluation or approval. Registry/configuration, model weights and deployment gates are unchanged. Application health correctly reports database/fallback ready, statistical model NOT_APPROVED and overall DEGRADED. An approved statistical classifier remains an earlier-phase deployment dependency; the tested application uses the existing local deterministic fallback.

## Performance

Five measured runs record page-ready time, send-to-visible-answer time, debounced autocomplete, actual NLP total/phase timings, database lookup phase, journey HTTP latency and Chromium JS heap usage in `docs/phase4c-performance.json`. NLP database lookup is the engine phase duration, not isolated SQL CPU time. Page-ready includes local navigation/bootstrap and chat timing includes HTTP plus visible rendering; they are not synthetic React-only render timings. JS heap is a browser metric rather than full process RAM. See PHASE_4C_PERFORMANCE.md for numerical results and measurement limits. No before/after speedup is claimed without a controlled baseline.

## Limits and acceptance boundary

- All dates/transport facts come from local data. DEMO is visible. The deployed rtc.db has different route coverage from the isolated browser fixture; a direct next bus to Nellore from Vijayawada may correctly have no result. New fixture AC/vehicle/ambiguous-station records are explicitly fictional and temporary.
- Unknown inventory, GPS, platform and amenities remain unconfirmed. Operational expiry is enforced; UI corrections do not create live tracking or booking integration.
- The existing FareRule schema has no expiry fields and rejected import rows lack persistent history. These audits remain explicitly unavailable. Dated segment-fare expiry and stored import issues are audited.
- Admin reference lists retain the prior 100-choice limit and unsupported resources remain read-only. There is one local-admin role, not enterprise identity/RBAC. Unsaved-edit guards cover form dismissal, links and document unload; same-document browser history traversal is not a comprehensive router-level blocking system.
- The earlier route-offset timing model, Asia/Kolkata presentation, per-process rate limiting and bounded search caveats remain. Transfer-station requirements filter actual generated paths; a truncated graph search still reports partial results.
- SQLite and real local HTTP were tested. No new PostgreSQL execution, OS-wide network isolation, exhaustive screen-reader certification or real-operator-data validation is claimed.
- Candidate model loading is verified offline, but no statistical classifier is approved for production. This phase does not override that gate or claim it has completed prior model-training acceptance requirements.

Phase 4C passenger UX/stabilization functionality is implemented and verified for the current local deterministic deployment, subject to these explicit data/model/deployment limits. Phase 5 has not been started. Original request, prioritized audit and requirement coverage are preserved in `phase4c-request.md`, `PHASE_4C_AUDIT.md` and `phase4c-coverage.json`.
