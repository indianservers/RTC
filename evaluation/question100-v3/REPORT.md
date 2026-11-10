# question100-v3: 100 new questions and expectation-based training

Actual running bot: **22/100** automated intent/context checks. Previous candidate shadow: **48/100**. Newly trained candidate shadow: **53/100**. Training-specific change: **+5 checks**.

All 100 questions were checked for exact novelty against prior batches and training before asking. There were 181 additional, separately counted setup requests to establish selected-service context. Every expected label/action was frozen before execution. These are agent-authored synthetic expectations, not human-reviewed independent data.

## What was trained

Added 60 single-intent and 10 OOS examples to the previous corpus: **2419 total training examples**. Kept 20 contextual and 10 multi-intent questions as structured regression targets outside the 60-way loss. Neither model learns a new dialogue state transition just because a structured target is stored. SVM and TextCNN were both retrained as versioned candidates; old weights and previous reports are preserved.

The 100-question batch is training material. Results on it are memorization/integration diagnostics, not independent accuracy. The live bot remains on deterministic rules; shadow results are from isolated DB copies with outbound socket/DNS access denied. No candidate was deployed.

## Separate synthetic holdout

- SVM raw in-scope accuracy on the unchanged 180-question synthetic holdout: **92.22% → 93.89%**; macro-F1 **0.9198 → 0.9361**.
- CNN raw in-scope accuracy on the unchanged 180-question synthetic holdout: **81.11% → 83.89%**; macro-F1 **0.8052 → 0.8368**.

CNN validation rejection calibration: **failed; reject-all policy**. No independent human-reviewed validation/test set exists. The holdout is a previously exposed synthetic regression set; it was not used for this batch's fitting or threshold selection. All raw/selective decisions and confusion matrices are saved in model-comparison.json.

## Interpretation and unresolved work

**47 checks remain unresolved.** Per-kind counts are stored in verification.json. These are automated assertions, not human semantic answer-quality ratings. Some checks only test retained state or intent labels; they do not prove completeness or appropriate wording. Selected context can make ordinary lexical rules dominate a statistical classifier. Contextual corrections and multi-intent handling still need separate dialogue/composition work; single-label fitting alone cannot fix them.

Recommendation: keep production unchanged pending independent review, validated uncertainty, conversation regression and explicit approval. Inspect holdout and control results rather than attributing the whole rules-to-candidate difference to this training batch. Model weights stay excluded from Git.

## Execution

`python scripts/question100.py baseline --version question100-v3 --previous-version question100-v2 --base-dataset training/datasets/question100-v2` freezes expectations and asks the live bot. `prepare` with the same arguments freezes the cumulative dataset. Use the existing train_english_recovery.py with `--dataset training/datasets/question100-v3 --output-version question100-v3` for svm and cnn. The evaluation and shadow scripts take the same version arguments; `shadow --previous` evaluates the fixed predecessor. No startup downloads or production activation is involved.

## Verification

**346 cross-batch data/artifact/model tests passed**, covering all three batches, report consistency, complete confusion matrices, training/holdout separation, privacy and inactive-candidate flags. These passing validation tests are not 346 successful bot answers: this batch's new candidate passes only 53/100 response assertions. Ruff and Mypy on three tools also passed. The 70 new classifier examples have no detected character-ngram near overlap at cutoff 0.85 with the 480 validation/holdout rows. Bus category names for these new questions were fetched from the current local database, not a hardcoded list. See `verification.json` and `leakage-audit.json` for actual results.

## All questions, expected behavior and actual replies

### question100-v3-Q001 — Sir, which Nellore bus is the earliest one I can still catch tomorrow?

Expected: Find the earliest eligible departures after the passenger's requested threshold, including later operating dates.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

### question100-v3-Q002 — For tomorrow's full day, tell me when the very first Nellore run starts.

Expected: Find the earliest departure within one explicitly selected operating day, independent of the current time.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.

### question100-v3-Q003 — I must not miss tomorrow's final Nellore run; what is its leaving time?

Expected: Find the final eligible departure inside the chosen calendar or operator-defined operating-day bounds.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q004 — Please bring up tomorrow's bus timetable from Vijayawada across to Nellore.

Expected: List scheduled services permitting boarding at the origin and later alighting at the destination.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

### question100-v3-Q005 — Nellore travel tomorrow after ten at night only; what departures are listed?

Expected: Find eligible departures following an explicitly supplied lower time bound.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

### question100-v3-Q006 — Have you got Nellore departures tomorrow before half past six in the morning?

Expected: Find eligible departures preceding an explicitly supplied upper time bound.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Recorded services match outside the requested time window. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v3-Q007 — Look for a Nellore run tomorrow around 8:45 in the evening, give or take a little.

Expected: Find departures within a documented tolerance window around a specified clock time.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded services match outside the requested time window. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q008 — What reaching time does the published timetable give for this particular coach?

Expected: Retrieve the scheduled arrival time for the selected service and stop, labelling any operational override separately.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.

### question100-v3-Q009 — Roughly how long is the ride itself on the bus I've already chosen?

Expected: Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Your selected journey takes 120 minutes, including any transfer wait.

Trained candidate in isolated shadow:

> Your selected journey takes 120 minutes, including any transfer wait.

### question100-v3-Q010 — Please verify whether Nellore services run on the current calendar day.

Expected: Check which services operate on the station-local current date using calendars and exceptions.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v3-Q011 — How regularly do buses on the Nellore route leave throughout the timetable?

Expected: Describe scheduled departure counts or intervals on a segment within a specified period, without assuming regular headways.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v3-Q012 — Are festival-only Nellore departures or holiday timetable exceptions recorded here?

Expected: Retrieve date-specific extra or changed schedules for a specified holiday, festival or special operating date.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00. Recorded timetable for the requested date, including local calendar exceptions; no official festival schedule is inferred.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00. Recorded timetable for the requested date, including local calendar exceptions; no official festival schedule is inferred.

### question100-v3-Q013 — On this corridor, what different bus classifications appear among the departures?

Expected: List the service classifications represented by eligible departures on the requested segment.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v3-Q014 — Find Nellore services with an air-conditioned passenger compartment, please.

Expected: Find services whose assigned vehicle or configuration explicitly supports air conditioning.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

### question100-v3-Q015 — I specifically need a non-air-conditioned Nellore service; omit all the AC ones.

Expected: Find services explicitly known to be non-air-conditioned, excluding unknown configurations.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

### question100-v3-Q016 — Any Nellore coach that has sleeping accommodation in berths for this journey?

Expected: Find services with verified sleeping berths, independently of branded category and seat inventory.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> No eligible scheduled departures matched. Calendar coverage, publication or availability cannot be established from this diagnosis. Your restrictions are unchanged.

### question100-v3-Q017 — I want a sitting seat rather than a bed for Nellore; which services offer that layout?

Expected: Find services with verified seater accommodation rather than inferring layout from category branding.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

### question100-v3-Q018 — Can a Nellore passenger choose a bus whose propulsion is electric?

Expected: Find services with an explicitly assigned electric vehicle or configuration.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v3-Q019 — For this selected coach, list the convenience features passengers get while on board.

Expected: Report verified amenities of the selected assigned vehicle, retaining unknown feature states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Leg 1: AC is available; sleeper is not available.

### question100-v3-Q020 — Describe the differences in comfort and facilities between Demo electric and Demo sleeper.

Expected: Explain recorded differences between two or more service categories without guaranteeing vehicle amenities.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### question100-v3-Q021 — Find a service to Nellore with recorded access provisions for a wheelchair passenger.

Expected: Find departures meeting explicitly recorded accessibility requirements.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No supporting local records are available for this enquiry. Only explicitly wheelchair-accessible assigned vehicle types match.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Only explicitly wheelchair-accessible assigned vehicle types match.

### question100-v3-Q022 — What number of seats or berths does this assigned vehicle contain altogether?

Expected: Report physical seat and berth capacity of the assigned configuration, not vacant inventory.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Seat availability information is not available.

Trained candidate in isolated shadow:

> Seat availability information is not available.

### question100-v3-Q023 — Is changing buses avoidable when travelling from Vijayawada all the way to Nellore?

Expected: Find a single service allowing the requested journey without a vehicle change.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v3-Q024 — Which places are listed as halts, in sequence, for the service I've picked?

Expected: Retrieve the ordered scheduled stopping pattern of the selected route variant or service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v3-Q025 — Is Ongole on the path taken by this Nellore service, whether or not we stop there?

Expected: Check or search for a route passing through a requested via point without asserting a passenger halt.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 8:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 8:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 8:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 9:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 9:56 PM.

Trained candidate in isolated shadow:

> Which intermediate station should the bus pass through?

### question100-v3-Q026 — For this coach, please check that Ongole is a scheduled halt and not just a place passed through.

Expected: Confirm whether a selected service actually calls at a specific intermediate station and allows the relevant passenger action.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM.

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### question100-v3-Q027 — Where does this chosen service allow a traveller to board along its route?

Expected: Identify locations at which passengers may board the selected service or destination-bound journey.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v3-Q028 — Please identify the permitted places for a passenger to get down from this coach.

Expected: Identify permitted drop-off locations or validate a requested alighting station on a selected service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v3-Q029 — Find me a workable sequence of buses to Tirumala, including where to change.

Expected: Find feasible time-ordered multi-leg journeys respecting transfer windows and stop permissions.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q030 — I'd like another way of getting to Nellore by bus, avoiding the itinerary already selected.

Expected: Find different feasible paths or transfer patterns for the same journey, relative to an optional selected route.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Connect using a9f5e740-2f94-4a8c-bf41-efc65980b35c; arrival 09 Nov 2026 at 9:11 PM.
> 2. Connect using b8e8dad4-8915-455e-8c09-5e041ffae48f; arrival 09 Nov 2026 at 9:21 PM.
> 3. Connect using a9f5e740-2f94-4a8c-bf41-efc65980b35c then 0535d1b3-3d15-42a7-b705-379a18cb8466; arrival 09 Nov 2026 at 9:31 PM.
> 4. Connect using 0535d1b3-3d15-42a7-b705-379a18cb8466; arrival 09 Nov 2026 at 9:31 PM.
> 5. Connect using a9f5e740-2f94-4a8c-bf41-efc65980b35c then 79488092-c1b9-4706-88ae-81ff3fa0c5d7; arrival 09 Nov 2026 at 10:46 PM.

### question100-v3-Q031 — Tell me the kilometres covered from my chosen entry stop to my chosen exit stop.

Expected: Retrieve sourced cumulative or segment distance along the applicable route variant.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The recorded route segment distance is 120.00 km.

### question100-v3-Q032 — Starting from this stand, can a bus journey of any kind reach Tirumala?

Expected: Determine whether any feasible direct or connecting bus itinerary reaches the requested destination in the search period.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo seater service DEMO3: scheduled departure 09 Nov 2026 at 1:51 AM. Fare INR 100.00.
> 2. Demo seater service DEMO45: scheduled departure 09 Nov 2026 at 3:45 AM. Fare INR 100.00.
> 3. Demo seater service DEMO87: scheduled departure 09 Nov 2026 at 5:39 AM. Fare INR 100.00.
> 4. Demo seater service DEMO24: scheduled departure 09 Nov 2026 at 2:48 PM. Fare INR 100.00.
> 5. Demo seater service DEMO66: scheduled departure 09 Nov 2026 at 4:42 PM. Fare INR 100.00.

Trained candidate in isolated shadow:

> 1. Connect using DEMO3; arrival 09 Nov 2026 at 4:51 AM.
> 2. Connect using DEMO45; arrival 09 Nov 2026 at 6:45 AM.
> 3. Connect using DEMO87; arrival 09 Nov 2026 at 8:39 AM.
> 4. Connect using DEMO24; arrival 09 Nov 2026 at 5:48 PM.
> 5. Connect using DEMO66; arrival 09 Nov 2026 at 7:42 PM. Scheduled or estimated journeys do not confirm GPS, seats or guaranteed connections. Transfers require the same physical station; inter-stand travel is unsupported. Concessions and through-ticket discounts are not evaluated. Active verified service disruption records are conservatively excluded when avoid_verified_disruptions is enabled. Results are bounded to the next 24 hours and configured transfer/resource limits. No result does not prove the destination is unreachable.

### question100-v3-Q033 — Please state the ticket price applicable to my current selection and travel segment.

Expected: Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v3-Q034 — Choose the most affordable Nellore departure by comparing the ticket costs you actually know.

Expected: Rank eligible services by known applicable segment fare; missing prices are never zero.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v3-Q035 — Of the Nellore departures available, select the one needing the fewest travel minutes.

Expected: Rank eligible services by elapsed journey duration for the same requested segment.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

### question100-v3-Q036 — Lay out the differences in ticket prices between these buses for the exact same endpoints.

Expected: Compare applicable prices for multiple services or categories on the same boarding segment and travel date.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v3-Q037 — Does a still-fresh availability snapshot show room for two on the bus I selected?

Expected: Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Seat availability information is not available.

### question100-v3-Q038 — Can the selected bus be reserved ahead of time, or is reservation not offered on it?

Expected: Report whether reservations are supported for the selected service, separately from current seat availability.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v3-Q039 — Through which official booking methods can a traveller buy this operator's tickets?

Expected: Describe locally recorded approved ticket booking channels and instructions without executing a purchase.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v3-Q040 — Can you inspect an existing authorized booking record and tell whether the reservation is confirmed?

Expected: Read status of an existing booking only when an authorized local record is available; otherwise report unsupported or unavailable.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v3-Q041 — If a passenger decides not to travel, what ticket cancellation terms and charges apply?

Expected: Explain locally stored passenger ticket cancellation terms, independently of operational trip cancellation.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v3-Q042 — According to local policy, under what circumstances is a paid ticket fare refundable?

Expected: Explain applicable recorded refund rules or a supported calculation; never infer a refund without required policy data.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v3-Q043 — Tell me the recorded age and proof requirements for a senior-citizen fare concession.

Expected: Explain date-effective concession schemes and explicit eligibility requirements without assuming passenger qualification.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Which RTC operator do you mean?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### question100-v3-Q044 — Is there a luggage weight allowance, and when would excess baggage attract a charge?

Expected: Describe recorded baggage allowances, restrictions and applicable published luggage charges.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> This database enquiry does not support luggage rules.

Trained candidate in isolated shadow:

> This database enquiry does not support luggage rules.

### question100-v3-Q045 — I mean the coach's verified whereabouts right now, not the list of towns on its route.

Expected: Report the freshest authoritative operational state or location, distinguishing scheduled-only, stale and unknown data.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v3-Q046 — Can you check the most recent confirmed delay record for the departure I selected?

Expected: Report a verified delay duration or recorded reason for the selected dated trip and affected stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Delay information is not confirmed.

Trained candidate in isolated shadow:

> Delay information is not confirmed.

### question100-v3-Q047 — Has this exact dated service been officially marked as not operating because it was cancelled?

Expected: Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v3-Q048 — Please tell me the confirmed departure-platform assignment for the bus I've selected here.

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> The platform has not been confirmed.

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### question100-v3-Q049 — Do you have an updated observed arrival estimate for this trip instead of its scheduled arrival?

Expected: Report a fresh verified operational arrival estimate; a scheduled arrival alone does not satisfy this intent.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

Trained candidate in isolated shadow:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v3-Q050 — Has a real departure event been entered for my coach at this station yet?

Expected: Confirm departure only from an authoritative actual-departure event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v3-Q051 — Has staff confirmed the actual arrival of this specific bus at our stand?

Expected: Confirm arrival only from an authoritative actual-arrival event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.

Trained candidate in isolated shadow:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.

### question100-v3-Q052 — What current service-impact notices mention blocked roads or diversions on this corridor?

Expected: Report verified diversions, suspensions or other incidents effective for the requested service or period.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v3-Q053 — Did the departure-platform allocation for this coach get revised after its first assignment?

Expected: Confirm a platform reassignment by examining assignment history for the same trip and station.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> The platform has not been confirmed.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> The platform has not been confirmed.

### question100-v3-Q054 — Please identify service 3521 by looking up its route and endpoints in the timetable.

Expected: Resolve a service identifier within operator and validity scope, requesting clarification if multiple records match.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v3-Q055 — What amenities, such as public toilets and a waiting hall, does the local stand record show?

Expected: Report locally recorded passenger facilities and their verification or availability state at a station.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Leg 1: AC is available; sleeper is not available.
> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> Leg 1: AC is available; sleeper is not available.
> No matching information is available for that enquiry.

### question100-v3-Q056 — Where is the counter where passengers can speak to the enquiry staff at this station?

Expected: Provide a recorded station enquiry/helpdesk contact, location or opening information.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v3-Q057 — An item of mine is still on a coach; how should I contact the local found-property service?

Expected: Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v3-Q058 — Please provide whatever authorized depot contact details exist for my bus's operating organization.

Expected: Provide published local operator or depot contact information relevant to the passenger's service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### question100-v3-Q059 — From where a passenger enters this stand, how should they walk towards platform six?

Expected: Provide recorded within-station directions or zone information without inventing an indoor route.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The platform has not been confirmed.

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### question100-v3-Q060 — What is the documented route for making a passenger grievance against the bus operator's staff?

Expected: Explain the locally recorded complaint or grievance channel and reporting instructions.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v3-Q061 — How many rupees for the option we've just selected?

Expected: Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v3-Q062 — For that very departure, where is the boarding bay?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No supporting local records are available for this enquiry. Recorded addresses and bay zones only; no indoor route is inferred.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Recorded addresses and bay zones only; no indoor route is inferred.

### question100-v3-Q063 — Continue using the exact same selected bus, please.

Expected: preserve selection. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v3-Q064 — I'd like to go with departure number two from this result list.

Expected: select second. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v3-Q065 — Sorry, change the destination for this trip to Tirumala.

Expected: dest tirumala. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: FAIL; trained candidate: PASS.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No feasible connection matched the recorded stop times and your current restrictions. A single cause has not been established. Your restrictions are unchanged.

### question100-v3-Q066 — My destination is Tirupati now, not Nellore.

Expected: dest tirupati. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q067 — Shift the travel day forward to the day after tomorrow.

Expected: date plus two. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 10 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 10 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 10 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 10 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 10 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q068 — In these results, keep air-conditioned services and nothing else.

Expected: filter ac. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

### question100-v3-Q069 — I would rather travel without air conditioning; update that preference.

Expected: filter non ac. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No eligible scheduled departures matched. Calendar coverage, publication or availability cannot be established from this diagnosis. Your restrictions are unchanged.

### question100-v3-Q070 — Please search again with sleeper accommodation as my preference.

Expected: filter sleeper. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### question100-v3-Q071 — Cap the ticket cost for my search at 250 rupees.

Expected: budget 250. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v3-Q072 — There will be two travellers going on this booking enquiry.

Expected: passengers two. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v3-Q073 — Please undo the fare ceiling I had set before.

Expected: remove budget. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.

Trained candidate in isolated shadow:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.

### question100-v3-Q074 — Search beyond the selected leaving time for a later bus.

Expected: later departures. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v3-Q075 — No, the selected departure isn't the one I was trying to choose.

Expected: reject selection. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v3-Q076 — Drop the previous trip details and give me a fresh conversation.

Expected: reset. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q077 — Read your immediately preceding answer again for me.

Expected: repeat. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q078 — And what's the travelling duration for the same bus we picked?

Expected: Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Your selected journey takes 120 minutes, including any transfer wait.

Trained candidate in isolated shadow:

> Your selected journey takes 120 minutes, including any transfer wait.

### question100-v3-Q079 — I'd now like to get into the coach at Ongole.

Expected: origin ongole. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q080 — I will end my ride at Ongole instead; change the destination accordingly.

Expected: dest ongole. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q081 — Identify the next Nellore departure and quote the fare for that particular bus.

Expected: Find the earliest eligible departures after the passenger's requested threshold, including later operating dates.; Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.
> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.
> 2. Service DEMO-CONV-3f8df292-2: fare INR 205.00.
> 3. Service DEMO-CONV-3f8df292-3: Fare information is not available.
> 4. Service DEMO-CONV-698c52cb-1: fare INR 101.00.
> 5. Service DEMO-CONV-698c52cb-2: fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.
> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.
> 2. Service DEMO-CONV-3f8df292-2: fare INR 205.00.
> 3. Service DEMO-CONV-3f8df292-3: Fare information is not available.
> 4. Service DEMO-CONV-698c52cb-1: fare INR 101.00.
> 5. Service DEMO-CONV-698c52cb-2: fare INR 205.00.

### question100-v3-Q082 — Give me the selected bus's intermediate halts plus its onboard amenity details.

Expected: Retrieve the ordered scheduled stopping pattern of the selected route variant or service.; Report verified amenities of the selected assigned vehicle, retaining unknown feature states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Leg 1: AC is available; sleeper is not available.

### question100-v3-Q083 — For the bus I selected, check both its confirmed bay and any recorded delay.

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.; Report a verified delay duration or recorded reason for the selected dated trip and affected stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Delay information is not confirmed.

Trained candidate in isolated shadow:

> Delay information is not confirmed.

### question100-v3-Q084 — Tell me the first Nellore bus timing together with how long that first journey takes.

Expected: Find the earliest departure within one explicitly selected operating day, independent of the current time.; Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 1. Service DEMO-CONV-3f8df292-1: journey time 120 minutes.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 1. Service DEMO-CONV-3f8df292-1: journey time 120 minutes.

### question100-v3-Q085 — Compare what these buses cost and how much time each spends travelling.

Expected: Compare applicable prices for multiple services or categories on the same boarding segment and travel date.; Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v3-Q086 — Which is the day's final Nellore departure and what bus category is that run?

Expected: Find the final eligible departure inside the chosen calendar or operator-defined operating-day bounds.; List the service classifications represented by eligible departures on the requested segment.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

### question100-v3-Q087 — Has my coach been cancelled, and is there evidence it actually departed?

Expected: Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request.; Confirm departure only from an authoritative actual-departure event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Current operational status is not confirmed.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v3-Q088 — Check for a through bus with no transfer and tell me its route distance in km.

Expected: Find a single service allowing the requested journey without a vehicle change.; Retrieve sourced cumulative or segment distance along the applicable route variant.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.
> The recorded route segment distance is 120.00 km.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.
> The recorded route segment distance is 120.00 km.

### question100-v3-Q089 — Are a couple of seats recorded available, and is this a reservable service?

Expected: Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states.; Report whether reservations are supported for the selected service, separately from current seat availability.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Seat availability information is not available.

Trained candidate in isolated shadow:

> Seat availability information is not available.

### question100-v3-Q090 — Tell me whom to contact at the operating depot and how to report my missing suitcase.

Expected: Provide published local operator or depot contact information relevant to the passenger's service.; Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v3-Q091 — Which team finished top of the professional basketball league this year?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q092 — What tax deduction can I claim for interest on my education loan?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q093 — How do I make a mango pickle that stays fresh for months?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q094 — Predict whether Nellore will have high winds during the next few days.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

### question100-v3-Q095 — Compose a wedding invitation message in rhyming English.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q096 — What medicine should I take for a recurring migraine?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q097 — Which digital camera would you recommend for wildlife photography?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q098 — Explain the ending of a popular science-fiction movie.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v3-Q099 — What rate is the market charging for platinum today?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Where would you like to travel?

Trained candidate in isolated shadow:

> Where would you like to travel?

### question100-v3-Q100 — Teach me how to calculate the area under a curve with integration.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

