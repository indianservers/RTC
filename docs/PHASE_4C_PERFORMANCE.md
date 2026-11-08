# Phase 4C local performance measurements

Recorded: 2026-11-08T09:35:55.500Z. Five runs on the isolated seeded DEMO SQLite database. Loopback HTTP; outbound browser/backend socket calls blocked. The application uses its local deterministic inference path.

These are observations on this machine, not throughput or production service-level guarantees. No baseline-controlled speedup is claimed.

- Page ready (local navigation + bootstrap): median **109.02 ms**, observed range 76.71–116.67 ms.
- Chat send to answer visible: median **163.31 ms**, observed range 118.72–200.55 ms.
- Autocomplete including 180 ms debounce: median **250.14 ms**, observed range 247.88–272.73 ms.
- NLP engine total: median **37.53 ms**, observed range 34.07–42.18 ms.
- Journey planner HTTP round trip: median **46.41 ms**, observed range 43.02–58.02 ms.
- Chromium JS heap used (MiB): median **14.34 MiB**, observed range 8.43–21.01 MiB.
- Intent inference phase: median **2.82 ms**, observed range 2.18–3.62 ms.
- Database enquiry/orchestration phase: median **25.30 ms**, observed range 23.87–29.14 ms.

The browser test measures send-to-visible-answer as the user-observed interaction, including transport and rendering. It does not isolate React commit CPU time. Database phase timing includes the existing enquiry engine work, rather than isolated database CPU. Browser heap is Chromium JS heap at each sample, not full process/OS memory. Navigation includes warm local assets and repeated application startup within a single browser context; it is not a cold-machine benchmark. Concurrent local work can influence timings. Five samples are too few for a meaningful percentile claim.

Optimizations retained or added: shared query keys, 180 ms autocomplete debounce, aborted obsolete requests, local asset bundles, lazy admin chunk, bounded histories, server pagination, expiry-aware operational polling, and no live polling of historical chat cards. Rich results still fetch required local reference metadata; operational data are masked at supplied expiry.

Final build: passenger JS 431.78 kB (136.31 kB gzip); lazy admin JS 443.02 kB (126.12 kB gzip); CSS 41.42 kB (9.99 kB gzip). Bundle sizes are build artifacts, not downloaded internet dependencies.

The existing local SVM candidate loaded in the model environment with **all socket connections blocked**; candidate loading and batch inference timings are stored separately in phase4c-offline-model.json. It remains unapproved and is not substituted for the measured application fallback.

Raw samples: phase4c-performance.json. Reproduce through the production-browser test named "local runtime performance benchmark records measured timings". The full test configuration provisions an isolated database with explicitly DEMO test vehicles and station ambiguity records; it does not alter rtc.db.
