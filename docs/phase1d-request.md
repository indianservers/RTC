# RTC OFFLINE AI — PHASE 1D
## Offline NLP Integration, Entity Recognition & Conversational Engine

You are a senior NLP engineer, machine-learning architect, Python backend engineer and conversational AI specialist.

Continue development in the EXISTING RTC Offline AI repository.

Previous phases:
- 1A: Database architecture and schema.
- 1B: Bus enquiry and route intelligence engine.
- 1C: Offline model download, registry and validation.

Your task is to integrate the existing modules into a working offline conversational enquiry engine.

IMPORTANT:
Do not assume previous phases are complete merely because files or README entries exist. Inspect the actual repository and preserve working functionality.

Do not recreate existing implementations or duplicate APIs, tables, models or services.

## 1. STRICT PROJECT REQUIREMENTS

The entire application must work offline.

Prohibited:
- GPT, OpenAI, Gemini, Claude
- Cloud inference APIs
- External speech services
- Runtime model downloading
- External database calls
- Hardcoded bus timings and fares
- Arbitrary LLM-generated SQL
- Passenger UI development

Required:
- Python FastAPI
- PostgreSQL and SQLite
- Local MuRIL model adapter
- Deterministic NLP fallback
- Database-driven entity resolution
- Multi-turn conversation manager
- Telugu, English and Tanglish
- Typed request/response models
- Local automated tests

No frontend implementation until Phase 4.

Actual speech recognition and audio playback orchestration belong to Phase 3. Build interfaces only where necessary.

---

# 2. CENTRAL NLP PIPELINE

Implement:

`RTCNLPEngine`

Input:

```json
{
  "session_id": null,
  "text": "Vijayawada nunchi Nellore ki next AC bus eppudu?",
  "language": "auto",
  "station_context": "VIJAYAWADA_PNBS"
}
```

Expected structured interpretation:

```json
{
  "intent": "NEXT_BUS",
  "origin": "Vijayawada",
  "destination": "Nellore",
  "bus_features": {
    "ac": true
  },
  "time_reference": "NEXT_AVAILABLE",
  "confidence": 0.94,
  "requires_clarification": false
}
```

This is an illustrative target contract; confidence is not a measured model result.

The engine must execute a structured query using the existing RTCEnquiryEngine and return a verified database-derived response.

Use the pipeline:

1. Input validation
2. Unicode and text normalization
3. Language/script detection
4. Tokenization
5. Intent classification
6. Entity extraction
7. Entity canonicalization
8. Context merging
9. Ambiguity detection
10. Enquiry tool selection
11. Database execution
12. Response template rendering
13. Session update
14. Structured result output

Implement each component separately with clear interfaces.

---

# 3. LANGUAGE NORMALIZATION

Build:

`LanguageNormalizer`

Support:
- Telugu script
- English
- Tanglish
- Mixed Telugu-English
- Romanized Telugu
- Informal spelling
- Common abbreviations
- Speech recognition transcription errors

Examples:

"నెల్లూరుకు బస్సు ఎప్పుడు?"
"Nellore ki bus eppudu?"
"nellur ki next bus"
"Nellore bus timing"
"నెల్లూరు next bus?"

All should map to the appropriate canonical meaning when supported by the training lexicon and rules.

Implement:
- Unicode normalization
- Whitespace cleanup
- Case folding for Latin text
- Telugu punctuation handling
- Abbreviation expansion
- Common phonetic variations
- Configurable transliteration mappings
- Preservation of important numeric tokens
- Correct handling of AM/PM and clock expressions

Preserve the original user text.

Do not blindly remove suffixes or translate words without context.

Do not force every query into a single language.

Store normalization rules and aliases in configurable resources or existing NLP database tables.

---

# 4. INTENT RECOGNITION ENGINE

Implement:

`IntentClassifier`

Provide two interchangeable strategies.

## Strategy A: Deterministic baseline

Use:
- Keyword matching
- Phrase templates
- Token patterns
- Weighted rules
- RapidFuzz where appropriate
- Context-aware disambiguation

Support at least 40 enquiry intents.

Examples:

NEXT_BUS
FIRST_BUS
LAST_BUS
GET_FARE
GET_BUS_TYPES
GET_PLATFORM
GET_ROUTE
GET_STOPS
GET_ARRIVAL
GET_DURATION
GET_DELAY
GET_CANCELLATION
GET_SEAT_AVAILABILITY
GET_CHEAPEST_SERVICE
GET_FASTEST_SERVICE
GET_CONNECTING_BUSES
GET_CONCESSIONS
GET_FACILITIES
GET_BOOKING_OPTIONS
GET_LUGGAGE_RULES
GET_SERVICE_DETAILS

Use the existing intent registry instead of introducing conflicting intent names.

Handle greetings, thanks, help requests, confirmations and corrections as dialogue acts rather than forcing them into bus enquiry intents.

## Strategy B: MuRIL adapter

Create:

`MuRILIntentClassifier`

Load model and tokenizer exclusively from the local model registry.

Support:
- Base model loading
- Classification-head loading when available
- Tokenizer consistency checking
- Model label mapping
- Local-only inference
- CPU execution
- Optional GPU execution
- Configurable inference timeout
- Model version tracking

CRITICAL:

The downloaded pretrained MuRIL base model is NOT automatically a trained RTC intent classifier.

Do not pretend that its masked-language-model output is an intent prediction.

If fine-tuned weights are unavailable:
- Mark the MuRIL classifier as NOT_READY.
- Keep deterministic baseline active.
- Expose correct readiness information.
- Do not generate random intent predictions.

Prepare an adapter that can accept Phase 2 fine-tuned weights without changing the dialogue engine.

---

# 5. ENTITY EXTRACTION ENGINE

Implement:

`RTCEntityExtractor`

Extract:

## Location
- Origin city
- Destination city
- Origin bus station
- Destination bus station
- Intermediate stop
- Transfer station

## Bus classification
- Bus category
- AC / non-AC
- Sleeper / seater
- Electric bus
- Reserved / non-reserved
- Accessibility requirements

## Date and time
- Today
- Tomorrow
- Day after tomorrow
- Specific calendar dates
- Morning / afternoon / evening / night
- After a specified time
- Before a specified time
- First / next / last
- Relative time expressions

## Passenger and price
- Number of passengers
- Number of seats
- Maximum fare
- Cheapest option
- Fastest option
- Senior citizen concession enquiry
- Other explicitly mentioned concession categories

## Service identification
- Service number
- Route number
- Vehicle number where applicable
- Platform number

Support mixed Telugu and English expressions.

Examples:

"repu podduna"
"రేపు ఉదయం"
"tomorrow morning"

All should resolve to the same semantic date/time concept using station-local time.

Do not resolve relative dates using UTC or the developer machine timezone.

Inject the current time into the parser so date tests are deterministic.

---

# 6. ENTITY CANONICALIZATION

Implement:

`RTCEntityResolver`

Query the existing database's stations, cities, aliases, bus categories and service information.

Examples:
- Vizag → Visakhapatnam
- Bezawada → Vijayawada
- Tirupathi → Tirupati
- Rajahmundry → Rajamahendravaram
- SL bus → Super Luxury, only where operator aliases establish this meaning

Preserve the distinction:
- Tirupati
- Tirumala

Support city-wide searches across multiple stations.

When multiple station matches are plausible, return explicit candidates and ask the passenger to clarify.

Use a confidence or match-score system, but calibrate thresholds through testing rather than inventing probability claims.

Avoid aggressive fuzzy matching that might select an entirely different destination.

---

# 7. MULTI-INTENT QUESTION HANDLING

The passenger may ask several things at once.

Examples:

"Next bus to Nellore and ticket fare?"

"Vizag last bus eppudu? AC sleeper unda?"

"Tomorrow Tirupati bus timing and platform?"

Implement:
- Primary intent
- Secondary intents
- Shared entities
- Execution ordering
- Aggregated response
- Partial-results handling

For instance:

NEXT_BUS + GET_FARE + GET_PLATFORM

Resolve the service once when possible and reuse its identifier for the remaining enquiries.

Avoid redundant database requests.

If one data field is unavailable, still provide the other verified results.

---

# 8. CONVERSATION MEMORY

Implement:

`ConversationManager`

Use a state machine with dialogue acts and slot filling.

Track:
- Session ID
- Current origin
- Current destination
- Travel date
- Time window
- Preferred operator
- Bus category
- AC preference
- Sleeper preference
- Passenger count
- Selected service
- Last intent
- Pending clarification
- Last result references
- Language preference
- Session expiry

Example conversation:

Passenger:
"Nellore ki next bus eppudu?"

System:
Responds using database.

Passenger:
"AC unda?"

System:
Queries AC services to the same destination.

Passenger:
"Super Luxury?"

System:
Applies Super Luxury category to the same journey.

Passenger:
"Repu morning?"

System:
Changes the date/time and searches again.

Passenger:
"No, Tirupati."

System:
Replaces the destination with Tirupati and preserves appropriate previous filters.

Implement rules for:
- Filling missing information
- Replacing earlier selections
- Clearing conflicting selections
- Confirming ambiguous information
- Switching destinations
- Switching intent
- Repeating the previous result
- Starting a new enquiry
- Session expiration

Do not retain stale trip selections when changing the route or date.

Do not share conversation context between unrelated kiosk users.

---

# 9. DIALOGUE MANAGEMENT

Implement:

`RTCDialogueManager`

Dialogue states:

IDLE
UNDERSTANDING
AWAITING_ORIGIN
AWAITING_DESTINATION
AWAITING_DATE
AWAITING_STATION_CLARIFICATION
AWAITING_SERVICE_SELECTION
EXECUTING_QUERY
ANSWERING
NO_RESULTS
ERROR
SESSION_COMPLETE

The system must ask the smallest useful clarification question.

Examples:

Passenger:
"Next bus?"

Response:
"Where would you like to travel?"

If the kiosk has a trusted default station, do not ask for the origin unnecessarily.

Passenger:
"Vijayawada bus."

If multiple boarding stations are relevant, resolve using context or ask which station.

Passenger:
"AC sleeper to Tirupati."

If the date is absent, apply the documented next-available policy, not an arbitrary date.

Never use a generic apology when a precise clarification is possible.

---

# 10. DATABASE QUERY ORCHESTRATION

Create:

`RTCQueryOrchestrator`

Connect NLP output to the existing RTCEnquiryEngine.

Examples:

NEXT_BUS → get_next_buses()
GET_FARE → get_bus_fare()
LAST_BUS → get_last_bus()
GET_ROUTE → get_route_stops()
GET_PLATFORM → get_platform_assignment()
GET_CONNECTING_BUSES → get_connecting_services()

Do not duplicate SQL query logic inside the NLP package.

Use typed tool parameters.

Validate all extracted data before query execution.

The NLP model must never directly construct executable SQL.

If required data is missing, request clarification.

Handle:
- No matching services
- Unsupported enquiry
- Unknown station
- Incomplete fare data
- Missing platform
- Stale operational information
- Database failure
- Ambiguous trip selection

---

# 11. NATURAL RESPONSE GENERATION

Implement:

`RTCResponseEngine`

Use deterministic response templates.

Support:
- Telugu
- English
- Mixed language where explicitly configured

Response categories:
- Success
- No results
- Missing information
- Clarification
- Data stale
- Unsupported enquiry
- Service cancelled
- Multiple bus options
- Connection available

Example:

English:
"The next Super Luxury bus to Nellore is scheduled at {time}. The fare is {fare}."

Telugu:
"నెల్లూరుకు వెళ్లే తదుపరి సూపర్ లగ్జరీ బస్సు {time} కు బయలుదేరుతుంది. టికెట్ ధర {fare}."

Only include fields that have verified values.

If the platform is unknown, state that the platform is not confirmed.

Do not fabricate natural-sounding operational explanations.

Support Telugu rendering of:
- Times
- Dates
- Rupee amounts
- Bus numbers
- Passenger counts

Keep spoken responses short and understandable.

Prepare text output that can be passed to an offline TTS engine in Phase 3.

---

# 12. NLP API

Create or extend:

POST /api/v1/nlp/interpret
POST /api/v1/conversation/message
POST /api/v1/conversation/reset
GET /api/v1/nlp/status
GET /api/v1/models/status

Example conversation request:

{
  "session_id": "optional-session-id",
  "text": "Nellore ki next AC bus eppudu?",
  "language": "auto",
  "station_context": "VIJAYAWADA_PNBS"
}

Return:
- Session ID
- Detected language
- Detected intents
- Extracted entities
- Canonical entities
- Applied context
- Clarification requirements
- Query result references
- Answer text
- Data freshness indicators
- Warnings
- Processing duration

Do not expose sensitive debugging details to ordinary passenger-facing clients.

---

# 13. NLP DATASET FOUNDATION

Prepare structured files or database seeds for:

- 40+ enquiry intents
- Telugu examples
- English examples
- Tanglish examples
- Mixed-language examples
- Station aliases
- Bus-category synonyms
- Dialogue acts
- Multi-turn conversation tests

Include at least 20–30 carefully reviewed examples per intent as an initial baseline corpus.

Label synthetic examples clearly.

Create a data validation script to detect:
- Duplicate utterances
- Contradictory labels
- Missing intents
- Invalid entity spans
- Unsupported languages
- Train/test leakage

Do not claim that this initial corpus is sufficient for production model training.

Phase 2 will expand, annotate and evaluate the dataset.

---

# 14. OFFLINE MODEL MANAGEMENT

Reuse the local registry created in Phase 1C.

Implement:
- Lazy model loading
- Cached local model instances
- Readiness checks
- Explicit model version reporting
- Local path validation
- Checksum verification
- Controlled inference errors
- Safe fallback to deterministic NLP

Enforce offline loading through local model paths and offline runtime configuration.

Do not download missing model files automatically.

If models are missing, the deterministic baseline must continue working.

Avoid loading IndicConformer just to handle text enquiries.

---

# 15. TESTING — CRITICAL

Create automated tests for:

1. Telugu script input
2. English input
3. Tanglish input
4. Mixed Telugu-English input
5. Station alias recognition
6. Bus-type alias recognition
7. Tirupati/Tirumala distinction
8. Date normalization
9. Tomorrow-morning interpretation
10. Midnight boundaries
11. Multi-intent recognition
12. Missing destination clarification
13. Ambiguous station clarification
14. Unknown bus category
15. Unknown fare
16. No matching trips
17. Follow-up AC filter
18. Follow-up bus type
19. Destination correction
20. Date correction
21. Origin correction
22. Context expiration
23. Concurrent independent sessions
24. Unsupported passenger input
25. No-model fallback
26. Corrupted local model
27. Database failure
28. Telugu response rendering
29. English response rendering
30. Complete NLP-to-database enquiry

Create at least 100 deterministic NLP test cases and 30 multi-turn dialogue scenarios.

Evaluate clean text separately from speech-transcription errors.

Measure:
- Intent classification accuracy
- Entity extraction precision/recall
- Canonical station resolution accuracy
- Clarification correctness
- Context retention accuracy
- End-to-end answer correctness
- P50/P95 response latency

Never claim an accuracy percentage without executing the tests.

---

# 16. PERFORMANCE AND RELIABILITY

Requirements:
- Keep database query logic outside NLP modules.
- Cache normalized aliases and model instances where useful.
- Bound fuzzy-search candidate counts.
- Avoid unbounded conversation histories.
- Support multiple simultaneous kiosk sessions.
- Prevent one session from changing another session's context.
- Do not log raw audio.
- Make message processing resilient to partial failures.

Benchmark the deterministic baseline separately from MuRIL inference.

Report actual hardware and dataset conditions.

---

# 17. IMPLEMENTATION STRUCTURE

Use the existing repository and adapt to its architecture.

Suggested additions:

backend/app/nlp/
  normalizer.py
  language_detector.py
  intent_classifier.py
  entity_extractor.py
  entity_resolver.py
  temporal_parser.py
  dialogue_manager.py
  conversation_manager.py
  query_orchestrator.py
  response_engine.py
  model_adapters/
    muril.py
    deterministic.py

backend/app/api/
  nlp.py
  conversation.py
  model_status.py

backend/tests/nlp/
backend/tests/conversation/

training/datasets/
training/evaluation/

Do not duplicate existing modules under different names.

---

# 18. COMPLETION CRITERIA

Phase 1D is complete only when:

1. Telugu, English and Tanglish questions are processed.
2. Deterministic intent classification works.
3. Bus entities resolve against database masters.
4. Context-aware follow-up enquiries work.
5. Multi-intent questions work.
6. Existing RTC enquiry functions are reused.
7. Response templates use only database information.
8. MuRIL adapter reports genuine readiness.
9. Missing models do not break the application.
10. NLP APIs return consistent typed results.
11. Automated tests pass.
12. Offline operation is verified.
13. No frontend or UI is implemented.

Do not confuse successful tokenization with an accurate NLP model.

Do not hardcode fictional answers merely to make demonstration conversations pass.

---

# 19. FINAL DELIVERABLES

Provide:
1. Complete working NLP pipeline
2. Deterministic intent classifier
3. MuRIL model adapter
4. Entity extraction and resolution
5. Temporal expression parser
6. Conversation state manager
7. Query orchestration layer
8. Telugu/English response renderer
9. NLP REST endpoints
10. Baseline training dataset
11. Automated evaluation tests
12. Offline verification report
13. Architecture documentation
14. Phase 2 readiness report

Run the application, execute tests and fix failures.

Report actual test counts and failures.

If substantial features remain incomplete, clearly mark PHASE 1D INCOMPLETE.

Do not begin Phase 2 training or Phase 3 audio integration.

Begin implementation in the existing repository immediately.