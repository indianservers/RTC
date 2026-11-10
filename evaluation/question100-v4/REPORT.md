# question100-v4: 100 new questions and expectation-based training

Actual running bot: **17/100** automated intent/context checks. Previous candidate shadow: **50/100**. Newly trained candidate shadow: **58/100**. Training-specific change: **+8 checks**.

All 100 questions were checked for exact novelty against prior batches and training before asking. There were 181 additional, separately counted setup requests to establish selected-service context. Every expected label/action was frozen before execution. These are agent-authored synthetic expectations, not human-reviewed independent data.

## What was trained

Added 60 single-intent and 10 OOS examples to the previous corpus: **2489 total training examples**. Kept 20 contextual and 10 multi-intent questions as structured regression targets outside the 60-way loss. Neither model learns a new dialogue state transition just because a structured target is stored. SVM and TextCNN were both retrained as versioned candidates; old weights and previous reports are preserved.

The 100-question batch is training material. Results on it are memorization/integration diagnostics, not independent accuracy. The live bot remains on deterministic rules; shadow results are from isolated DB copies with outbound socket/DNS access denied. No candidate was deployed.

## Separate synthetic holdout

- SVM raw in-scope accuracy on the unchanged 180-question synthetic holdout: **93.89% → 94.44%**; macro-F1 **0.9361 → 0.9412**.
- CNN raw in-scope accuracy on the unchanged 180-question synthetic holdout: **83.89% → 87.22%**; macro-F1 **0.8368 → 0.8691**.

CNN validation rejection calibration: **failed; reject-all policy**. No independent human-reviewed validation/test set exists. The holdout is a previously exposed synthetic regression set; it was not used for this batch's fitting or threshold selection. All raw/selective decisions and confusion matrices are saved in model-comparison.json.

## Interpretation and unresolved work

**42 checks remain unresolved.** Per-kind counts are stored in verification.json. These are automated assertions, not human semantic answer-quality ratings. Some checks only test retained state or intent labels; they do not prove completeness or appropriate wording. Selected context can make ordinary lexical rules dominate a statistical classifier. Contextual corrections and multi-intent handling still need separate dialogue/composition work; single-label fitting alone cannot fix them.

Recommendation: keep production unchanged pending independent review, validated uncertainty, conversation regression and explicit approval. Inspect holdout and control results rather than attributing the whole rules-to-candidate difference to this training batch. Model weights stay excluded from Git.

## Execution

`python scripts/question100.py baseline --version question100-v4 --previous-version question100-v3 --base-dataset training/datasets/question100-v3` freezes expectations and asks the live bot. `prepare` with the same arguments freezes the cumulative dataset. Use the existing train_english_recovery.py with `--dataset training/datasets/question100-v4 --output-version question100-v4` for svm and cnn. The evaluation and shadow scripts take the same version arguments; `shadow --previous` evaluates the fixed predecessor. No startup downloads or production activation is involved.

## Validation and scoring protocol

**453 cross-batch data/artifact/model validation tests passed**, together with Ruff and Mypy on three tools. These are integrity/regression tests, not 453 correctly answered enquiries; this batch's candidate passes 58/100 response assertions. The new 70 classifier examples have no detected >=0.85 character-ngram near-overlap with the 480 validation/holdout rows. All 400 questions across the four batches are distinct wordings.

This batch uses a stricter selection protocol. The second-option question starts with the first service selected, so retaining the previous choice cannot produce a false pass. Keeping a selected bus must preserve it and resolve the request without another clarification. All live/predecessor/trained runs use the same new protocol; direct score comparisons with earlier batches are inappropriate. Previous reports remain unchanged. Thirty dialogue/multi-intent targets are retained and checked, not falsely described as state transitions learned by a single-label classifier. No candidate is active in production. See `verification.json` for exact results and health evidence.

## All questions, expected behavior and actual replies

### question100-v4-Q001 — When can I leave next for Nellore on tomorrow's buses from this stand?

Expected: Find the earliest eligible departures after the passenger's requested threshold, including later operating dates.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

### question100-v4-Q002 — Nellore's first morning run tomorrow, sir: what departure time starts the schedule?

Expected: Find the earliest departure within one explicitly selected operating day, independent of the current time.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Recorded services match outside the requested time window. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match outside the requested time window. Your restrictions are unchanged.

### question100-v4-Q003 — What's my final chance tomorrow night to board a scheduled Nellore bus?

Expected: Find the final eligible departure inside the chosen calendar or operator-defined operating-day bounds.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

### question100-v4-Q004 — Show the services tomorrow that have Vijayawada and Nellore as my travel endpoints.

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

### question100-v4-Q005 — Tomorrow I cannot leave until 8:20 PM; find Nellore buses after that time.

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

### question100-v4-Q006 — I need a Nellore departure tomorrow earlier than 6:40 AM, if any are scheduled.

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

### question100-v4-Q007 — Can you search near 7:50 PM tomorrow for a Nellore departure rather than an entire evening?

Expected: Find departures within a documented tolerance window around a specified clock time.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> What departure time should I search around? For example, at 8 PM.

### question100-v4-Q008 — According to its timetable, when is this particular bus supposed to finish at Nellore?

Expected: Retrieve the scheduled arrival time for the selected service and stop, labelling any operational override separately.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.

### question100-v4-Q009 — How long would a passenger remain travelling between my selected stops on this coach?

Expected: Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Your selected journey takes 120 minutes, including any transfer wait.
> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Your selected journey takes 120 minutes, including any transfer wait.
> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v4-Q010 — On today's operating date, are any Nellore runs actually included in the service calendar?

Expected: Check which services operate on the station-local current date using calendars and exceptions.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Which service number do you mean? It must match one active service.

Trained candidate in isolated shadow:

> Which service number do you mean? It must match one active service.

### question100-v4-Q011 — What departure spacing and daily number of runs does this Nellore timetable provide?

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

### question100-v4-Q012 — Please check whether festival service additions or holiday departures to Nellore have been published.

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

### question100-v4-Q013 — For Nellore travel from here, which named categories of coach does the timetable offer?

Expected: List the service classifications represented by eligible departures on the requested segment.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> I could not complete that enquiry: Origin equals destination.

### question100-v4-Q014 — Can I make this Nellore journey in a coach whose air conditioning is available?

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

### question100-v4-Q015 — Please find an ordinary Nellore bus without AC rather than offering cooled coaches.

Expected: Find services explicitly known to be non-air-conditioned, excluding unknown configurations.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### question100-v4-Q016 — Are sleeping-berth coaches offered for the Nellore journey instead of seated accommodation?

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

### question100-v4-Q017 — I'd prefer to sit for the Nellore journey; show seater-type services rather than sleepers.

Expected: Find services with verified seater accommodation rather than inferring layout from category branding.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
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

### question100-v4-Q018 — Is there a scheduled Nellore bus powered by batteries that I could choose?

Expected: Find services with an explicitly assigned electric vehicle or configuration.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v4-Q019 — What facilities inside this chosen coach are recorded for passengers to use during travel?

Expected: Report verified amenities of the selected assigned vehicle, retaining unknown feature states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v4-Q020 — In terms of service and comfort, how is Demo sleeper unlike Demo electric?

Expected: Explain recorded differences between two or more service categories without guaranteeing vehicle amenities.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Which service number do you mean? It must match one active service.

Trained candidate in isolated shadow:

> Which service number do you mean? It must match one active service.

### question100-v4-Q021 — Which Nellore departures use a vehicle that is marked suitable for wheelchair access?

Expected: Find departures meeting explicitly recorded accessibility requirements.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No supporting local records are available for this enquiry. Only explicitly wheelchair-accessible assigned vehicle types match.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Only explicitly wheelchair-accessible assigned vehicle types match.

### question100-v4-Q022 — Please read the total passenger capacity from the seating or berth layout of my chosen vehicle.

Expected: Report physical seat and berth capacity of the assigned configuration, not vacant inventory.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Recorded layout: 40 seats and 0 berths. This is not seat availability.

### question100-v4-Q023 — Can I stay aboard just one coach between Vijayawada and Nellore, with no transfer required?

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

### question100-v4-Q024 — Please name all the scheduled calling stations of this coach, from the first halt onward.

Expected: Retrieve the ordered scheduled stopping pattern of the selected route variant or service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.

### question100-v4-Q025 — When it runs to Nellore, does the bus take a route by way of Ongole?

Expected: Check or search for a route passing through a requested via point without asserting a passenger halt.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Which service do you mean? Choose a listed bus or give its service number.

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### question100-v4-Q026 — Is a passenger stop in Ongole specifically scheduled for the selected bus's journey?

Expected: Confirm whether a selected service actually calls at a specific intermediate station and allows the relevant passenger action.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM.

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### question100-v4-Q027 — Which pickup locations on this service are authorized for a passenger to get in?

Expected: Identify locations at which passengers may board the selected service or destination-bound journey.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v4-Q028 — Which drop locations on this selected service are authorized for a passenger to get down?

Expected: Identify permitted drop-off locations or validate a requested alighting station on a selected service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v4-Q029 — Please arrange a feasible bus-to-bus connection towards Tirumala and identify the interchange.

Expected: Find feasible time-ordered multi-leg journeys respecting transfer windows and stop permissions.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No feasible connection matched the recorded stop times and your current restrictions. A single cause has not been established. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No feasible connection matched the recorded stop times and your current restrictions. A single cause has not been established. Your restrictions are unchanged.

### question100-v4-Q030 — What other routing to Nellore could I take if I do not follow the displayed bus itinerary?

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

### question100-v4-Q031 — How far in kilometres does this coach cover between the exact stops selected for my ride?

Expected: Retrieve sourced cumulative or segment distance along the applicable route variant.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.
> The recorded route segment distance is 120.00 km.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.
> The recorded route segment distance is 120.00 km.

### question100-v4-Q032 — Is there any feasible bus-network path from this stand that would get me to Tirumala?

Expected: Determine whether any feasible direct or connecting bus itinerary reaches the requested destination in the search period.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Scheduled or estimated journeys do not confirm GPS, seats or guaranteed connections. Transfers require the same physical station; inter-stand travel is unsupported. Concessions and through-ticket discounts are not evaluated. Active verified service disruption records are conservatively excluded when avoid_verified_disruptions is enabled. No eligible itinerary found within the horizon and resource bounds. Consider explicitly relaxing category, fare, time or transfer constraints. Results are bounded to the next 24 hours and configured transfer/resource limits. No result does not prove the destination is unreachable.

### question100-v4-Q033 — What ticket amount is recorded for travelling on this selected bus between my chosen stops?

Expected: Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v4-Q034 — Which priced Nellore service is the least expensive of the departure choices you can find?

Expected: Rank eligible services by known applicable segment fare; missing prices are never zero.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 3. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 4. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

### question100-v4-Q035 — Which bus option to Nellore would spend the minimum number of minutes on the journey?

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

### question100-v4-Q036 — Please contrast the known passenger fare amounts for these different Nellore departures.

Expected: Compare applicable prices for multiple services or categories on the same boarding segment and travel date.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v4-Q037 — Is the latest seat record recent enough to say whether two places remain on this run?

Expected: Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Seat availability information is not available.

### question100-v4-Q038 — Does the operator permit seats on this selected departure to be reserved in advance?

Expected: Report whether reservations are supported for the selected service, separately from current seat availability.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Seat availability information is not available.

Trained candidate in isolated shadow:

> Seat availability information is not available.

### question100-v4-Q039 — Where and through what approved channels can someone arrange a ticket with this operator?

Expected: Describe locally recorded approved ticket booking channels and instructions without executing a purchase.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### question100-v4-Q040 — Is there an authorized record stored locally that tells whether an already-made booking succeeded?

Expected: Read status of an existing booking only when an authorized local record is available; otherwise report unsupported or unavailable.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v4-Q041 — What rules and penalties govern a passenger cancelling a reserved ticket with this operator?

Expected: Explain locally stored passenger ticket cancellation terms, independently of operational trip cancellation.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> This database enquiry does not support cancellation policy.

### question100-v4-Q042 — If ticket money is to be returned, what refund eligibility and repayment rules are recorded?

Expected: Explain applicable recorded refund rules or a supported calculation; never infer a refund without required policy data.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> This database enquiry does not support refund policy.

### question100-v4-Q043 — Under the published concession scheme, what must a senior passenger satisfy to get a discount?

Expected: Explain date-effective concession schemes and explicit eligibility requirements without assuming passenger qualification.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Which RTC operator do you mean?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### question100-v4-Q044 — How much baggage does the ticket permit before this operator applies an additional luggage fee?

Expected: Describe recorded baggage allowances, restrictions and applicable published luggage charges.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.
> This database enquiry does not support luggage rules.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.
> This database enquiry does not support luggage rules.

### question100-v4-Q045 — Where has this selected coach most recently been located by a verified fresh tracking report?

Expected: Report the freshest authoritative operational state or location, distinguishing scheduled-only, stale and unknown data.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v4-Q046 — What confirmed late-running update, including the delay in minutes, exists for my chosen service?

Expected: Report a verified delay duration or recorded reason for the selected dated trip and affected stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Delay information is not confirmed.

Trained candidate in isolated shadow:

> Delay information is not confirmed.

### question100-v4-Q047 — Does the operational record say that the specific trip I've chosen was cancelled by the operator?

Expected: Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v4-Q048 — Where in this stand is the confirmed departure bay assigned to the coach I picked?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No supporting local records are available for this enquiry. Recorded addresses and bay zones only; no indoor route is inferred.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Recorded addresses and bay zones only; no indoor route is inferred.

### question100-v4-Q049 — What current arrival estimate has operations supplied after revising the original timetable?

Expected: Report a fresh verified operational arrival estimate; a scheduled arrival alone does not satisfy this intent.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

Trained candidate in isolated shadow:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v4-Q050 — Is there an observed leaving event confirming that this service has already departed our station?

Expected: Confirm departure only from an authoritative actual-departure event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v4-Q051 — Do staff observations confirm that this service has already come into the station?

Expected: Confirm arrival only from an authoritative actual-arrival event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v4-Q052 — Are any verified notices about closures or diversions interrupting bus service on my route?

Expected: Report verified diversions, suspensions or other incidents effective for the requested service or period.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v4-Q053 — Has my bus's currently confirmed stand number changed from its earlier allocated platform?

Expected: Confirm a platform reassignment by examining assignment history for the same trip and station.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The platform has not been confirmed.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

Trained candidate in isolated shadow:

> The platform has not been confirmed.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### question100-v4-Q054 — Use service number 3521 to find the corresponding bus route, starting point and destination.

Expected: Resolve a service identifier within operator and validity scope, requesting clarification if multiple records match.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.
> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.
> No matching information is available for that enquiry.

### question100-v4-Q055 — What recorded facilities for waiting, washing and drinking water are available in this station?

Expected: Report locally recorded passenger facilities and their verification or availability state at a station.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v4-Q056 — Where should I go inside this stand to speak to the passenger assistance counter staff?

Expected: Provide a recorded station enquiry/helpdesk contact, location or opening information.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v4-Q057 — A wallet was left behind on my bus seat; how can I enquire through the lost-and-found process?

Expected: Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v4-Q058 — What office address or telephone details can I use to reach the depot responsible for my coach?

Expected: Provide published local operator or depot contact information relevant to the passenger's service.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### question100-v4-Q059 — How would a passenger walk from the stand entrance across to departure platform six?

Expected: Provide recorded within-station directions or zone information without inventing an indoor route.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The platform has not been confirmed.

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### question100-v4-Q060 — If I want to report poor conduct by bus staff, which official grievance procedure should I follow?

Expected: Explain the locally recorded complaint or grievance channel and reporting instructions.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Recorded complaint contacts only; opening hours and freshness are not live-verified.

### question100-v4-Q061 — For that selection, what ticket payment would I need to make?

Expected: Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v4-Q062 — And where should I wait in this stand for the chosen departure?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### question100-v4-Q063 — Leave my selected coach as it is while we continue.

Expected: preserve selection. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v4-Q064 — Change my choice to the second departure shown in the list.

Expected: select second. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v4-Q065 — Replace the present destination with Tirumala, please.

Expected: dest tirumala. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v4-Q066 — Please revise the trip to end at Tirupati rather than Nellore.

Expected: dest tirupati. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v4-Q067 — Make the journey date the day after tomorrow, keeping the destination.

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

### question100-v4-Q068 — Narrow these choices down to buses that have AC.

Expected: filter ac. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
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

### question100-v4-Q069 — Switch my preference so that only non-air-conditioned buses are searched.

Expected: filter non ac. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No eligible scheduled departures matched. Calendar coverage, publication or availability cannot be established from this diagnosis. Your restrictions are unchanged.

### question100-v4-Q070 — I now want a berth, so search sleeper coaches for me.

Expected: filter sleeper. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### question100-v4-Q071 — My maximum ticket budget should be 250 rupees for this search.

Expected: budget 250. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v4-Q072 — Count two passengers for the trip we are discussing.

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

### question100-v4-Q073 — Take off the price limit that was applied to my search.

Expected: remove budget. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.

Trained candidate in isolated shadow:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.

### question100-v4-Q074 — Can you find departures following the one that is currently selected?

Expected: later departures. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

### question100-v4-Q075 — That selected service was a mistake; I wanted a different bus.

Expected: reject selection. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v4-Q076 — Remove all the trip context so I can start a new enquiry.

Expected: reset. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v4-Q077 — Show the answer you just gave me one more time.

Expected: repeat. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v4-Q078 — What would the total time travelling be for that chosen departure?

Expected: Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Your selected journey takes 120 minutes, including any transfer wait.

### question100-v4-Q079 — Make Ongole the point where I board for this ride.

Expected: origin ongole. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM.

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### question100-v4-Q080 — Please make Ongole my final alighting destination instead of Nellore.

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

### question100-v4-Q081 — Find the soonest Nellore departure and give the ticket cost of that same service.

Expected: Find the earliest eligible departures after the passenger's requested threshold, including later operating dates.; Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### question100-v4-Q082 — For this chosen coach, read the route's stopping sequence and the onboard facility list.

Expected: Retrieve the ordered scheduled stopping pattern of the selected route variant or service.; Report verified amenities of the selected assigned vehicle, retaining unknown feature states.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### question100-v4-Q083 — Check both the departure bay allocated to my bus and any confirmed lateness.

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.; Report a verified delay duration or recorded reason for the selected dated trip and affected stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### question100-v4-Q084 — What is the first bus to Nellore and how many minutes does that particular trip take?

Expected: Find the earliest departure within one explicitly selected operating day, independent of the current time.; Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.

### question100-v4-Q085 — Contrast the ticket charges for these options and their scheduled travel durations.

Expected: Compare applicable prices for multiple services or categories on the same boarding segment and travel date.; Calculate travel duration between the passenger's valid boarding and alighting stops.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.
> 2. Service DEMO-CONV-698c52cb-1: fare INR 101.00.
> 3. Service DEMO-CONV-3f8df292-2: fare INR 205.00.
> 4. Service DEMO-CONV-698c52cb-2: fare INR 205.00.

### question100-v4-Q086 — Find the closing departure for Nellore and tell me the category of coach used on it.

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

### question100-v4-Q087 — For my selected trip, check cancellation and whether actual departure was observed.

Expected: Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request.; Confirm departure only from an authoritative actual-departure event at the specified stop.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### question100-v4-Q088 — Look for a single-coach journey without interchange and state the distance it covers.

Expected: Find a single service allowing the requested journey without a vehicle change.; Retrieve sourced cumulative or segment distance along the applicable route variant.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### question100-v4-Q089 — Check for two available seats on this run and confirm whether advance reservation is supported.

Expected: Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states.; Report whether reservations are supported for the selected service, separately from current seat availability.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: PASS; predecessor: PASS; trained candidate: PASS.

Live reply:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> Seat availability information is not available.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> Seat availability information is not available.

### question100-v4-Q090 — Explain the found-property procedure for my forgotten bag and give the operating depot's contact.

Expected: Provide published local operator or depot contact information relevant to the passenger's service.; Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### question100-v4-Q091 — Who received the best-player award at the recent tennis tournament?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v4-Q092 — Explain how capital-gains tax applies when I sell a house.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v4-Q093 — Can you describe how to prepare a layered chocolate dessert at home?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v4-Q094 — Will the humidity around Nellore be high this coming Saturday?

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

### question100-v4-Q095 — Write a congratulatory message for my friend's university graduation.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v4-Q096 — What medical tests should I get for repeated stomach pain?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v4-Q097 — Suggest a reliable washing machine for a small family.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v4-Q098 — Give me a detailed summary of a historical fantasy novel.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### question100-v4-Q099 — What is the going market price for a tonne of copper?

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: FAIL; trained candidate: FAIL.

Live reply:

> Which destination or bus would you like the fare for?

Trained candidate in isolated shadow:

> Which destination or bus would you like the fare for?

### question100-v4-Q100 — Explain how to multiply two matrices and find their determinant.

Expected: out of scope. Facts must come from current DB records; missing, stale or unsupported information must remain explicit.
Automated checks — live: FAIL; predecessor: PASS; trained candidate: PASS.

Live reply:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

