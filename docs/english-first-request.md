# RTC OFFLINE AI — ENGLISH-FIRST IMPLEMENTATION
## Complete English NLP, Voice Recognition and Conversational Enquiry Engine

Continue in the EXISTING RTC Offline AI repository.

IMPORTANT CHANGE OF SCOPE:

We are temporarily postponing Telugu, Tanglish, MuRIL and IndicConformer integration.

Our immediate objective is a fully working, completely offline ENGLISH conversational bus enquiry system.

Do not delete previous multilingual code, aliases, partial model downloads, datasets or configuration. Preserve them for later phases.

Do not create a passenger UI. UI development remains Phase 4.

## 1. TECHNOLOGY

Backend:
- Python FastAPI
- PostgreSQL / SQLite
- Existing RTCEnquiryEngine
- Existing conversation manager

NLP:
- TensorFlow/Keras for custom English intent classification
- Scikit-learn TF-IDF + linear SVM baseline
- RapidFuzz for station and service alias matching
- Deterministic entity extraction and temporal parsing

Speech recognition:
- Vosk English, fully offline

Speech synthesis:
- Local English TTS, preferably Piper with a compatible licensed voice
- No cloud speech services

Use isolated environments where dependencies conflict.

## 2. MODEL DOWNLOAD AND VERIFICATION

Download an official English Vosk model.

Start with:
vosk-model-small-en-us-0.15

Also benchmark:
vosk-model-en-us-0.22-lgraph

Official models:
https://alphacephei.com/vosk/models

Check available hardware, disk space and RAM before downloading.

Verify:
- Complete download
- Expected extracted model files
- Model initialization
- Real English audio transcription
- Offline inference
- Word error rate on labelled samples
- Real-time factor
- Memory consumption

Do not report audio accuracy without real recordings and reference transcripts.

Do not download additional large models unnecessarily.

## 3. CUSTOM ENGLISH NLP MODEL

Build a training pipeline using TensorFlow/Keras.

Prepare English training examples covering all existing 40+ RTC enquiry intents.

Examples:

"When is the next bus to Tirupati?"
"What is the ticket fare to Nellore?"
"What is the last bus to Visakhapatnam?"
"Are there any AC sleeper buses tonight?"
"Is there a direct bus to Tirumala?"
"Does this bus stop at Ongole?"
"Are two seats available?"
"Which is the cheapest bus tomorrow?"
"Is the 9 PM bus cancelled?"
"What platform does the bus depart from?"

Train and evaluate:
A. TF-IDF + linear SVM baseline.
B. TensorFlow Embedding + TextCNN.
C. Optional BiLSTM if supported by results.

Use the same train/validation/test partitions.

Prevent leakage from generated paraphrases and repeated question templates.

Report precision, recall, macro-F1, confusion matrix and inference latency.

Do not assume TensorFlow performs better merely because it uses a neural network.

Select the model using actual evaluation results and deployment requirements.

## 4. ENTITY RECOGNITION

Implement robust extraction for:

- Origin
- Destination
- Station
- Bus category
- AC/non-AC
- Sleeper/seater
- First/next/last
- Date
- Relative date
- Time
- Morning/evening/night
- Passenger count
- Fare constraints
- Service number
- Platform
- Intermediate stops
- Concessions
- Accessibility requirements

Resolve locations and categories against existing database masters.

Never hardcode a small fixed list of destinations into the model.

For unknown station aliases, use safe disambiguation.

## 5. REALTIME CONVERSATION

Implement a session-based dialogue manager supporting:

- Follow-up questions
- Context retention
- Corrections
- Multiple intents
- Clarification requests
- Context expiration
- New conversation detection
- Selected bus references
- Changing date, time, destination or category

Example:

User: "When is the next bus to Nellore?"

System: Answers from the database.

User: "Is there an AC bus?"

System: Retains destination and filters by AC.

User: "What is the fare?"

System: Uses the currently selected service or asks which service if ambiguous.

User: "What about tomorrow morning?"

System: Updates the travel date and time window.

User: "No, I meant Tirupati."

System: Replaces the destination and invalidates previous service selection.

Do not rely on hardcoded conversational scripts.

Use structured context, dialogue acts and database queries.

## 6. SPEECH PIPELINE

Implement:

Microphone
→ Voice activity detection
→ Vosk English ASR
→ NLP classifier
→ Entity extraction
→ Conversation manager
→ RTC enquiry engine
→ Response formatter
→ Offline TTS

Support:
- Continuous listening
- Optional push-to-talk
- Partial transcripts
- End-of-utterance detection
- Silence timeout
- Interruption while speaking
- Audio output cancellation
- No repeated trigger from the assistant's own speaker audio
- Session reset after inactivity

Use echo mitigation or half-duplex fallback if reliable barge-in cannot be achieved on the available hardware.

Real-time performance must be measured rather than assumed.

## 7. ENGLISH RESPONSE GENERATION

Create accurate natural English response templates.

Examples:

"The next Super Luxury bus to Nellore is scheduled to depart at 6:30 PM."

"The fare is 450 rupees."

"The platform has not yet been confirmed."

"There are no matching scheduled services for your selected time."

All operational details must be taken from the database.

Never invent fares, departures or availability.

Label demo schedules as demonstration data.

## 8. APIs AND TERMINAL DEMONSTRATION

Implement or reuse:

POST /api/v1/nlp/interpret
POST /api/v1/conversation/message
POST /api/v1/conversation/reset
GET /api/v1/models/status

Implement a working terminal voice assistant using the microphone and speaker.

This is not a graphical passenger UI.

Support:
- Typed conversation
- Spoken conversation
- Conversation transcripts
- Debug information
- Offline runtime

## 9. MODEL REGISTRY

Track:
- English Vosk checkpoint
- NLP SVM model
- TensorFlow classifier
- English TTS model
- MuRIL status: DEFERRED
- Telugu IndicConformer status: DEFERRED

Preserve existing partial Telugu-model downloads.

Do not mark postponed components as failed English requirements.

## 10. TRAINING DATASET

Prepare an initial English dataset with:
- At least 40 RTC intents
- A target of 200 varied examples per intent
- Negative and ambiguous examples
- Multi-intent examples
- Follow-up conversations
- Realistic Indian English phrasing
- Common transcription errors
- Station and service-category variations

Create reproducible training, validation and test splits.

Ensure the dataset's quality before training.

Do not report that 8,000 examples are ready unless 8,000 actual validated examples exist.

## 11. TESTING

Test:
- All 40+ enquiry intents
- English station names
- Indian English expressions
- First and last bus queries
- Fare and bus category questions
- Multi-turn memory
- Destination corrections
- Relative dates
- Ambiguous stations
- Unavailable data
- Offline model loading
- Live microphone input
- TTS audio playback
- Session isolation
- Local database queries

Benchmark:
- Intent classification macro-F1
- Entity extraction F1
- Complete enquiry correctness
- ASR word error rate
- Speech processing real-time factor
- End-to-end response latency
- CPU and memory consumption

Set provisional acceptance targets:
- Intent macro-F1 >= 0.95 on independent evaluation data
- End-to-end answer accuracy >= 0.95 on a reviewed test set
- Acceptable conversational latency on actual kiosk hardware

Treat targets as goals, not achieved results.

## 12. OFFLINE REQUIREMENTS

No runtime network connections.

Download dependencies and model files during setup only.

Verify inference with outbound network access disabled.

Ensure:
- Database works offline
- NLP model works offline
- Speech recognition works offline
- TTS works offline
- Conversation manager works offline

Do not use GPT, cloud AI, online speech services or CDN resources.

## 13. PROTECT PREVIOUS WORK

Preserve:
- Current database and migrations
- Existing enquiry engine
- Telugu/Tanglish aliases
- MuRIL checkpoint partial downloads
- IndicConformer checkpoint partial downloads
- Model registry
- Existing tests
- Existing API contracts

Avoid unnecessary refactoring.

## 14. FINAL DELIVERABLES

1. Working offline English NLP model.
2. English intent classification evaluation.
3. Offline English Vosk ASR.
4. Offline English TTS.
5. Working dialogue manager.
6. Database-integrated conversational enquiry engine.
7. Terminal-based voice demonstration.
8. Model installation verification.
9. Automated tests.
10. Offline smoke test.
11. Actual latency and memory benchmarks.
12. Updated documentation.

If an acceptance requirement remains unverified, report it explicitly.

Do not claim the project is complete based only on downloaded files, passing tokenization tests or generated scripts.

Start implementing immediately.

Prioritize completion of the working English conversational engine over additional architecture documentation.