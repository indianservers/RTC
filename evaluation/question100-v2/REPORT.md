# question100-v2: 100 new questions and expectation-based training

Actual running bot: **15/100** automated intent/context checks. Previous candidate shadow: **50/100**. Newly trained candidate shadow: **52/100**. Training-specific change: **+2 checks**.

All 100 questions were checked for exact novelty against prior batches and training before asking. There were 181 additional, separately counted setup requests to establish selected-service context. Every expected label/action was frozen before execution. These are agent-authored synthetic expectations, not human-reviewed independent data.

## What was trained

Added 60 single-intent and 10 OOS examples to the previous corpus: **2349 total training examples**. Kept 20 contextual and 10 multi-intent questions as structured regression targets outside the 60-way loss. Neither model learns a new dialogue state transition just because a structured target is stored. SVM and TextCNN were both retrained as versioned candidates; old weights and previous reports are preserved.

The 100-question batch is training material. Results on it are memorization/integration diagnostics, not independent accuracy. The live bot remains on deterministic rules; shadow results are from isolated DB copies with outbound socket/DNS access denied. No candidate was deployed.

## Separate synthetic holdout

- SVM raw in-scope accuracy on the unchanged 180-question synthetic holdout: **92.22% → 92.22%**; macro-F1 **0.9211 → 0.9198**.
- CNN raw in-scope accuracy on the unchanged 180-question synthetic holdout: **84.44% → 81.11%**; macro-F1 **0.8386 → 0.8052**.

CNN validation rejection calibration: **failed; reject-all policy**. No independent human-reviewed validation/test set exists. The holdout is a previously exposed synthetic regression set; it was not used for this batch's fitting or threshold selection. All raw/selective decisions and confusion matrices are saved in model-comparison.json.

## Interpretation and unresolved work

**48 checks remain unresolved.** Per-kind counts are stored in verification.json. These are automated assertions, not human semantic answer-quality ratings. Some checks only test retained state or intent labels; they do not prove completeness or appropriate wording. Selected context can make ordinary lexical rules dominate a statistical classifier. Contextual corrections and multi-intent handling still need separate dialogue/composition work; single-label fitting alone cannot fix them.

Recommendation: keep production unchanged pending independent review, validated uncertainty, conversation regression and explicit approval. Inspect holdout and control results rather than attributing the whole rules-to-candidate difference to this training batch. Model weights stay excluded from Git.

## Execution

`python scripts/question100.py baseline --version question100-v2 --previous-version question100-v1 --base-dataset training/datasets/question100-v1` freezes expectations and asks the live bot. `prepare` with the same arguments freezes the cumulative dataset. Use the existing train_english_recovery.py with `--dataset training/datasets/question100-v2 --output-version question100-v2` for svm and cnn. The evaluation and shadow scripts take the same version arguments; `shadow --previous` evaluates the fixed predecessor. No startup downloads or production activation is involved.

## Verification

**239 cross-batch data/artifact/model tests passed**, including all 200 question records, expected/actual report consistency, complete confusion-matrix denominators, heldout separation, privacy and inactive-candidate checks. These passing tests do not mean the 100 bot responses were all correct: the new candidate passed only 52 of the behavioral assertions. Ruff and Mypy (three tools) passed. Exact results and active-production health are in `verification.json`. The new 70 classifier examples have no >=0.85 character-ngram near overlaps with the 480 heldout rows; the maximum observed similarity is 0.5264.

## All questions, expected behavior and actual replies

### question100-v2-Q001 — I'm travelling to Nellore tomorrow; what is the nearest departure still available?

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

### question100-v2-Q002 — Please identify the departure that starts tomorrow's entire Nellore service schedule.

Expected: Find the earliest departure within one explicitly selected operating day, independent of the current time.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.

### question100-v2-Q003 — Tomorrow, after which Nellore departure will there be no more buses that day?

Expected: Find the final eligible departure inside the chosen calendar or operator-defined operating-day bounds.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

### question100-v2-Q004 — What scheduled choices connect my current Vijayawada stand with Nellore on the next day?

Expected: List scheduled services permitting boarding at the origin and later alighting at the destination.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
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

### question100-v2-Q005 — Filter tomorrow's Nellore departures to those starting beyond 9:15 PM.

Expected: Find eligible departures following an explicitly supplied lower time bound.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v2-Q006 — I want to leave for Nellore prior to 5:45 AM tomorrow; list those services.

Expected: Find eligible departures preceding an explicitly supplied upper time bound.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v2-Q007 — Check for a Nellore departure tomorrow approximately at quarter past seven in the evening.

Expected: Find departures within a documented tolerance window around a specified clock time.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q008 — Read the timetable entry for when this chosen service reaches its destination stop.

Expected: Retrieve the scheduled arrival time for the selected service and stop, labelling any operational override separately.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.

Trained candidate in isolated shadow:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.

### question100-v2-Q009 — For the departure I've picked, what is the elapsed travelling time in hours?

Expected: Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q010 — Is the current date included in the operating calendar for buses serving Nellore?

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

### question100-v2-Q011 — Across a day, how closely spaced are the bus runs serving this corridor?

Expected: Describe scheduled departure counts or intervals on a segment within a specified period, without assuming regular headways.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> There are 6 recorded departures on this date. Gaps between distinct departures (minutes): 10, 10, 75, 10, 10. This is not a guaranteed frequency.

### question100-v2-Q012 — Does your local data include extra Nellore runs or changed timings for a festival day?

Expected: Retrieve date-specific extra or changed schedules for a specified holiday, festival or special operating date.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
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
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00. Recorded timetable for the requested date, including local calendar exceptions; no official festival schedule is inferred.

### question100-v2-Q013 — What range of service classes is actually scheduled between my selected endpoints?

Expected: List the service classifications represented by eligible departures on the requested segment.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v2-Q014 — I'd prefer a cooled bus cabin; search air-conditioned departures for Nellore.

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

### question100-v2-Q015 — Remove every AC option from the Nellore list because I want an uncooled coach.

Expected: Find services explicitly known to be non-air-conditioned, excluding unknown configurations.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

### question100-v2-Q016 — Could I make the Nellore journey lying in a berth rather than sitting upright?

Expected: Find services with verified sleeping berths, independently of branded category and seat inventory.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> No eligible scheduled departures matched. Calendar coverage, publication or availability cannot be established from this diagnosis. Your restrictions are unchanged.

### question100-v2-Q017 — For my Nellore trip, find the coach type where the accommodation consists of seats.

Expected: Find services with verified seater accommodation rather than inferring layout from category branding.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Seat availability information is not available.

Trained candidate in isolated shadow:

> Seat availability information is not available.

### question100-v2-Q018 — Which listed runs to Nellore use battery propulsion instead of a combustion engine?

Expected: Find services with an explicitly assigned electric vehicle or configuration.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q019 — Can you describe the onboard equipment and comforts attached to this particular vehicle?

Expected: Report verified amenities of the selected assigned vehicle, retaining unknown feature states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q020 — What service features distinguish Demo sleeper from Demo electric in the database?

Expected: Explain recorded differences between two or more service categories without guaranteeing vehicle amenities.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Which service number do you mean? It must match one active service.

Trained candidate in isolated shadow:

> Which service number do you mean? It must match one active service.

### question100-v2-Q021 — Are wheelchair-friendly boarding arrangements offered by any service on this corridor?

Expected: Find departures meeting explicitly recorded accessibility requirements.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Which service number do you mean? It must match one active service.

Trained candidate in isolated shadow:

> Which service number do you mean? It must match one active service.

### question100-v2-Q022 — How many passenger places were built into the chosen coach's seating layout?

Expected: Report physical seat and berth capacity of the assigned configuration, not vacant inventory.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Recorded layout: 40 seats and 0 berths. This is not seat availability.

### question100-v2-Q023 — I don't wish to interchange anywhere; is Nellore served all the way by one coach?

Expected: Find a single service allowing the requested journey without a vehicle change.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v2-Q024 — Give the station-by-station stopping pattern followed by the bus I've selected.

Expected: Retrieve the ordered scheduled stopping pattern of the selected route variant or service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v2-Q025 — Will the selected coach travel by way of Ongole before it gets to Nellore?

Expected: Check or search for a route passing through a requested via point without asserting a passenger halt.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 8:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 8:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 8:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 9:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 9:56 PM.

Trained candidate in isolated shadow:

> Which intermediate station should the bus pass through?

### question100-v2-Q026 — Passing Ongole is not enough for me; is a stop there part of this trip's schedule?

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

### question100-v2-Q027 — Please show where this route authorizes passengers to enter the bus for their journey.

Expected: Identify locations at which passengers may board the selected service or destination-bound journey.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v2-Q028 — At what authorized dropping stops could a passenger leave this selected service?

Expected: Identify permitted drop-off locations or validate a requested alighting station on a selected service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v2-Q029 — Plan a route to Tirumala by linking an initial coach to an onward bus after a change.

Expected: Find feasible time-ordered multi-leg journeys respecting transfer windows and stop permissions.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Which service do you mean? Choose a listed bus or give its service number.

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### question100-v2-Q030 — If I avoid the itinerary currently shown, what other bus path could take me to Nellore?

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

### question100-v2-Q031 — Between the chosen pickup and drop stops, what route length in kilometres is stored?

Expected: Retrieve sourced cumulative or segment distance along the applicable route variant.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v2-Q032 — Can any chain of available bus services get a passenger from this stand to Tirumala?

Expected: Determine whether any feasible direct or connecting bus itinerary reaches the requested destination in the search period.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Scheduled or estimated journeys do not confirm GPS, seats or guaranteed connections. Transfers require the same physical station; inter-stand travel is unsupported. Concessions and through-ticket discounts are not evaluated. Active verified service disruption records are conservatively excluded when avoid_verified_disruptions is enabled. No eligible itinerary found within the horizon and resource bounds. Consider explicitly relaxing category, fare, time or transfer constraints. Results are bounded to the next 24 hours and configured transfer/resource limits. No result does not prove the destination is unreachable.

### question100-v2-Q033 — For the bus I'm currently referring to, what amount of money buys one passenger ticket?

Expected: Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q034 — Among the Nellore services with known prices, choose whichever costs the smallest amount.

Expected: Rank eligible services by known applicable segment fare; missing prices are never zero.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v2-Q035 — Please minimize travelling duration when selecting a Nellore bus from these results.

Expected: Rank eligible services by elapsed journey duration for the same requested segment.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> I could not complete that enquiry: Origin equals destination.

Trained candidate in isolated shadow:

> I could not complete that enquiry: Origin equals destination.

### question100-v2-Q036 — For an identical origin and destination, contrast the ticket amounts on the listed coaches.

Expected: Compare applicable prices for multiple services or categories on the same boarding segment and travel date.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.
> 2. Service DEMO-CONV-698c52cb-1: fare INR 101.00.
> 3. Service DEMO-CONV-3f8df292-2: fare INR 205.00.
> 4. Service DEMO-CONV-698c52cb-2: fare INR 205.00.

### question100-v2-Q037 — Has the local system recently recorded enough unused seats for a pair of passengers on my trip?

Expected: Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Seat availability information is not available.

Trained candidate in isolated shadow:

> Seat availability information is not available.

### question100-v2-Q038 — Before the day of travel, does the selected departure permit passengers to reserve seats?

Expected: Report whether reservations are supported for the selected service, separately from current seat availability.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Seat availability information is not available.

Trained candidate in isolated shadow:

> Seat availability information is not available.

### question100-v2-Q039 — Tell me the operator-approved methods for arranging and purchasing my bus ticket.

Expected: Describe locally recorded approved ticket booking channels and instructions without executing a purchase.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q040 — If I already have a ticket reference, is its confirmation state available in an authorized local record?

Expected: Read status of an existing booking only when an authorized local record is available; otherwise report unsupported or unavailable.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> This database enquiry does not support booking status.

### question100-v2-Q041 — Explain the passenger ticket-withdrawal rules, including any cancellation penalty that applies.

Expected: Explain locally stored passenger ticket cancellation terms, independently of operational trip cancellation.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v2-Q042 — What locally published conditions determine the ticket money returned to a passenger?

Expected: Explain applicable recorded refund rules or a supported calculation; never infer a refund without required policy data.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> This database enquiry does not support refund policy.

### question100-v2-Q043 — Would an eligible elderly passenger qualify for a concessional fare under this operator's rules?

Expected: Explain date-effective concession schemes and explicit eligibility requirements without assuming passenger qualification.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v2-Q044 — Before I bring a large suitcase, explain this operator's recorded baggage limits and surcharges.

Expected: Describe recorded baggage allowances, restrictions and applicable published luggage charges.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> This database enquiry does not support luggage rules.

Trained candidate in isolated shadow:

> This database enquiry does not support luggage rules.

### question100-v2-Q045 — Where does the newest verified tracking observation place the selected coach at present?

Expected: Report the freshest authoritative operational state or location, distinguishing scheduled-only, stale and unknown data.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v2-Q046 — Is this trip behind its timetable, and how many late-running minutes are officially recorded?

Expected: Report a verified delay duration or recorded reason for the selected dated trip and affected stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Delay information is not confirmed.

Trained candidate in isolated shadow:

> Delay information is not confirmed.

### question100-v2-Q047 — Has an authorized update withdrawn the particular trip that I selected from operation?

Expected: Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v2-Q048 — At this station, which numbered stand has been assigned and confirmed for my departure?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### question100-v2-Q049 — After taking operational updates into account, what is the freshest ETA for the incoming service?

Expected: Report a fresh verified operational arrival estimate; a scheduled arrival alone does not satisfy this intent.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q050 — Please distinguish the scheduled leaving time from evidence that my selected coach actually left.

Expected: Confirm departure only from an authoritative actual-departure event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v2-Q051 — Has anyone recorded that the incoming service has physically arrived at this bus station?

Expected: Confirm arrival only from an authoritative actual-arrival event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v2-Q052 — Do current route notices report roadworks, interruptions or detours affecting this journey?

Expected: Report verified diversions, suspensions or other incidents effective for the requested service or period.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v2-Q053 — Is the bay now allocated to my coach different from the one originally announced?

Expected: Confirm a platform reassignment by examining assignment history for the same trip and station.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v2-Q054 — Which origin, destination and route are associated with bus service number 3521?

Expected: Resolve a service identifier within operator and validity scope, requesting clarification if multiple records match.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.
> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.
> No matching information is available for that enquiry.

### question100-v2-Q055 — What public conveniences and waiting areas can passengers use at this bus terminal?

Expected: Report locally recorded passenger facilities and their verification or availability state at a station.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v2-Q056 — Please point me towards this terminal's passenger information and enquiry office.

Expected: Provide a recorded station enquiry/helpdesk contact, location or opening information.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v2-Q057 — My suitcase was accidentally left in a bus; which local process handles recovery of found belongings?

Expected: Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v2-Q058 — How would I reach the office or telephone contact of the operator responsible for this coach?

Expected: Provide published local operator or depot contact information relevant to the passenger's service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### question100-v2-Q059 — Guide me on foot from inside the terminal towards the departure area at bay six.

Expected: Provide recorded within-station directions or zone information without inventing an indoor route.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Recorded addresses and bay zones only; no indoor route is inferred.

### question100-v2-Q060 — I need to lodge a grievance about a bus staff member; which authorized channel should receive it?

Expected: Explain the locally recorded complaint or grievance channel and reporting instructions.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Recorded complaint contacts only; opening hours and freshness are not live-verified.

### question100-v2-Q061 — And what would that selected ride cost me?

Expected: Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v2-Q062 — Which bay should I go to for the one I've chosen?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> The platform has not been confirmed.

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### question100-v2-Q063 — Please retain that exact coach for the next question.

Expected: preserve selection. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
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

### question100-v2-Q064 — Use the second displayed departure as my choice.

Expected: select second. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q065 — Correction: the destination should be Tirumala for this journey.

Expected: dest tirumala. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Scheduled or estimated journeys do not confirm GPS, seats or guaranteed connections. Transfers require the same physical station; inter-stand travel is unsupported. Concessions and through-ticket discounts are not evaluated. Active verified service disruption records are conservatively excluded when avoid_verified_disruptions is enabled. No eligible itinerary found within the horizon and resource bounds. Consider explicitly relaxing category, fare, time or transfer constraints. Results are bounded to the next 24 hours and configured transfer/resource limits. No result does not prove the destination is unreachable.

### question100-v2-Q066 — Change where I'm going from Nellore to Tirupati, please.

Expected: dest tirupati. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v2-Q067 — I want this trip two days from today instead of tomorrow.

Expected: date plus two. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v2-Q068 — Keep only buses fitted with air conditioning for this search.

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

### question100-v2-Q069 — Please exclude cooled coaches and use non-AC ones instead.

Expected: filter non ac. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### question100-v2-Q070 — Change the accommodation preference to a sleeping berth.

Expected: filter sleeper. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q071 — I can spend no more than INR 250 on the ticket.

Expected: budget 250. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v2-Q072 — Please make the passenger count two for this journey.

Expected: passengers two. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v2-Q073 — Clear the maximum fare I supplied earlier.

Expected: remove budget. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.

Trained candidate in isolated shadow:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.

### question100-v2-Q074 — Look for a bus leaving after the departure I currently picked.

Expected: later departures. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v2-Q075 — You've got my bus choice wrong; let me choose another.

Expected: reject selection. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q076 — Clear this conversation so I can begin a different journey.

Expected: reset. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q077 — Could you say the last reply once more without changing anything?

Expected: repeat. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

### question100-v2-Q078 — How many hours on board for that very same selection?

Expected: Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q079 — Switch the pickup location for my ride to Ongole.

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

### question100-v2-Q080 — Change my dropping destination from Nellore to Ongole.

Expected: dest ongole. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo seater service DEMO4: scheduled departure 09 Nov 2026 at 2:28 AM. Fare INR 100.00.
> 2. Demo seater service DEMO46: scheduled departure 09 Nov 2026 at 4:22 AM. Fare INR 100.00.
> 3. Demo seater service DEMO88: scheduled departure 09 Nov 2026 at 6:16 AM. Fare INR 100.00.
> 4. Demo seater service DEMO25: scheduled departure 09 Nov 2026 at 3:25 PM. Fare INR 100.00.
> 5. Demo seater service DEMO67: scheduled departure 09 Nov 2026 at 5:19 PM. Fare INR 100.00.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q081 — Which Nellore bus comes next, and what ticket amount does that departure charge?

Expected: Find the earliest eligible departures after the passenger's requested threshold, including later operating dates.; Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
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

### question100-v2-Q082 — Describe both the halt sequence and the onboard facilities of my chosen coach.

Expected: Retrieve the ordered scheduled stopping pattern of the selected route variant or service.; Report verified amenities of the selected assigned vehicle, retaining unknown feature states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v2-Q083 — Tell me my bus's assigned platform together with any verified delay minutes.

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.; Report a verified delay duration or recorded reason for the selected dated trip and affected stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Delay information is not confirmed.
> The platform has not been confirmed.

Trained candidate in isolated shadow:

> Delay information is not confirmed.
> The platform has not been confirmed.

### question100-v2-Q084 — Find the opening Nellore departure and give the duration of that particular ride.

Expected: Find the earliest departure within one explicitly selected operating day, independent of the current time.; Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Your selected journey takes 120 minutes, including any transfer wait.

Trained candidate in isolated shadow:

> Your selected journey takes 120 minutes, including any transfer wait.

### question100-v2-Q085 — Set the ticket prices alongside each other and also tell me their journey durations.

Expected: Compare applicable prices for multiple services or categories on the same boarding segment and travel date.; Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v2-Q086 — What time is the final Nellore departure, and which service class operates it?

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

### question100-v2-Q087 — Check if this run has been cancelled and whether an actual departure was recorded.

Expected: Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request.; Confirm departure only from an authoritative actual-departure event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v2-Q088 — Search for a no-change bus journey and provide its kilometre length.

Expected: Find a single service allowing the requested journey without a vehicle change.; Retrieve sourced cumulative or segment distance along the applicable route variant.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The recorded route segment distance is 120.00 km.

### question100-v2-Q089 — Can two places be found on this departure, and does it accept advance reservations?

Expected: Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states.; Report whether reservations are supported for the selected service, separately from current seat availability.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v2-Q090 — I left luggage behind; give the recovery guidance and the responsible operator's contact details.

Expected: Provide published local operator or depot contact information relevant to the passenger's service.; Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> This database enquiry does not support luggage rules.

Trained candidate in isolated shadow:

> This database enquiry does not support luggage rules.

### question100-v2-Q091 — Who lifted the international hockey trophy last season?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Where would you like to travel?

Trained candidate in isolated shadow:

> Where would you like to travel?

### question100-v2-Q092 — Calculate the compound interest on a five-year bank deposit for me.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q093 — Describe the steps for baking a loaf of sourdough bread.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q094 — Will heavy rainfall be likely around Nellore over the coming weekend?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q095 — Write a short birthday poem for my younger sister.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q096 — Which treatment should someone take for an ear infection?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q097 — Help me choose a mobile phone with a good camera.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q098 — Summarize the plot of a famous detective novel.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v2-Q099 — How much is a kilogram of silver worth in today's market?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Which destination or bus would you like the fare for?

Trained candidate in isolated shadow:

> Which destination or bus would you like the fare for?

### question100-v2-Q100 — Find the derivative of a polynomial using calculus rules.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

