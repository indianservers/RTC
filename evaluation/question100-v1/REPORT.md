# 100-question bot check and training

The actual running bot was asked **100 unique questions**, with **181 separate setup requests** establishing selected journeys. These are agent-authored synthetic expectations, not independent human labels.

Automated intent/context checks: live rules **28/100**; previous SVM shadow **62/100**; newly trained SVM shadow **64/100**. The training-specific gain over the previous candidate is **2 checks**. The larger difference from rules is not attributed solely to training these questions.

These are fixed intent/context assertions, not a human-rated answer-quality percentage. Some checks only verify state retention or recognition; a matching intent does not prove the answer is complete. Full original responses and structured results are in before.json, previous-shadow.json and after-shadow.json. The shadow runs use private DB copies with socket/DNS denial; production was not changed.

## Training and independent-evaluation limits

All 100 expectations are retained. **60 single-intent + 10 OOS questions** were added to the classifier corpus (2,279 total examples). **20 contextual + 10 multi-intent cases** are stored separately as structured dialogue/composition targets and executed as behavioral checks; they are not falsely treated as single-label SVM/CNN examples. Those 30 are not learned state transitions merely because they are saved in a dataset.

Both SVM and TensorFlow CNN candidates were retrained at models/english/nlp/question100-v1; previous checkpoints remain intact and weights are Git-ignored. New entries are CANDIDATE, unapproved and ineligible for production. Training-batch recognition/memorization is not independent accuracy.

On the unchanged 180-ID synthetic holdout, SVM raw accuracy changed **92.78% to 92.22%**, CNN **85.00% to 84.44%**. CNN rejection calibration again failed and its policy remains reject-all. No human-reviewed independent set exists. Both models identify all 60 class labels consistently. There is no justification to promote the new candidates on these results.

The 70 new classifier rows have no exact or >=0.85 character-ngram near overlaps with the 480 validation/holdout rows. Maximum measured similarity was 0.6982. Holdouts remain previously exposed synthetic regression sets, not newly independent evidence.

## Remaining behavior

The new shadow candidate still fails **36/100** checks. Context stayed **9/20** and multi-intent stayed **5/10**; classifier fitting alone does not repair these dialogue/composition rules. Generic clarifications, incorrect retained timing intent, unsupported enquiry routing, negation, budget/reset/repeat phrasing and out-of-scope questions containing place/price words remain visible below. Do not interpret a correct state-retention check as proof that the response wording was appropriate.

## Reproduction

Run `python scripts/question100.py baseline` once for a new batch, then `prepare`; baseline and manifests refuse overwrite. Train with the existing `scripts/train_english_recovery.py` using `--dataset training/datasets/question100-v1 --output-version question100-v1` for svm and cnn. Run `scripts/evaluate_question100.py`, and `scripts/question100.py shadow` / `shadow --previous` for isolated comparisons. All evaluation questions that are later used for training must remain labelled training checks. Scripts and versioned artifacts document the specific run.

## Every question, expectation and actual answer

### Q001 — Could you pick the next Nellore departure that I can catch tomorrow?

Expected: Find the earliest eligible departures after the passenger's requested threshold, including later operating dates.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

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

### Q002 — At what hour does tomorrow's Nellore timetable begin its daily runs?

Expected: Find the earliest departure within one explicitly selected operating day, independent of the current time.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q003 — Which Nellore departure brings tomorrow's service day to a close?

Expected: Find the final eligible departure inside the chosen calendar or operator-defined operating-day bounds.

Live check: FAIL; previous candidate: FAIL; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

### Q004 — Give me the full choice of buses linking Vijayawada with Nellore tomorrow.

Expected: List scheduled services permitting boarding at the origin and later alighting at the destination.

Live check: FAIL; previous candidate: FAIL; trained candidate: PASS.

Live bot:

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

### Q005 — I can leave only after 8 PM tomorrow; which Nellore buses fit?

Expected: Find eligible departures following an explicitly supplied lower time bound.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.
> 4. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 10 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 10 Nov 2026 at 7:21 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 10 Nov 2026 at 7:21 PM. Fare INR 205.00.

### Q006 — Which Nellore services tomorrow depart earlier than seven in the morning?

Expected: Find eligible departures preceding an explicitly supplied upper time bound.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Recorded services match outside the requested time window. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### Q007 — Is a Nellore coach scheduled near half past eight tomorrow evening?

Expected: Find departures within a documented tolerance window around a specified clock time.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> What departure time should I search around? For example, at 8 PM.

### Q008 — At what timetabled hour will the coach I chose get into Nellore?

Expected: Retrieve the scheduled arrival time for the selected service and stop, labelling any operational override separately.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.

### Q009 — How many travel minutes does my chosen bus take to reach Nellore?

Expected: Calculate travel duration between the passenger's valid boarding and alighting stops.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> Your selected journey takes 120 minutes, including any transfer wait.

### Q010 — Does the local calendar show Nellore buses in operation on today's date?

Expected: Check which services operate on the station-local current date using calendars and exceptions.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

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

### Q011 — What intervals separate scheduled departures on the Nellore corridor?

Expected: Describe scheduled departure counts or intervals on a segment within a specified period, without assuming regular headways.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> There are 6 recorded departures on this date. Gaps between distinct departures (minutes): 10, 10, 75, 10, 10. This is not a guaranteed frequency.

### Q012 — Has any additional festival timetable for Nellore been published locally?

Expected: Retrieve date-specific extra or changed schedules for a specified holiday, festival or special operating date.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

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

### Q013 — Which kinds of coach can a traveller choose on the Nellore route?

Expected: List the service classifications represented by eligible departures on the requested segment.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### Q014 — Please restrict my Nellore options to vehicles with cabin air conditioning.

Expected: Find services whose assigned vehicle or configuration explicitly supports air conditioning.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

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

### Q015 — For Nellore, discard air-conditioned coaches and retain only non-AC services.

Expected: Find services explicitly known to be non-air-conditioned, excluding unknown configurations.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### Q016 — I would like a sleeping berth on the trip to Nellore; are sleeper coaches listed?

Expected: Find services with verified sleeping berths, independently of branded category and seat inventory.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### Q017 — Please look for Nellore buses offering seated accommodation instead of berths.

Expected: Find services with verified seater accommodation rather than inferring layout from category branding.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

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

### Q018 — Are any Nellore departures operated using battery-electric vehicles?

Expected: Find services with an explicitly assigned electric vehicle or configuration.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### Q019 — What passenger comforts are recorded for the exact coach I picked?

Expected: Report verified amenities of the selected assigned vehicle, retaining unknown feature states.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Leg 1: AC is available; sleeper is not available.

### Q020 — Explain how Demo electric and Demo sleeper differ as service categories.

Expected: Explain recorded differences between two or more service categories without guaranteeing vehicle amenities.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Which service number do you mean? It must match one active service.

Trained candidate in isolated shadow:

> Which service number do you mean? It must match one active service.

### Q021 — Can you find a Nellore service that accommodates wheelchair boarding?

Expected: Find departures meeting explicitly recorded accessibility requirements.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Which service number do you mean? It must match one active service.

Trained candidate in isolated shadow:

> Which service number do you mean? It must match one active service.

### Q022 — What is the installed passenger seating capacity of the vehicle I selected?

Expected: Report physical seat and berth capacity of the assigned configuration, not vacant inventory.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Recorded layout: 40 seats and 0 berths. This is not seat availability.

### Q023 — Can a single bus carry me from Vijayawada to Nellore without changing coaches?

Expected: Find a single service allowing the requested journey without a vehicle change.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### Q024 — Read out the calling points of my selected bus in their proper order.

Expected: Retrieve the ordered scheduled stopping pattern of the selected route variant or service.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q025 — Does my selected route take the path through Ongole on the way?

Expected: Check or search for a route passing through a requested via point without asserting a passenger halt.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Which service do you mean? Choose a listed bus or give its service number.

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### Q026 — Is an actual passenger halt at Ongole included for this service?

Expected: Confirm whether a selected service actually calls at a specific intermediate station and allows the relevant passenger action.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM.

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### Q027 — At which recorded stops am I permitted to join the selected coach?

Expected: Identify locations at which passengers may board the selected service or destination-bound journey.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### Q028 — Which recorded stops permit me to end my ride on this service?

Expected: Identify permitted drop-off locations or validate a requested alighting station on a selected service.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### Q029 — Work out a bus connection to Tirumala with a transfer at an intermediate station.

Expected: Find feasible time-ordered multi-leg journeys respecting transfer windows and stop permissions.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> No feasible connection matched the recorded stop times and your current restrictions. A single cause has not been established. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No feasible connection matched the recorded stop times and your current restrictions. A single cause has not been established. Your restrictions are unchanged.

### Q030 — Could you suggest a different bus itinerary to Nellore besides the one displayed?

Expected: Find different feasible paths or transfer patterns for the same journey, relative to an optional selected route.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

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

### Q031 — What kilometre distance is recorded for my selected boarding-to-alighting segment?

Expected: Retrieve sourced cumulative or segment distance along the applicable route variant.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The recorded route segment distance is 120.00 km.

### Q032 — Is Tirumala reachable at all through the bus network starting here?

Expected: Determine whether any feasible direct or connecting bus itinerary reaches the requested destination in the search period.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> No supporting local records are available for this enquiry. Scheduled or estimated journeys do not confirm GPS, seats or guaranteed connections. Transfers require the same physical station; inter-stand travel is unsupported. Concessions and through-ticket discounts are not evaluated. Active verified service disruption records are conservatively excluded when avoid_verified_disruptions is enabled. No eligible itinerary found within the horizon and resource bounds. Consider explicitly relaxing category, fare, time or transfer constraints. Results are bounded to the next 24 hours and configured transfer/resource limits. No result does not prove the destination is unreachable.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Scheduled or estimated journeys do not confirm GPS, seats or guaranteed connections. Transfers require the same physical station; inter-stand travel is unsupported. Concessions and through-ticket discounts are not evaluated. Active verified service disruption records are conservatively excluded when avoid_verified_disruptions is enabled. No eligible itinerary found within the horizon and resource bounds. Consider explicitly relaxing category, fare, time or transfer constraints. Results are bounded to the next 24 hours and configured transfer/resource limits. No result does not prove the destination is unreachable.

### Q033 — Quote the recorded passenger ticket charge for the exact departure I selected.

Expected: Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### Q034 — Put the Nellore services in budget order and pick the minimum known fare.

Expected: Rank eligible services by known applicable segment fare; missing prices are never zero.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### Q035 — Find the Nellore coach with the least scheduled time spent travelling.

Expected: Rank eligible services by elapsed journey duration for the same requested segment.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

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

### Q036 — How much would each of these Nellore coach options charge for the same trip?

Expected: Compare applicable prices for multiple services or categories on the same boarding segment and travel date.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### Q037 — Is there a recent local record showing two vacant places on my chosen trip?

Expected: Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Seat availability information is not available.

Trained candidate in isolated shadow:

> Seat availability information is not available.

### Q038 — Is advance seat reservation supported for the particular service I selected?

Expected: Report whether reservations are supported for the selected service, separately from current seat availability.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### Q039 — Which authorized channel should I use to purchase a ticket for this operator?

Expected: Describe locally recorded approved ticket booking channels and instructions without executing a purchase.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q040 — Can this offline system verify whether an existing reservation is confirmed?

Expected: Read status of an existing booking only when an authorized local record is available; otherwise report unsupported or unavailable.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### Q041 — What ticket-cancellation conditions and deductions does this operator publish?

Expected: Explain locally stored passenger ticket cancellation terms, independently of operational trip cancellation.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### Q042 — Under the recorded refund rules, what happens to the money paid for a cancelled ticket?

Expected: Explain applicable recorded refund rules or a supported calculation; never infer a refund without required policy data.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### Q043 — What eligibility conditions apply to a senior traveller seeking a reduced ticket rate?

Expected: Explain date-effective concession schemes and explicit eligibility requirements without assuming passenger qualification.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### Q044 — What baggage allowance and excess-luggage charges are recorded for this operator?

Expected: Describe recorded baggage allowances, restrictions and applicable published luggage charges.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> This database enquiry does not support luggage rules.

Trained candidate in isolated shadow:

> This database enquiry does not support luggage rules.

### Q045 — Do you have a fresh verified position for the bus I chose, rather than its planned route?

Expected: Report the freshest authoritative operational state or location, distinguishing scheduled-only, stale and unknown data.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### Q046 — What current verified lateness is recorded against my selected trip?

Expected: Report a verified delay duration or recorded reason for the selected dated trip and affected stop.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Delay information is not confirmed.

### Q047 — Does the latest local operational information mark my particular departure as cancelled?

Expected: Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Current operational status is not confirmed.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.

### Q048 — Which departure bay is confirmed for the exact trip I selected at this stand?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### Q049 — What revised arrival estimate is available from recent operational observations?

Expected: Report a fresh verified operational arrival estimate; a scheduled arrival alone does not satisfy this intent.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

Trained candidate in isolated shadow:

> The selected journey's recorded arrival is 09 Nov 2026 at 9:21 PM.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### Q050 — Has staff actually observed this bus leaving, as opposed to its departure time passing?

Expected: Confirm departure only from an authoritative actual-departure event at the specified stop.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### Q051 — Is there a verified observation that this incoming coach has reached the stand?

Expected: Confirm arrival only from an authoritative actual-arrival event at the specified stop.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### Q052 — Are any published closures or diversions currently affecting services on this route?

Expected: Report verified diversions, suspensions or other incidents effective for the requested service or period.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### Q053 — Has the dispatcher replaced this service's earlier bay assignment with a different one?

Expected: Confirm a platform reassignment by examining assignment history for the same trip and station.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### Q054 — Look up the route and destination belonging to service identifier 3521.

Expected: Resolve a service identifier within operator and validity scope, requesting clarification if multiple records match.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Recorded stops: Vijayawada, Ongole, Nellore.

### Q055 — Which waiting, drinking-water and washroom facilities are recorded for this terminal?

Expected: Report locally recorded passenger facilities and their verification or availability state at a station.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> No matching information is available for that enquiry.

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### Q056 — Where can I locate the staffed passenger enquiry counter in this bus stand?

Expected: Provide a recorded station enquiry/helpdesk contact, location or opening information.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### Q057 — I have left a bag inside a coach; what local lost-property procedure should I follow?

Expected: Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No matching information is available for that enquiry.

### Q058 — What telephone or office contact is recorded for the depot operating my service?

Expected: Provide published local operator or depot contact information relevant to the passenger's service.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### Q059 — Which way should I walk inside this terminal to get to platform six?

Expected: Provide recorded within-station directions or zone information without inventing an indoor route.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> The platform has not been confirmed.

Trained candidate in isolated shadow:

> The platform has not been confirmed.

### Q060 — Where should a passenger submit a formal complaint about conductor behaviour?

Expected: Explain the locally recorded complaint or grievance channel and reporting instructions.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> No supporting local records are available for this enquiry. Recorded complaint contacts only; opening hours and freshness are not live-verified.

Trained candidate in isolated shadow:

> No supporting local records are available for this enquiry. Recorded complaint contacts only; opening hours and freshness are not live-verified.

### Q061 — What's the price for that option?

Expected: Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> The fare for your selected service is INR 205.00.

Trained candidate in isolated shadow:

> The fare for your selected service is INR 205.00.

### Q062 — And the bay for that one?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q063 — Keep the bus I picked.

Expected: Acknowledge and retain the current selected journey.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q064 — The number two choice, please.

Expected: Select the second result using the current result list.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### Q065 — Actually, make the destination Tirumala.

Expected: Change destination to Tirumala and invalidate dependent selection.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Okay, I've applied your correction. No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Okay, I've applied your correction. No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

### Q066 — Not Nellore; Tirupati instead.

Expected: Change destination to Tirupati and invalidate dependent selection.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> No published active direct service is recorded for this segment. Connecting options may still exist. Your restrictions are unchanged.

### Q067 — Move this journey to the day after tomorrow.

Expected: Change travel date to the day after tomorrow.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 10 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 10 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 10 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 10 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 10 Nov 2026 at 8:56 PM. Fare INR 205.00.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 10 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 10 Nov 2026 at 7:21 PM. Fare INR 205.00.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 10 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 10 Nov 2026 at 8:46 PM. Fare INR 101.00.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 10 Nov 2026 at 8:56 PM. Fare INR 205.00.

### Q068 — Only show air-conditioned departures now.

Expected: Search only AC services without silently retaining an incompatible trip.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> The category 'show air-conditioned departures now' is not in the current database. Which recorded category would you like: Demo electric, Demo express, Demo seater, Demo sleeper?

Trained candidate in isolated shadow:

> The category 'show air-conditioned departures now' is not in the current database. Which recorded category would you like: Demo electric, Demo express, Demo seater, Demo sleeper?

### Q069 — I meant a bus without AC.

Expected: Search only non-AC services.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Okay, I've applied your correction. Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Okay, I've applied your correction. Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### Q070 — Let me lie down; sleeper options only.

Expected: Search sleeper services.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

Trained candidate in isolated shadow:

> Recorded services match when the bus category restrictions are removed. Your restrictions are unchanged.

### Q071 — Set my spending limit to 250 rupees.

Expected: Apply maximum fare 250 to a fresh search.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q072 — Two people are travelling.

Expected: Set two passengers and revalidate the current journey.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

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

### Q073 — Remove the budget restriction.

Expected: Remove the previously supplied fare cap.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q074 — Show later departures instead.

Expected: Search departures later than the current selection.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.

### Q075 — That is not the coach I wanted.

Expected: Reject the selected bus and ask which option is intended.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> No eligible scheduled departures matched. Calendar coverage, publication or availability cannot be established from this diagnosis. Your restrictions are unchanged.

### Q076 — Forget the current journey and start over.

Expected: Clear prior journey and pending clarification.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> Please clarify which bus information you need.

### Q077 — Please repeat your previous answer.

Expected: Repeat the previous assistant answer without changing the journey.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q078 — Tell me the travel time for that same coach.

Expected: Calculate travel duration between the passenger's valid boarding and alighting stops.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q079 — Can we board at Ongole instead?

Expected: Change boarding station to Ongole and invalidate dependent selection.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 7:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 8:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 8:56 PM.

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q080 — Could we get off at Ongole rather than Nellore?

Expected: Change destination to Ongole and invalidate dependent selection.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 8:11 PM.
> 2. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 8:21 PM.
> 3. Demo electric service DEMO-CONV-3f8df292-3: scheduled departure 09 Nov 2026 at 8:31 PM.
> 4. Demo electric service DEMO-CONV-698c52cb-1: scheduled departure 09 Nov 2026 at 9:46 PM.
> 5. Demo electric service DEMO-CONV-698c52cb-2: scheduled departure 09 Nov 2026 at 9:56 PM.

Trained candidate in isolated shadow:

> Which service do you mean? Choose a listed bus or give its service number.

### Q081 — Find the next Nellore service, and tell me its fare.

Expected: Find the earliest eligible departures after the passenger's requested threshold, including later operating dates. Retrieve an applicable date-effective fare for the actual boarding and alighting segment and selected service or category.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

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

### Q082 — For the selected coach, list the stops and onboard amenities.

Expected: Retrieve the ordered scheduled stopping pattern of the selected route variant or service. Report verified amenities of the selected assigned vehicle, retaining unknown feature states.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Leg 1: AC is available; sleeper is not available.
> Recorded stops: Vijayawada, Ongole, Nellore.

Trained candidate in isolated shadow:

> Leg 1: AC is available; sleeper is not available.
> Recorded stops: Vijayawada, Ongole, Nellore.

### Q083 — Which platform is my bus using, and is it delayed?

Expected: Report the currently valid confirmed station bay assignment for a specific dated trip. Report a verified delay duration or recorded reason for the selected dated trip and affected stop.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> The platform has not been confirmed.
> Delay information is not confirmed.

Trained candidate in isolated shadow:

> The platform has not been confirmed.
> Delay information is not confirmed.

### Q084 — Show the first Nellore departure and its journey duration.

Expected: Find the earliest departure within one explicitly selected operating day, independent of the current time. Calculate travel duration between the passenger's valid boarding and alighting stops.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 1. Service DEMO-CONV-3f8df292-1: journey time 120 minutes.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-1: scheduled departure 09 Nov 2026 at 7:11 PM. Fare INR 101.00.
> 1. Service DEMO-CONV-3f8df292-1: journey time 120 minutes.

### Q085 — Compare the fares and travel times for these buses.

Expected: Compare applicable prices for multiple services or categories on the same boarding segment and travel date. Calculate travel duration between the passenger's valid boarding and alighting stops.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> 1. Service DEMO-CONV-3f8df292-1: fare INR 101.00.
> 2. Service DEMO-CONV-698c52cb-1: fare INR 101.00.
> 3. Service DEMO-CONV-3f8df292-2: fare INR 205.00.
> 4. Service DEMO-CONV-698c52cb-2: fare INR 205.00.

### Q086 — When does the last bus leave, and what category is it?

Expected: Find the final eligible departure inside the chosen calendar or operator-defined operating-day bounds. List the service classifications represented by eligible departures on the requested segment.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-698c52cb-3: scheduled departure 09 Nov 2026 at 9:06 PM.

### Q087 — Is my selected bus cancelled, or has it already departed?

Expected: Confirm operational cancellation of a specific service occurrence, not a passenger's ticket cancellation request. Confirm departure only from an authoritative actual-departure event at the specified stop.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Current operational status is not confirmed.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

Trained candidate in isolated shadow:

> Current operational status is not confirmed.
> No supporting local records are available for this enquiry. No dated trip record; scheduled times do not establish operational facts.

### Q088 — Find a direct bus and show its route distance.

Expected: Find a single service allowing the requested journey without a vehicle change. Retrieve sourced cumulative or segment distance along the applicable route variant.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> Recorded stops: Vijayawada, Ongole, Nellore.
> The recorded route segment distance is 120.00 km.

Trained candidate in isolated shadow:

> 1. Demo electric service DEMO-CONV-3f8df292-2: scheduled departure 09 Nov 2026 at 7:21 PM. Fare INR 205.00.
> Recorded stops: Vijayawada, Ongole, Nellore.
> The recorded route segment distance is 120.00 km.

### Q089 — Check whether there are seats and whether reservations are supported.

Expected: Report fresh segment-specific inventory for a dated trip and requested seat count, distinguishing unknown and stale states. Report whether reservations are supported for the selected service, separately from current seat availability.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Seat availability information is not available.

Trained candidate in isolated shadow:

> Seat availability information is not available.

### Q090 — Give me the operator contact and lost-property guidance.

Expected: Provide published local operator or depot contact information relevant to the passenger's service. Provide the locally recorded lost-property reporting contact or procedure without claiming an item was found.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Which RTC operator do you mean?

Trained candidate in isolated shadow:

> Which RTC operator do you mean?

### Q091 — Who won the badminton world championship most recently?

Expected: Decline unrelated questions without answering them as RTC facts.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q092 — Could you work out the monthly repayment on my home loan?

Expected: Decline unrelated questions without answering them as RTC facts.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q093 — Give me a recipe for a vegetable omelette.

Expected: Decline unrelated questions without answering them as RTC facts.

Live check: PASS; previous candidate: PASS; trained candidate: PASS.

Live bot:

> I can help with RTC bus schedules, fares, routes and station information.

Trained candidate in isolated shadow:

> I can help with RTC bus schedules, fares, routes and station information.

### Q094 — Is there a chance of thunderstorms in Nellore next week?

Expected: Decline unrelated questions without answering them as RTC facts.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

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

### Q095 — Translate this Spanish paragraph into French for me.

Expected: Decline unrelated questions without answering them as RTC facts.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q096 — Which antibiotic should I use for a persistent sore throat?

Expected: Decline unrelated questions without answering them as RTC facts.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q097 — Recommend a gaming laptop for video editing.

Expected: Decline unrelated questions without answering them as RTC facts.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q098 — Tell me a funny story about a talking parrot.

Expected: Decline unrelated questions without answering them as RTC facts.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.

### Q099 — What is the current gold price per gram?

Expected: Decline unrelated questions without answering them as RTC facts.

Live check: FAIL; previous candidate: FAIL; trained candidate: FAIL.

Live bot:

> Which destination or bus would you like the fare for?

Trained candidate in isolated shadow:

> Which destination or bus would you like the fare for?

### Q100 — Explain how to solve a quadratic equation by completing the square.

Expected: Decline unrelated questions without answering them as RTC facts.

Live check: FAIL; previous candidate: PASS; trained candidate: PASS.

Live bot:

> Are you asking about bus timings, a fare, a platform or a route?

Trained candidate in isolated shadow:

> I can help with RTC bus enquiries; that request appears outside this scope.
