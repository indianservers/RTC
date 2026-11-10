# question100-v5: 100 new questions and expectation-based training

Actual running bot: **18/100** automated intent/context checks. Previous candidate shadow: **53/100**. Newly trained candidate shadow: **57/100**. Training-specific change: **+4 checks**.

All 100 questions were checked for exact novelty against prior batches and training before asking. There were 181 additional, separately counted setup requests to establish selected-service context. Every expected label/action was frozen before execution. These are agent-authored synthetic expectations, not human-reviewed independent data.

## What was trained

Added 60 single-intent and 10 OOS examples to the previous corpus: **2559 total training examples**. Kept 20 contextual and 10 multi-intent questions as structured regression targets outside the 60-way loss. Neither model learns a new dialogue state transition just because a structured target is stored. SVM and TextCNN were both retrained as versioned candidates; old weights and previous reports are preserved.

The 100-question batch is training material. Results on it are memorization/integration diagnostics, not independent accuracy. The live bot remains on deterministic rules; shadow results are from isolated DB copies with outbound socket/DNS access denied. No candidate was deployed.

## Separate synthetic holdout

- SVM raw in-scope accuracy on the unchanged 180-question synthetic holdout: **94.44% → 92.78%**; macro-F1 **0.9412 → 0.9236**.
- CNN raw in-scope accuracy on the unchanged 180-question synthetic holdout: **87.22% → 85.56%**; macro-F1 **0.8691 → 0.8522**.

CNN validation rejection calibration: **failed; reject-all policy**. No independent human-reviewed validation/test set exists. The holdout is a previously exposed synthetic regression set; it was not used for this batch's fitting or threshold selection. All raw/selective decisions and confusion matrices are saved in model-comparison.json.

## Interpretation and unresolved work

**43 checks remain unresolved.** Per-kind counts are stored in verification.json. These are automated assertions, not human semantic answer-quality ratings. Some checks only test retained state or intent labels; they do not prove completeness or appropriate wording. Selected context can make ordinary lexical rules dominate a statistical classifier. Contextual corrections and multi-intent handling still need separate dialogue/composition work; single-label fitting alone cannot fix them.

Recommendation: keep production unchanged pending independent review, validated uncertainty, conversation regression and explicit approval. Inspect holdout and control results rather than attributing the whole rules-to-candidate difference to this training batch. Model weights stay excluded from Git.

## Execution

`python scripts/question100.py baseline --version question100-v5 --previous-version question100-v4 --base-dataset training/datasets/question100-v4` freezes expectations and asks the live bot. `prepare` with the same arguments freezes the cumulative dataset. Use the existing train_english_recovery.py with `--dataset training/datasets/question100-v5 --output-version question100-v5` for svm and cnn. The evaluation and shadow scripts take the same version arguments; `shadow --previous` evaluates the fixed predecessor. No startup downloads or production activation is involved.

## Verification

**560 cross-batch data/artifact/model validation tests passed**, with Ruff and Mypy on four tools. Those are integrity checks, not 560 successful bot answers: the trained shadow candidate passes only 57/100 response assertions in this batch. There are 500 distinct question wordings across the five batches. The 70 new classifier examples have no detected character-ngram overlap at or above 0.85 with the 480 validation/holdout rows; holdout file hashes remain unchanged. Current bus-category names were fetched from the local DB.

The stricter selection protocol from batch four remains in use: the second-option test starts from option one, and retaining a selection must resolve without another clarification. All three comparisons within this batch use the same protocol. The 30 contextual/multi-intent expectations are retained and checked separately, not claimed as learned state transitions. Production remains on deterministic rules. See `verification.json` for exact results and health evidence.

## All questions, expected behavior and actual replies

### question100-v5-Q001 — For Nellore tomorrow, which departure is next in line for me to catch?

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

### question100-v5-Q002 — What is the opening time of the complete Nellore bus schedule for tomorrow?

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

### question100-v5-Q003 — Please locate tomorrow's Nellore run that leaves later than every other service that day.

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

### question100-v5-Q004 — I'd like tomorrow's list of departures serving the Vijayawada-to-Nellore journey.

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

### question100-v5-Q005 — Show Nellore buses tomorrow whose leaving time falls after 9:40 PM.

Expected: Find eligible departures following an explicitly supplied lower time bound.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 10 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 10 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 10 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 10 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 10 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 10 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v5-Q006 — List tomorrow's Nellore runs with a departure time before 7:25 AM.

Expected: Find eligible departures preceding an explicitly supplied upper time bound.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Recorded services match outside the requested time window. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v5-Q007 — Search within a small time range near 8:10 PM tomorrow for a Nellore bus.

Expected: Find departures within a documented tolerance window around a specified clock time.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> What departure time should I search around? For example, at 8 PM.

### question100-v5-Q008 — For this selected trip, what destination-reaching hour appears in its schedule?

Expected: Retrieve the scheduled arrival time for the selected service and stop, labelling any operational override separately.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.

### question100-v5-Q009 — What amount of time does the selected coach spend covering my travel segment?

Expected: Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Your selected journey takes 120 minutes, including any transfer wait.

### question100-v5-Q010 — Do the service calendars include any Nellore buses running on this day?

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

### question100-v5-Q011 — What daily service count and gap between successive departures does Nellore have?

Expected: Describe scheduled departure counts or intervals on a segment within a specified period, without assuming regular headways.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> There are 6 recorded departures on this date. Gaps between distinct departures (minutes): 10, 10, 75, 10, 10. This is not a guaranteed frequency.

### question100-v5-Q012 — Have extra buses or special timings been recorded for Nellore during the holiday festival?

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

### question100-v5-Q013 — What coach-class choices are represented by the available services on this Nellore corridor?

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

### question100-v5-Q014 — For Nellore, find a departure operated with an air-conditioned coach cabin.

Expected: Find services whose assigned vehicle or configuration explicitly supports air conditioning.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
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

### question100-v5-Q015 — I want Nellore options where air conditioning is absent, not the AC category.

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

### question100-v5-Q016 — On a Nellore service, is there an accommodation type with a berth I can lie in?

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

### question100-v5-Q017 — Find a Nellore coach offering seated travel rather than sleeping-berth travel.

Expected: Find services with verified seater accommodation rather than inferring layout from category branding.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
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

### question100-v5-Q018 — Does this route's timetable offer any Nellore service using an electric-powered bus?

Expected: Find services with an explicitly assigned electric vehicle or configuration.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No matching information is available for that enquiry.
> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.
> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v5-Q019 — Please give the recorded list of passenger amenities fitted inside this selected bus.

Expected: Report verified amenities of the selected assigned vehicle, retaining unknown feature states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Leg 1: AC is available; sleeper is not available.

Trained candidate in isolated shadow:

> Leg 1: AC is available; sleeper is not available.

### question100-v5-Q020 — Help me understand the service-feature contrast between Demo sleeper and Demo electric.

Expected: Explain recorded differences between two or more service categories without guaranteeing vehicle amenities.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### question100-v5-Q021 — Is wheelchair-compatible boarding recorded for any of the Nellore coach options?

Expected: Find departures meeting explicitly recorded accessibility requirements.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No supporting local records are available for this enquiry. Only explicitly wheelchair-accessible assigned vehicle types match.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Only explicitly wheelchair-accessible assigned vehicle types match.

### question100-v5-Q022 — Tell me how many passenger places the selected vehicle's installed layout is designed to provide.

Expected: Report physical seat and berth capacity of the assigned configuration, not vacant inventory.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Recorded layout: 40 seats and 0 berths. This is not seat availability.

### question100-v5-Q023 — Can Nellore be reached from Vijayawada on one through service without an interchange?

Expected: Find a single service allowing the requested journey without a vehicle change.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Which service number do you mean? It must match one active service.

Trained candidate in isolated shadow:

> Which service number do you mean? It must match one active service.

### question100-v5-Q024 — What is the complete ordered set of passenger halts followed by my chosen departure?

Expected: Retrieve the ordered scheduled stopping pattern of the selected route variant or service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v5-Q025 — Does the selected bus follow a path that goes through Ongole before reaching Nellore?

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

### question100-v5-Q026 — Will this specific service make a scheduled stop for passengers at Ongole?

Expected: Confirm whether a selected service actually calls at a specific intermediate station and allows the relevant passenger action.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Which service number do you mean? It must match one active service.

Trained candidate in isolated shadow:

> Which service number do you mean? It must match one active service.

### question100-v5-Q027 — Identify the stops on this chosen run where getting onto the coach is permitted.

Expected: Identify locations at which passengers may board the selected service or destination-bound journey.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v5-Q028 — Identify the stops on this chosen run where leaving the coach is permitted.

Expected: Identify permitted drop-off locations or validate a requested alighting station on a selected service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v5-Q029 — How could I reach Tirumala by catching an initial service and then an onward connecting bus?

Expected: Find feasible time-ordered multi-leg journeys respecting transfer windows and stop permissions.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Which service number do you mean? It must match one active service.

Trained candidate in isolated shadow:

> Which service number do you mean? It must match one active service.

### question100-v5-Q030 — Search for a substitute bus itinerary to Nellore instead of the current routing choice.

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

### question100-v5-Q031 — What distance in km lies along the route between my selected pickup and drop points?

Expected: Retrieve sourced cumulative or segment distance along the applicable route variant.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v5-Q032 — Does the local bus network contain any possible journey from this stand to Tirumala?

Expected: Determine whether any feasible direct or connecting bus itinerary reaches the requested destination in the search period.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Scheduled or estimated journeys do not confirm GPS, seats or guaranteed connections. Transfers require the same physical station; inter-stand travel is unsupported. Concessions and through-ticket discounts are not evaluated. Active verified service disruption records are conservatively excluded when avoid_verified_disruptions is enabled. No eligible itinerary found within the horizon and resource bounds. Consider explicitly relaxing category, fare, time or transfer constraints. Results are bounded to the next 24 hours and configured transfer/resource limits. No result does not prove the destination is unreachable.

### question100-v5-Q033 — Tell me the fare amount for the selected coach on the precise segment I've chosen.

Expected: Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v5-Q034 — From services with a recorded fare to Nellore, pick the one needing the lowest ticket payment.

Expected: Rank eligible services by known applicable segment fare; missing prices are never zero.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v5-Q035 — From the Nellore choices, pick the service that completes its journey in the shortest duration.

Expected: Rank eligible services by elapsed journey duration for the same requested segment.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Which service number do you mean? It must match one active service.

Trained candidate in isolated shadow:

> Which service number do you mean? It must match one active service.

### question100-v5-Q036 — For the same travel segment, show how the fares of these departure options differ.

Expected: Compare applicable prices for multiple services or categories on the same boarding segment and travel date.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.
> 2. Service DEMO-CONV-698c52cb-1: fare INR 101.00.
> 3. Service DEMO-CONV-3f8df292-2: fare INR 205.00.
> 4. Service DEMO-CONV-698c52cb-2: fare INR 205.00.

### question100-v5-Q037 — Is there sufficiently fresh local seat information to check room for two travellers on this trip?

Expected: Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Seat availability information is not available.

### question100-v5-Q038 — Is reserving a place beforehand a facility supported on the coach I've chosen?

Expected: Report whether reservations are supported for the selected service, separately from current seat availability.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v5-Q039 — What authorized ticket-purchase channels are listed for the operator of this service?

Expected: Describe locally recorded approved ticket booking channels and instructions without executing a purchase.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### question100-v5-Q040 — Can an already issued reservation reference be checked against a permitted local booking record?

Expected: Read status of an existing booking only when an authorized local record is available; otherwise report unsupported or unavailable.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v5-Q041 — I am enquiring about ticket cancellation conditions and fees, not whether my bus was cancelled.

Expected: Explain locally stored passenger ticket cancellation terms, independently of operational trip cancellation.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v5-Q042 — What repayment of the ticket fare is allowed under the operator's documented refund conditions?

Expected: Explain applicable recorded refund rules or a supported calculation; never infer a refund without required policy data.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v5-Q043 — For a senior passenger, what fare reduction eligibility and required proof are specified locally?

Expected: Explain date-effective concession schemes and explicit eligibility requirements without assuming passenger qualification.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v5-Q044 — Please explain the baggage entitlement for one ticket and charges beyond the permitted allowance.

Expected: Describe recorded baggage allowances, restrictions and applicable published luggage charges.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> This database enquiry does not support luggage rules.

Trained candidate in isolated shadow:

> This database enquiry does not support luggage rules.

### question100-v5-Q045 — What is the last fresh verified observation of this coach's present location along its journey?

Expected: Report the freshest authoritative operational state or location, distinguishing scheduled-only, stale and unknown data.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

### question100-v5-Q046 — Is any confirmed delay duration recorded against the bus that I currently have selected?

Expected: Report a verified delay duration or recorded reason for the selected dated trip and affected stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Delay information is not confirmed.
> Your selected journey takes 120 minutes, including any transfer wait.

Trained candidate in isolated shadow:

> Delay information is not confirmed.
> Your selected journey takes 120 minutes, including any transfer wait.

### question100-v5-Q047 — Has an authorized operational notice cancelled my selected dated trip rather than just changing its timing?

Expected: Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v5-Q048 — What confirmed platform number at this bus stand should I use for the selected trip?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> The platform has not been confirmed.

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### question100-v5-Q049 — What revised ETA, based on recent operational information, applies to this incoming coach?

Expected: Report a fresh verified operational arrival estimate; a scheduled arrival alone does not satisfy this intent.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v5-Q050 — Does an actual departure observation confirm that the selected bus has gone from this stand?

Expected: Confirm departure only from an authoritative actual-departure event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v5-Q051 — Does an actual arrival observation confirm that the selected bus is already at this stand?

Expected: Confirm arrival only from an authoritative actual-arrival event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.

Trained candidate in isolated shadow:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.

### question100-v5-Q052 — Do active notices describe any road restrictions or service interruptions affecting the route?

Expected: Report verified diversions, suspensions or other incidents effective for the requested service or period.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v5-Q053 — Was the confirmed bay for my service switched after an earlier platform had been assigned?

Expected: Confirm a platform reassignment by examining assignment history for the same trip and station.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The platform has not been confirmed.

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### question100-v5-Q054 — Find the scheduled route and destination for the bus whose service number is 3521.

Expected: Resolve a service identifier within operator and validity scope, requesting clarification if multiple records match.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Which service do you mean? Choose a listed bus or give its service number.

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### question100-v5-Q055 — Please list the local terminal's recorded waiting spaces, toilets and drinking-water conveniences.

Expected: Report locally recorded passenger facilities and their verification or availability state at a station.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v5-Q056 — At this station, where can a passenger find the staffed enquiry and assistance desk?

Expected: Provide a recorded station enquiry/helpdesk contact, location or opening information.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v5-Q057 — I forgot a parcel inside a coach; what found-property office or procedure should I use?

Expected: Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v5-Q058 — How can someone contact the operating depot's office for the bus I am referring to?

Expected: Provide published local operator or depot contact information relevant to the passenger's service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### question100-v5-Q059 — Which walking directions inside this terminal lead a passenger towards bay six?

Expected: Provide recorded within-station directions or zone information without inventing an indoor route.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Recorded addresses and bay zones only; no indoor route is inferred.

### question100-v5-Q060 — Please describe how a traveller should formally report a complaint about transport staff behaviour.

Expected: Explain the locally recorded complaint or grievance channel and reporting instructions.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No supporting local records are available for this enquiry. Recorded complaint contacts only; opening hours and freshness are not live-verified.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Recorded complaint contacts only; opening hours and freshness are not live-verified.

### question100-v5-Q061 — Can you quote the rupee amount for that exact option?

Expected: Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v5-Q062 — Where is the assigned stand for that particular departure?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### question100-v5-Q063 — Don't alter the coach I selected for the following enquiry.

Expected: preserve selection. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v5-Q064 — Please switch from my current choice to option two in these results.

Expected: select second. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v5-Q065 — I need the destination changed to Tirumala for this same travel plan.

Expected: dest tirumala. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v5-Q066 — Use Tirupati as the destination now; Nellore was the wrong place.

Expected: dest tirupati. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v5-Q067 — Please put the travel date on the day after tomorrow for this journey.

Expected: date plus two. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 10 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 10 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 10 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 10 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 10 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v5-Q068 — Exclude anything without AC from the current departure search.

Expected: filter ac. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### question100-v5-Q069 — Only non-AC coaches should remain in my updated search.

Expected: filter non ac. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### question100-v5-Q070 — Please apply a sleeper-berth preference to these options.

Expected: filter sleeper. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### question100-v5-Q071 — Set the upper fare I am willing to pay to INR 250.

Expected: budget 250. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v5-Q072 — Update this journey enquiry for a party of two passengers.

Expected: passengers two. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v5-Q073 — I no longer want the maximum ticket price filter applied.

Expected: remove budget. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.

Trained candidate in isolated shadow:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.

### question100-v5-Q074 — Find a run that departs later than my current chosen service.

Expected: later departures. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v5-Q075 — I didn't intend to select this coach; please let me correct the choice.

Expected: reject selection. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v5-Q076 — Erase this journey context and begin again with no selected trip.

Expected: reset. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v5-Q077 — Repeat the latest answer you gave, without replacing my journey selection.

Expected: repeat. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v5-Q078 — For the coach currently selected, how long would I spend on the ride?

Expected: Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Your selected journey takes 120 minutes, including any transfer wait.

Trained candidate in isolated shadow:

> Your selected journey takes 120 minutes, including any transfer wait.

### question100-v5-Q079 — Please replace my boarding station with Ongole for this trip.

Expected: origin ongole. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM.

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v5-Q080 — Set the place where I get off to Ongole rather than the previous Nellore destination.

Expected: dest ongole. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 8:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 8:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 8:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 9:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 9:56 PM.

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### question100-v5-Q081 — Show the next available Nellore bus and the fare charged by that specific departure.

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

### question100-v5-Q082 — Please provide both the stopping stations and inside-the-coach facilities for my selection.

Expected: Retrieve the ordered scheduled stopping pattern of the selected route variant or service.; Report verified amenities of the selected assigned vehicle, retaining unknown feature states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v5-Q083 — For the selected run, what bay is confirmed and how much delay is recorded?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.; Report a verified delay duration or recorded reason for the selected dated trip and affected stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.
> Delay information is not confirmed.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.
> Delay information is not confirmed.

### question100-v5-Q084 — Find the first Nellore service of the day and state that service's journey duration.

Expected: Find the earliest departure within one explicitly selected operating day, independent of the current time.; Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 1. Service DEMO-CONV-3f8df292-1: journey time 120 minutes.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 1. Service DEMO-CONV-3f8df292-1: journey time 120 minutes.

### question100-v5-Q085 — Compare these buses by their fare amounts as well as the length of time travelling.

Expected: Compare applicable prices for multiple services or categories on the same boarding segment and travel date.; Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v5-Q086 — Identify the last Nellore bus and give the coach category associated with that departure.

Expected: Find the final eligible departure inside the chosen calendar or operator-defined operating-day bounds.; List the service classifications represented by eligible departures on the requested segment.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

### question100-v5-Q087 — Check whether the selected run was cancelled and whether it has actually left the station.

Expected: Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request.; Confirm departure only from an authoritative actual-departure event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v5-Q088 — Find an uninterrupted single-bus option and give the route length for that journey.

Expected: Find a single service allowing the requested journey without a vehicle change.; Retrieve sourced cumulative or segment distance along the applicable route variant.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v5-Q089 — Look for two vacant places on this departure and tell me whether it supports reservations.

Expected: Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states.; Report whether reservations are supported for the selected service, separately from current seat availability.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Seat availability information is not available.

Trained candidate in isolated shadow:

> Seat availability information is not available.

### question100-v5-Q090 — Provide lost-item reporting guidance for my forgotten parcel along with the depot contact.

Expected: Provide published local operator or depot contact information relevant to the passenger's service.; Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v5-Q091 — Who is the reigning champion in the international chess competition?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v5-Q092 — How do I compare returns from two stock-market investment funds?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v5-Q093 — Give instructions for cooking a creamy mushroom pasta dish.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v5-Q094 — What will the outdoor temperature in Nellore be over the next weekend?

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

### question100-v5-Q095 — Draft a thank-you letter for my child's schoolteacher.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v5-Q096 — What could be the medical cause of persistent knee pain?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v5-Q097 — Recommend a home printer that can produce good colour photographs.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v5-Q098 — Describe the main characters of a well-known romantic comedy film.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v5-Q099 — How much does crude oil cost in the commodity market today?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Which destination or bus would you like the fare for?

Trained candidate in isolated shadow:

> Which destination or bus would you like the fare for?

### question100-v5-Q100 — Show me how to solve simultaneous equations using algebra.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

