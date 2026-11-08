# Phase 4C prioritized usability audit

The existing application was audited through actual local API/browser interactions, source review, seeded-database queries and the requested A/B/C conversations. Working screens/components, tables and migrations were retained.

## Critical and high priority

- HIGH, fixed: ordinary numeric bus selection trusted previously returned rows. It now rechecks the same service, operating date, departure, origin/destination and restrictions against the database, rejects departed/missing/ineligible results and clears stale selection references. Journey selections retain their existing revalidation.
- HIGH, fixed: an empty repeat search could retain an earlier candidate list. Search-result references now become empty when the new search returns no results.
- HIGH, fixed: ambiguous shared station names raised an unstructured clarification and lost the pending question. Real database choices are now returned, the pending question is stored in owned context, and a code reply resumes it automatically. Full unique station codes outrank embedded shorter ambiguous names.
- HIGH, fixed: "Does it stop at Ongole?" could replace the destination. Stop probes now populate the via slot and use the existing BUS_VIA_LOCATION enquiry while preserving destination and selected service.
- HIGH, fixed: "What if I change at Kadapa?" could overwrite the destination. The existing journey API now accepts an optional required transfer station, resolved against the database and applied before ranking/pagination. The dialogue preserves destination and date and explicitly allows transfers when requested.
- HIGH, fixed: category recovery could drop a hard accessibility restriction. Clearing bus-category preferences now retains accessibility and operator requirements.
- HIGH, fixed: interrupted requests survived only as unanswered text after reload. A tab-local pending marker now produces an explicit retry; drafts persist during navigation. Reset/expiry removes both draft and pending markers.

## Medium priority

- MEDIUM, fixed: suggestions barely varied by intent. They now use the current result, clarification state, filters and supported capability. Unknown/incomplete state does not generate arbitrary questions.
- MEDIUM, fixed: no-result recovery lacked a searched-context explanation and specific filter choices. Chat shows searched places/date/restrictions. Planner exposes explicit category/fare restriction removal, retained transfer recovery and reset search.
- MEDIUM, fixed: fixed 15-minute kiosk timeout. Two/five/ten/fifteen-minute settings now renew with typing/enquiry activity and respect server expiry. Footer reflects the configured policy.
- MEDIUM, fixed: unsaved admin form edits could be dismissed immediately. Close/cancel and link navigation now ask for confirmation; browser document unload uses its native unsaved-changes warning. Saving still uses existing validated backend CRUD.
- MEDIUM, fixed: stale result-card platform fallback could reuse an old row value. Platform now comes from the expiry-aware adapter. Seats stay unconfirmed without verified inventory evidence.
- MEDIUM, fixed: request errors lacked correlatable diagnostics. A bounded rotating local JSONL log records route templates, status, duration, category, severity and correlation IDs without bodies, query strings or credentials. UI API errors display the ID.
- MEDIUM, fixed: data quality lacked duplicate-name, route offset/distance monotonicity and service/operator category checks. These now query actual active records; possible duplicate names are warnings rather than automatic merges.

## Data/deployment constraints

- OPEN DATA LIMIT: the preserved schema cannot audit undated FareRule expiry or reconstruct unpersisted rejected import rows. The UI reports these as unavailable rather than zero issues.
- OPEN DEPLOYMENT LIMIT: no approved active statistical classifier exists. Candidate technical loading works offline in the provisioned model environment; the production app correctly uses local deterministic inference and reports degraded model readiness.
- OPEN DATA LIMIT: the existing rtc.db and isolated acceptance fixture have different demonstration coverage. A next-bus request can legitimately return no direct service in rtc.db. The implementation does not create fictional unlabelled schedules to hide this.

Evidence is linked from PHASE_4C_REPORT.md. No Phase 5, voice, Telugu training, payment or cloud feature was added.
