# RTC OFFLINE AI — PHASE 2 FINAL
## Complete English Model Training, Conversational Intelligence and Production Readiness

You are a senior NLP researcher, machine-learning engineer, conversational AI architect, MLOps specialist and Python backend developer.

Continue development in the EXISTING RTC Offline AI repository.

Previous phases:
- Phase 1: RTC database, enquiry engine, NLP foundation and model setup.
- Phase 2A: Canonical taxonomy of 60 RTC enquiry intents.
- Phase 2B: English training dataset generation, targeting 200+ examples per intent.

Your task is to complete ALL remaining Phase 2 activities:
- 2C: Dataset validation and preparation.
- 2D: Model training and comparison.
- 2E: Advanced conversational intelligence.
- 2F: End-to-end integration and final evaluation.

Do not stop at planning or scaffolding.

Do not implement passenger or admin UI.

Do not begin Phase 3 audio orchestration.

All runtime inference must work entirely offline.

No GPT, OpenAI, Gemini, Claude or cloud-based AI services.

---

# PART A — VERIFY EXISTING WORK

Inspect the actual repository.

Do not assume that previous phases are finished merely because documentation says so.

Verify:
1. Existing 60-intent registry.
2. Intent-code mappings and legacy aliases.
3. Dataset files and actual row counts.
4. JSONL schema correctness.
5. Dataset generation provenance.
6. Database-backed entity resolver.
7. Existing enquiry APIs.
8. Existing conversation manager.
9. Local training dependencies.
10. Model registry.

Create a requirements matrix showing:
- Implemented
- Partially implemented
- Missing
- Broken
- Tested

Preserve existing working code, migrations, datasets and model checkpoints.

Do not duplicate implementations.

# PART B — DATASET VALIDATION (2C)

## B1. Audit the entire dataset

Validate:
- Canonical intent labels
- Entity types
- Character span offsets
- Dialogue acts
- Required metadata
- Language labels
- Context-dependent examples
- Multi-intent annotations
- Negation constraints
- Dataset provenance

Identify:
- Exact duplicates
- Normalized duplicates
- Near duplicates
- Contradictory labels
- Unrealistic questions
- Invalid entity annotations
- Unbalanced intent coverage
- Repetitive templates
- Leakage risks

Do not automatically change ambiguous labels without logging the correction.

Separate automatically generated examples from genuinely human-reviewed examples.

## B2. Prepare trustworthy data splits

Create:
- Training split
- Validation split
- Synthetic challenge split
- Independent test split, only if independently collected data exists

Use group-based splitting.

Group related utterances by:
- Template family
- Parent example
- Paraphrase family
- Conversation scenario
- Source utterance

Prevent related examples from appearing across train and test splits.

Never call synthetic generated test examples an independent real-world evaluation.

Use deterministic random seeds.

## B3. Dataset versioning

Generate a versioned dataset manifest containing:
- Dataset version
- Exact record counts
- Train/validation/test counts
- Intent distribution
- Source type distribution
- SHA-256 checksums
- Generation version
- Validation rules
- Split seed
- Known limitations

Use read-only finalized dataset snapshots for training.

# PART C — MODEL TRAINING (2D)

Train and benchmark at least two models.

## C1. TF-IDF + Linear SVM

Use:
- Scikit-learn
- Word n-grams
- Character n-grams
- Linear SVM
- Appropriate feature scaling/weighting
- Class balancing where beneficial

Train on the prepared dataset.

Evaluate calibrated probabilities or correctly described decision scores.

Do not represent raw SVM margins as probabilities.

Persist the entire fitted preprocessing and classification pipeline.

## C2. TensorFlow TextCNN

Build a compact classifier with:
- TextVectorization
- Embedding layer
- Conv1D layers
- GlobalMaxPooling1D
- Dense layers
- Dropout
- Classification output

Use:
- Fixed random seeds
- Early stopping
- Validation monitoring
- Learning-rate scheduling
- Model checkpoints
- Training history
- Class weighting if justified

Train using the local CPU or GPU as available.

Do not require MuRIL or IndicConformer to complete English NLP training.

## C3. Multi-intent handling

Determine whether the existing single-label model is sufficient for ordinary enquiries.

For multi-intent examples:
- Train a separate multi-label classifier, OR
- Implement a compositional query decomposition strategy.

Choose based on actual evaluation results.

Do not incorrectly treat multiple simultaneous intents as a single-label problem.

Maintain canonical intent IDs.

## C4. Dialogue-act classification

Train or implement a suitable classifier for:
- Greeting
- Affirmation
- Negation
- Correction
- Clarification reply
- Change destination
- Change date
- Change bus type
- Repeat request
- Reset conversation
- Out-of-scope

Use deterministic handling for explicit commands where more reliable.

Do not confuse a dialogue act with a transport enquiry intent.

# PART D — MODEL EVALUATION

Evaluate SVM, TensorFlow and the existing deterministic baseline on exactly the same suitable splits.

Measure:
- Accuracy
- Macro precision
- Macro recall
- Macro-F1
- Weighted F1
- Per-intent precision/recall/F1
- Confusion matrix
- Out-of-scope detection
- Multi-intent exact-match accuracy
- False confident prediction rate
- Inference latency
- Peak memory usage
- Serialized model size

Analyze confusion pairs such as:

NEXT_BUS vs FIRST_BUS
LAST_BUS vs DEPARTURES_BEFORE
ARRIVAL_TIME vs ESTIMATED_ARRIVAL
DIRECT_BUS vs CONNECTING_BUSES
GET_FARE vs FARE_COMPARISON
BUS_DELAY vs LIVE_BUS_STATUS
BUS_PLATFORM vs PLATFORM_CHANGE
BOOKING_STATUS vs SEAT_AVAILABILITY

Select the best model based on correct classification and realistic deployment constraints.

A simpler model should win if it performs better.

Do not automatically select TensorFlow because it is neural.

# PART E — CONFIDENCE CALIBRATION

Implement calibrated confidence estimates where supported.

Determine:
- High-confidence execution threshold
- Medium-confidence clarification threshold
- Low-confidence rejection threshold
- Out-of-scope detection criteria

Tune thresholds using validation data.

Never invent confidence numbers.

Incorrect high-confidence enquiries are more damaging than asking a short clarification.

Implement safe fallback to deterministic matching where appropriate.

# PART F — ENTITY EXTRACTION IMPROVEMENTS

Strengthen database-backed extraction of:
- Origin
- Destination
- Intermediate stops
- Bus categories
- Vehicle features
- Operator
- Service number
- Date/time expressions
- Travel periods
- Passenger counts
- Fare limits
- Platform references
- Concession categories

Handle:
- Negation
- Exclusion
- Corrections
- Conflicting constraints
- Relative dates
- Times crossing midnight
- Ambiguous locations

Use validated aliases and database entity IDs.

Do not hardcode a small destination list.

Do not interpret "not AC" as AC=true.

If a location remains ambiguous, request clarification.

# PART G — CONVERSATIONAL INTELLIGENCE (2E)

Implement or improve:

RTCConversationEngine

Support true multi-turn state tracking.

Example:

Passenger:
"When is the next bus to Nellore?"

System:
Returns database results.

Passenger:
"Is it AC?"

System:
Retains destination and selected journey context.

Passenger:
"What about Super Luxury?"

System:
Updates bus category filter.

Passenger:
"Tomorrow morning?"

System:
Updates travel date and time preferences.

Passenger:
"No, I meant Tirupati."

System:
Corrects the destination and invalidates stale trip selection.

Passenger:
"Which is cheapest?"

System:
Finds the lowest valid known fare among matching services.

Support:
- Context retention
- Slot filling
- Follow-up questions
- Corrections
- Multiple intents
- Elliptical utterances
- Clarification states
- Selected trip references
- Context expiry
- Session reset
- Concurrent session isolation

Implement context transitions explicitly.

Do not rely on memorized demonstration dialogues.

# PART H — DATABASE-GROUNDED RESPONSE ENGINE

Connect the trained model to the existing RTCEnquiryEngine.

Pipeline:

User text
→ Normalization
→ Intent inference
→ Entity extraction
→ Dialogue/context resolution
→ Structured RTC enquiry
→ Local database
→ English response template

Requirements:
- No generated SQL from model output.
- No fabricated schedules or fares.
- No invented seat availability.
- No invented platform numbers.
- No unsupported booking confirmations.
- Clear demo-data labelling.
- Unknown and stale status handling.
- Graceful backend failures.

All passenger-facing operational answers must originate from database results.

# PART I — PRODUCTION MODEL REGISTRY

Implement:
- Model versioning
- Checkpoint metadata
- Dataset version linkage
- Preprocessing version linkage
- Intent label mapping
- Evaluation report linkage
- Model compatibility checks
- Candidate model registration
- Approval and promotion
- Rollback capability

Suggested lifecycle:

CANDIDATE
→ EVALUATED
→ APPROVED
→ ACTIVE

Allow rollback to the previous working model.

Do not promote a model based only on training accuracy.

# PART J — INFERENCE SERVICE

Implement a reusable offline English inference service.

Required methods:

classify_intent()
classify_multiple_intents()
extract_entities()
identify_dialogue_act()
interpret_query()
process_conversation()
reset_session()

Expose or reuse:

POST /api/v1/nlp/interpret
POST /api/v1/conversation/message
POST /api/v1/conversation/reset
GET /api/v1/models/status
GET /api/v1/nlp/health

Model loading:
- Local paths only
- No runtime downloading
- Load model once per process
- Validate label-map compatibility
- Thread-safe inference
- Bounded input length
- Controlled failure handling

Keep business logic independent of TensorFlow or scikit-learn.

# PART K — REALISTIC CONVERSATION TESTING

Create at least 500 multi-turn test conversations.

Include:
- Normal enquiries
- Short follow-up questions
- Corrections
- Switching destination
- Switching dates
- Selecting different buses
- Comparing fares
- Asking about intermediate stops
- Ambiguous references
- Unknown platform
- Unknown seat availability
- Cancelled service
- Multiple simultaneous intents
- Out-of-scope questions
- Session reset

Test correctness of resulting database requests, not merely whether an intent label matches.

Measure:
- Intent accuracy
- Entity accuracy
- Context transition accuracy
- Enquiry execution accuracy
- Final response correctness

Use deterministic clocks and known database fixtures.

# PART L — PERFORMANCE OPTIMIZATION

Benchmark on actual available hardware:

- Cold model load
- Warm inference
- End-to-end text enquiry
- Database query duration
- Memory use
- Concurrent sessions

Targets:
- Intent macro-F1 >= 0.95
- Entity extraction F1 >= 0.97
- Context correctness >= 0.95
- End-to-end answer accuracy >= 0.95
- Median NLP inference under 100 ms on target CPU

These are aspirational targets, not assumed achievements.

If missed, document measured results and improvement priorities.

# PART M — OFFLINE CERTIFICATION

Ensure:
- All required model files exist locally.
- No inference request calls the internet.
- Model loading uses local files only.
- No remote fonts, CDNs or services.
- No external logging or telemetry.
- SQLite/PostgreSQL runs locally.
- The entire text enquiry pipeline works without internet.

Run OS-enforced network-isolated tests where permissions and environment allow.

If complete isolation cannot be verified, state the limitation.

# PART N — AUTOMATED REGRESSION

Run:
- Dataset validation
- Model evaluation
- NLP unit tests
- Conversation integration tests
- Enquiry engine tests
- API tests
- Ruff
- Mypy
- Offline smoke tests

Preserve all previous Phase 1 functionality.

Report actual pass/fail counts.

Do not alter or weaken tests merely to obtain a passing result.

# PART O — DOCUMENTATION AND DELIVERABLES

Create or update:

docs/PHASE_2_FINAL_REPORT.md
docs/MODEL_COMPARISON.md
docs/DATASET_QUALITY_REPORT.md
docs/CONVERSATION_ENGINE.md
docs/OFFLINE_DEPLOYMENT.md

Save:
- Trained SVM pipeline
- Trained TensorFlow model
- Tokenizer/vectorizer assets
- Intent label map
- Dataset manifests
- Evaluation results
- Model registry
- Reproducible training scripts
- Confusion matrices
- Benchmark results

# FINAL ACCEPTANCE REQUIREMENTS

Phase 2 is COMPLETE only if:

1. Dataset is validated and versioned.
2. SVM model is actually trained and evaluated.
3. TensorFlow model is actually trained and evaluated.
4. Best model is selected based on measured results.
5. Multi-intent recognition works.
6. Entity extraction works against RTC database masters.
7. Conversation context and corrections work.
8. All passenger facts come from local database queries.
9. Model artifacts load offline.
10. Actual performance metrics are recorded.
11. Backend regression tests pass.
12. No UI or cloud inference was introduced.

If any major requirement is incomplete, report:

PHASE 2 INCOMPLETE

Do not mark the phase complete based solely on generated datasets, training scripts or test placeholders.

Execute the remaining Phase 2 work now.

At the end, show exact implementation status, measured model metrics, unresolved issues and Phase 3 readiness.