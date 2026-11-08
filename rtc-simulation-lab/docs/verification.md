# Verification results

Executed in the isolated lab virtual environment on 2026-11-08, Python 3.12.10.

- Generated: 60 cities, 120 stations, 600 routes, 2,400 scheduled trip occurrences, 600 route fare records.
- Authored gold suite: 540 scenarios (54 patterns with ten parameter sets), all ten requested A-J categories.
- English evaluation corpus: 540 distinct questions with scenario links; evaluation-only.
- Artifact validation: PASS, zero errors, including SHA-256 checksums, references, route/stop chronology, provenance and corpus linkage.
- Reference benchmark: 540/540 pass (100%); measured comparison time 0.0043923 seconds, excluding JSON loading. This is a local reference self-check, not production throughput.
- Replay: eight event kinds applied, frozen time 2026-11-08T08:07:00+05:30, live_positions=false.
- pytest: 552 passed in 3.97 seconds. Includes 540 parametrized gold cases and six Hypothesis properties (default maximum 100 examples per property), reproducibility, seed/config variation, CSV roundtrip, checksum tampering, adapter failure capture, all event mutations, overnight delays and Decimal rounding.

Generated coverage: reports/coverage.json and reports/coverage.md. Detailed gold comparisons: reports/benchmark.functional.json. Frozen replay snapshot and event log: reports/replay.json.

No production database, backend, migration, NLP classifier, training dataset, registry, requirements or configuration was modified by this workstream. All created project files are inside rtc-simulation-lab. No Git merge or publication was performed. Package downloads were confined to this lab's virtual environment.

Remaining limits: production adapter and NLP model have not been evaluated; network geography is synthetic rather than calibrated; scenario bus-category tags are coverage labels, not category-policy assertions; optional offline test wheelhouse is not bundled. See adapter.md for later integration.
