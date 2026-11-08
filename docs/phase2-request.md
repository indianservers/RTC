# RTC OFFLINE AI — PHASE 2 OF 6
## Train, Evaluate and Strengthen the English Conversational NLP Engine

You are a senior machine-learning engineer, NLP researcher, conversational AI architect, MLOps engineer and Python backend specialist.

Continue in the EXISTING RTC Offline AI repository.

PROJECT GOAL:
Create a highly accurate, entirely offline English-language conversational intelligence engine for RTC bus enquiries.

Initial scope: APSRTC, Andhra Pradesh.
Future scope: Other Indian transport operators and languages.

IMPORTANT:
- English only for active training and evaluation.
- Preserve all existing Telugu/Tanglish models, aliases and code.
- Do not start Telugu model training.
- No cloud AI, GPT or external inference.
- No passenger or admin UI until Phase 4.
- Do not rebuild working database or enquiry code.
- Implement, train, evaluate and test actual models.
- Do not stop at architecture documents.

---

# 1. AUDIT PREVIOUS PHASES

Inspect the real repository.

Check:

1. PostgreSQL/SQLite schema.
2. Enquiry engine and all implemented intents.
3. NLP preprocessing.
4. Existing deterministic classifier.
5. TensorFlow/Keras installation.
6. Existing TF-IDF/SVM classifier.
7. Saved checkpoints.
8. Training dataset.
9. Conversation manager.
10. English Vosk installation.
11. English TTS installation.
12. Offline model registry.

For each component, report:
- Implemented
- Tested
- Incomplete
- Missing
- Broken

Do not rely only on README or previous completion statements.

Continue existing implementations rather than creating duplicates.

---

# 2. BUILD AN ENGLISH RTC INTENT DATASET

Create a versioned dataset of at least 10,000 reviewed English utterances, targeting 40–60 distinct enquiry intents.

Target roughly 200–300 examples per intent, with additional examples for ambiguous and multi-intent requests.

Do not claim all records are human-reviewed unless they actually are.

Store generated synthetic examples separately from human-reviewed examples.

Example categories:

## Timing
NEXT_BUS
FIRST_BUS
LAST_BUS
BUS_AT_TIME
DEPARTURES_AFTER
DEPARTURES_BEFORE
ARRIVAL_TIME
JOURNEY_DURATION

## Bus types
AVAILABLE_BUS_TYPES
AC_BUS_AVAILABILITY
NON_AC_BUS_AVAILABILITY
SLEEPER_AVAILABILITY
SEATER_AVAILABILITY
BUS_AMENITIES
ELECTRIC_BUS_AVAILABILITY

## Route
DIRECT_BUS
ROUTE_STOPS
BUS_VIA_LOCATION
INTERMEDIATE_STOP
CONNECTING_BUSES
ALTERNATIVE_ROUTES

## Fare and availability
GET_FARE
FARE_COMPARISON
CHEAPEST_BUS
FASTEST_BUS
SEAT_AVAILABILITY
RESERVATION_SUPPORTED
CONCESSION_ENQUIRY
LUGGAGE_RULES

## Operational
BUS_DELAY
BUS_CANCELLATION
BUS_PLATFORM
LIVE_BUS_STATUS
SERVICE_DISRUPTION
STATION_FACILITIES
LOST_PROPERTY
STATION_HELPDESK

## Dialogue
GREETING
THANKS
CONFIRMATION
DENIAL
CORRECTION
REPEAT
HELP
RESET_CONVERSATION
OUT_OF_SCOPE
AMBIGUOUS_QUERY

Use the existing canonical intent registry and reconcile differences instead of duplicating labels.

---

# 3. TRAINING DATA QUALITY

Include natural Indian English passenger queries.

Examples:

"When is the next bus for Nellore?"
"At what time is the Vizag last bus?"
"Any Super Luxury going Tirupati now?"
"Is there an AC bus available tonight?"
"Does that bus go via Ongole?"
"How much ticket to Guntur?"
"Can I get two seats tomorrow morning?"
"Is the bus already gone?"
"Which platform should I stand at?"
"Can I change at Rajahmundry?"

Include:
- Short questions
- Incomplete sentences
- Common grammar variations
- Regional English expressions
- Misspellings
- ASR errors
- Multiple intents
- Negation
- Contradictory instructions
- Ambiguous phrases
- Unknown entities
- Noisy transcriptions
- Follow-up utterances

Do not overpopulate training data with near-identical templated examples.

Split data at template/paraphrase-family level to avoid train/test leakage.

Maintain separate:
- Training set
- Validation set
- Independent test set
- Challenge set

Never train on the final independent test set.

---

# 4. BASELINE MODEL — TF-IDF + LINEAR SVM

Build a robust baseline using:

- Scikit-learn
- Word n-gram TF-IDF
- Character n-gram TF-IDF
- Linear SVM

Evaluate calibrated probability estimates or decision scores.

Do not present raw SVM margins as probabilities.

Train on the available validated corpus.

Save:
- Vectorizer
- Classifier
- Label mapping
- Preprocessing version
- Metrics
- Dataset version

Benchmark inference speed and memory usage.

---

# 5. TENSORFLOW MODEL — TEXTCNN

Train a lightweight English intent model using:

- TensorFlow/Keras
- Text vectorization
- Embedding layer
- 1D convolution
- Global max pooling
- Dense classification head
- Dropout
- Softmax

Include:
- Class balancing where appropriate
- Early stopping
- Validation monitoring
- Learning-rate scheduling
- Reproducible random seeds
- Checkpoint saving
- Training history
- Confusion matrix
- Macro-F1
- Per-intent metrics

Experiment with vocabulary size, sequence length, embedding size and convolution filters.

Avoid excessive model complexity.

Use the available local hardware efficiently.

---

# 6. MODEL COMPARISON AND SELECTION

Compare the SVM and TensorFlow models on identical evaluation sets.

Measure:
- Intent accuracy
- Macro precision
- Macro recall
- Macro-F1
- Per-intent F1
- Out-of-scope detection
- Error patterns
- Inference latency
- Model size
- Memory consumption

Include performance on:
- Clean English
- Indian English
- Short queries
- Noisy ASR transcripts
- Follow-up utterances
- Multi-intent requests

A single-label classifier may not be sufficient for multi-intent questions.

Implement an appropriate multi-label classifier or a compositional intent parser when needed.

Do not force multiple intents into one arbitrary label.

Choose the production model using measured results.

Do not automatically select TensorFlow because it is a neural network.

---

# 7. ENTITY EXTRACTION

Strengthen the existing RTCEntityExtractor.

Recognize:
- Origin
- Destination
- Boarding point
- Alighting point
- Via location
- Transfer point
- Service number
- Bus category
- Vehicle characteristics
- AC/non-AC
- Sleeper/seater
- Travel date
- Date range
- Departure time
- Arrival time
- Time window
- Passenger count
- Fare limit
- Accessibility requirements
- Concession category

Use database-backed aliases as the primary source for station and bus-type names.

For dates and times, use a deterministic parser with explicit timezone handling.

Use an NER model only if benchmark evidence demonstrates that it improves extraction accuracy.

Never let a statistical entity prediction silently override exact validated station identification.

---

# 8. NEGATION AND CONSTRAINT UNDERSTANDING

Handle expressions such as:

"No AC buses."
"Only non-AC."
"Not a sleeper."
"Anything except Express."
"Under 500 rupees."
"After 7 PM, not before."
"No, I said Tirumala, not Tirupati."

Create structured constraints with explicit operators.

For example:

{
  "exclude_categories": ["EXPRESS"],
  "ac": false,
  "max_fare": 500,
  "departure_after": "19:00"
}

Do not treat negated terms as positive filters.

Validate contradictory combinations.

---

# 9. MULTI-TURN CONVERSATION TRAINING

Create at least 500 varied conversation scenarios.

Examples:

Conversation A:
1. "Next bus to Nellore?"
2. "Is it AC?"
3. "How much?"
4. "What about tomorrow?"
5. "Only sleeper."
6. "Actually, Tirupati."

Conversation B:
1. "I need to go to Vizag."
2. "Which is the cheapest?"
3. "Does it stop at Rajahmundry?"
4. "What time will I arrive?"
5. "What if I miss it?"

Conversation C:
1. "Two seats for Hyderabad."
2. "Tonight."
3. "Not AC."
4. "Any earlier bus?"
5. "Which platform?"

Validate:
- Context preservation
- Slot replacement
- Intent switching
- Correct use of previous selected services
- Confirmation and rejection
- Clarification states
- Session reset
- Expiration
- Concurrent sessions

Implement a deterministic dialogue manager with an explicit state model.

Do not substitute memorized conversation scripts.

---

# 10. CONFIDENCE AND UNCERTAINTY

Introduce confidence-aware classification.

When confidence is insufficient:
- Ask for clarification.
- Present limited candidate interpretations.
- Fall back to deterministic matching.
- Avoid executing an unrelated bus enquiry.

Calibrate thresholds on validation data.

Measure:
- False confident predictions
- Incorrect entity matches
- Out-of-scope false positives
- Clarification frequency
- Correct clarification outcomes

Do not invent fixed confidence percentages.

---

# 11. DATABASE INTEGRATION

Connect the trained classifier to the existing RTCEnquiryEngine.

Pipeline:

Passenger text
→ Normalization
→ Intent classification
→ Entity extraction
→ Dialogue context
→ Validated structured enquiry
→ Database query
→ Verified response template

The model must never:
- Generate SQL directly
- Invent service IDs
- Invent timetable data
- Invent fares
- Make external network requests

All operational answers must originate from the database.

If only DEMO records are available, label results clearly as DEMO.

---

# 12. ENGLISH SPEECH ROBUSTNESS

Preserve and improve the Phase 1 English ASR adapter.

Use Vosk-generated transcripts for evaluation where available.

Build a transcription correction layer for:
- Common destination names
- Bus service categories
- Indian English pronunciations
- Route numbers
- Time expressions

Examples:
- Vizag / Visag
- Tirupati / Tirupathi
- Super Luxury / super luxery
- Nellore / Nelore

Do not over-correct valid unknown place names.

Use speech recognition alternatives where available, but do not invent them.

Do not train ASR from scratch in this phase.

---

# 13. MODEL REGISTRY AND VERSIONING

Register every trained model.

Track:
- Model ID
- Model architecture
- Training date
- Dataset version
- Dataset checksum
- Label-map version
- Preprocessing version
- Hyperparameters
- Validation metrics
- Test metrics
- Serialized model path
- Runtime dependencies
- Offline readiness
- Deployment status

Implement model promotion:
- Candidate
- Evaluated
- Approved
- Active
- Rolled back

Keep the previous working model available for rollback.

Do not automatically promote a new model unless its evaluation meets documented criteria.

---

# 14. EVALUATION AND REGRESSION SUITE

Create automated evaluation pipelines.

Required reports:
- Intent classification report
- Confusion matrix
- Entity extraction report
- Dialogue correctness report
- End-to-end enquiry correctness report
- Performance benchmark
- Model comparison report

Include at least 100 adversarial or difficult cases:
- Similar destination names
- Negated bus categories
- Impossible dates
- Missing destination
- Contradictory filters
- Multiple intent questions
- Out-of-scope speech
- Date corrections
- Selected-trip ambiguity
- Stale data
- Unknown fare
- Misrecognized numbers

All reports must distinguish:
- Training performance
- Validation performance
- Independent test performance

---

# 15. PERFORMANCE TARGETS

Targets, not guaranteed results:

- Intent macro-F1: >= 0.95
- Entity extraction F1: >= 0.97
- Dialogue state correctness: >= 0.95
- End-to-end answer accuracy: >= 0.95
- Median NLP inference latency: < 100 ms on target CPU, excluding database lookup and audio

Measure actual performance.

If any target is missed, provide an error analysis and implement improvements.

Do not fabricate results to satisfy acceptance criteria.

---

# 16. OFFLINE DEPLOYMENT

Ensure:
- Model training uses local datasets.
- Inference does not use network access.
- Models load from local paths.
- No runtime downloads.
- No cloud API dependency.
- Configuration supports Windows/Linux.
- Models and preprocessing assets are versioned.

Test offline inference with operating-system-level network isolation.

Preserve the multilingual foundation for future Telugu/Tanglish support.

---

# 17. DELIVERABLES

Produce:

1. Validated English RTC enquiry dataset.
2. SVM baseline classifier.
3. Trained TensorFlow TextCNN classifier.
4. Model comparison report.
5. Selected English production model.
6. Enhanced entity extractor.
7. Negation and constraints parser.
8. Multi-intent recognition.
9. Improved dialogue manager.
10. Confidence-aware clarification logic.
11. End-to-end NLP/database integration.
12. Automated test suite.
13. Offline verification.
14. Performance benchmarks.
15. Model registry updates.
16. Training and evaluation documentation.

Run actual training and testing.

Provide exact dataset counts, test counts and achieved metrics.

If a required component remains incomplete, report:

PHASE 2 INCOMPLETE

Do not claim production readiness based on synthetic training accuracy alone.

Do not start Phase 3 speech orchestration or Phase 4 UI.

Begin implementation immediately, using the existing repository rather than starting a new project.