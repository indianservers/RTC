# Phase 4B UI gap audit

Audit scope: existing passenger chat, search, planner, service details, admin tables, imports, diagnostics and status screens. Existing components and business APIs were retained.

- Chat lacked explicit selected-service context, reset confirmation, expiry-safe rendering and protection against late responses. Added context strips, real follow-up chips, cancellable requests, generation guards, private-display expiry and backend reset integration.
- Previous service results could repeat long histories and poll old cards. Older results now collapse; current cards use expiry-aware operational refresh. Stops and details have distinct working destinations.
- Planner lacked validated multi-option comparison and shortest-duration sorting. Added existing backend comparison integration, two/three-choice limits, dirty-filter invalidation and explicit direct-route recovery.
- Service information needed readable domain grouping. Added keyboard-accessible tabs and a shared ordered timeline; unknown amenities, inventory and operational information remain explicit.
- Admin search/sort previously covered only the fetched page. Existing listing endpoints now support database-wide search, validated sorting, active filters and total counts. Drawers and accessible confirmation dialogs replace native confirmation prompts.
- Data Quality had no dedicated database audit. Added actual SQL findings with severity, record links, corrections, paging and explicit unsupported checks.
- Diagnostics lacked actionable context/executor presentation. Added actual model, intent, entity, context, template, latency and executor output; fixed fare-comparison context routing.
- System Status needed real inventory/model/source distinctions. Added protected local inventory, health, source and stale-data presentation without simulated metrics.
- Autocomplete and other requests could become obsolete. Added debounce, cancellation, stable query keys and conservative freshness deadlines.
- Kiosk/mobile needed stronger resets and touch targets. Added touch mode, automatic session expiry, immediate private-display clearing, keyboard dialogs and responsive regression coverage.
- CSV invalid timezone could raise an unhandled server error. It now becomes a normal row validation error with rollback.

Evidence: 35 production-browser scenarios, backend regression log, live desktop comparison/service/Data Quality screenshots and mobile kiosk screenshot. Accessibility was checked through keyboard and semantic interaction tests; no exhaustive accessibility certification is claimed.
