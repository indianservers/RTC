# RTC OFFLINE AI — PHASE 2B
## Generate 12,000+ High-Quality English NLP Training Examples

You are a senior NLP dataset engineer, computational linguist, conversational AI researcher, transport-domain expert and Python developer.

Continue work in the EXISTING RTC Offline AI repository.

Previous phase:
Phase 2A — 60 canonical RTC enquiry intents, entity definitions, dialogue acts and ambiguity rules.

Your task is to build a large, diverse, reproducible and accurately labelled English-language training dataset for RTC bus stand enquiries.

DO NOT start model training.

DO NOT build the passenger UI.

DO NOT introduce GPT, OpenAI, Gemini, Claude or external generative AI services.

All dataset generation and validation must run locally.

Do not modify working RTC enquiry APIs or core database logic unnecessarily.

---

# 1. INSPECT THE EXISTING DATASET FOUNDATION

Before generating anything, inspect:

- Existing intent registry
- All 60 canonical intents
- Existing NLP utterances
- Existing station aliases
- Bus service categories
- Training datasets
- Existing annotation formats
- Dataset validation scripts
- Existing data splits
- Existing dialogue acts

Preserve previously created validated examples.

Avoid duplicates.

Reuse the canonical intent definitions from Phase 2A.

Do not silently rename intent codes.

Create a coverage report showing which intents already have examples and which require new data.

---

# 2. DATASET QUANTITY

Produce at least 200 unique candidate examples for each of the 60 canonical RTC enquiry intents.

Minimum:

60 intents × 200 = 12,000 labelled enquiry candidates.

Additional datasets:

- 1,000 multi-intent enquiries
- 1,000 context-dependent follow-up utterances
- 500 out-of-scope enquiries
- 500 ambiguity and clarification examples
- 500 correction and negation examples
- 500 challenging ASR-style text examples

Target a minimum of 16,000 records overall, with separate labels for each dataset category.

Do not count identical or near-duplicate utterances toward the required 200 unique examples per intent.

Do not claim generated examples are human-reviewed.

All automatically generated examples must carry source_type = SYNTHETIC.

---

# 3. EXAMPLE DISTRIBUTION PER INTENT

Target the following distribution:

- 40 natural English questions
- 35 Indian conversational English questions
- 25 short or incomplete questions
- 30 alternative grammar structures
- 20 long or detailed questions
- 20 misspelling or noisy ASR-like questions
- 20 contextual follow-up questions
- 10 challenging, negated or ambiguous examples

Total: 200.

Every example must preserve the intended meaning.

For inherently ambiguous examples, use explicit AMBIGUOUS or CLARIFICATION_REQUIRED labels rather than inventing one correct intent.

Context-dependent follow-up examples must include their preceding conversation state.

---

# 4. USE REAL RTC VOCABULARY

Reuse place names and aliases from the database.

Include destinations such as:

Vijayawada
Guntur
Nellore
Tirupati
Tirumala
Ongole
Kavali
Visakhapatnam
Vizag
Rajahmundry
Rajamahendravaram
Kakinada
Eluru
Kurnool
Kadapa
Anantapur
Srikakulam
Vizianagaram
Srisailam
Annavaram
Hyderabad
Machilipatnam
Bhimavaram

Include all available bus service categories from the database:

Pallevelugu
Express
Ultra Deluxe
Super Luxury
Indra
Amaravathi
Dolphin Cruise
Vennela
Vennela Economy
Saptagiri
Metro Express
Metro Luxury
and other categories already configured.

Do not fabricate categories as if they were official operating services.

Use database aliases and operator records rather than maintaining an unrelated hardcoded list.

The dataset must remain portable to Telangana and Tamil Nadu by changing the database vocabulary.

---

# 5. GENERATE DIFFERENT ENGLISH SPEAKING STYLES

Support the following language styles.

## Formal English

"When is the next scheduled departure to Tirupati?"

## Natural conversational English

"What's the next bus going to Tirupati?"

## Indian English

"Tirupati bus, what time it is coming?"

## Short enquiries

"Next Tirupati?"

## Incomplete speech

"Bus for Tirupati, evening."

## Urgent enquiries

"I missed the last bus. How can I reach Nellore now?"

## Polite requests

"Could you please tell me the next bus timing?"

## Detailed queries

"I am travelling with two family members tomorrow morning and need an AC bus to Hyderabad."

## ASR-like transcriptions

"next bus to tirupathi what time"

These examples must be diverse in meaning-preserving sentence structure, not merely in station names.

---

# 6. STRATEGIC COVERAGE FOR ALL 60 INTENTS

For each intent, implement a dedicated generation specification.

Include:

- Intent definition
- Positive examples
- Negative examples
- Confusable intents
- Required entities
- Optional entities
- Context requirements
- Query patterns
- Linguistic variations
- Common passenger situations
- Edge cases
- Valid response expectations

Particularly distinguish:

NEXT_BUS vs FIRST_BUS
LAST_BUS vs DEPARTURES_BEFORE
BUS_AT_TIME vs DEPARTURES_AFTER
ARRIVAL_TIME vs ESTIMATED_ARRIVAL
DIRECT_BUS vs CONNECTING_BUSES
BUS_VIA_LOCATION vs INTERMEDIATE_STOP
GET_FARE vs FARE_COMPARISON
CHEAPEST_BUS vs CONCESSION_ENQUIRY
BUS_DELAY vs LIVE_BUS_STATUS
BUS_PLATFORM vs PLATFORM_CHANGE
SEAT_AVAILABILITY vs BOOKING_STATUS

Create contrastive examples where similar wording leads to different labels.

---

# 7. MULTI-INTENT DATASET

Generate at least 1,000 valid multi-intent questions.

Examples:

"When is the next bus to Nellore and what is the fare?"

"Is the Hyderabad bus delayed and which platform is it on?"

"Show the cheapest AC sleeper to Vizag tomorrow."

"Does the Tirupati Express stop at Ongole and how long does the journey take?"

Represent multiple intents as arrays.

Example:

{
  "text": "Next bus to Nellore and how much is the fare?",
  "intents": ["NEXT_BUS", "GET_FARE"],
  "dataset_type": "MULTI_INTENT"
}

Distinguish an actual second intent from an entity modifier.

"Cheapest AC sleeper tomorrow" is primarily CHEAPEST_BUS with AC/sleeper/date constraints, not necessarily three separate enquiry intents.

---

# 8. CONTEXTUAL FOLLOW-UP DATASET

Generate at least 1,000 context-dependent passenger utterances.

Each record must contain:
- Prior conversation context
- Current passenger message
- Expected dialogue act
- Expected intent, if applicable
- Slot changes
- Expected context after processing

Example:

{
  "previous_context": {
    "destination": "Nellore",
    "bus_type": "Express"
  },
  "text": "What about Super Luxury?",
  "dialogue_act": "CHANGE_BUS_TYPE",
  "expected_context": {
    "destination": "Nellore",
    "bus_type": "Super Luxury"
  }
}

Cover:
- Changing destination
- Changing origin
- Changing date
- Changing bus category
- Passenger count changes
- Fare follow-ups
- Selected trip references
- Clarification replies
- Confirmation
- Rejection
- Conversation reset

Do not label an utterance correctly only because the generator has hidden context unavailable to the model.

Store required context explicitly.

---

# 9. AMBIGUOUS AND OUT-OF-SCOPE DATA

Generate at least:

500 out-of-scope examples.
500 ambiguity/clarification examples.

Out-of-scope examples:

"What's the cricket score?"
"Can you book a hotel?"
"What's the weather tomorrow?"
"Who won the election?"

Ambiguous examples:

"When is the bus?"
"How much?"
"Is it available?"
"Which one?"
"Tomorrow?"
"What about that service?"

For ambiguous examples, store:
- Possible intents
- Missing slots
- Clarification target
- Context requirements
- Whether the request can be resolved from previous turns

Do not force them into arbitrary enquiry labels.

---

# 10. NEGATION AND CORRECTION DATA

Generate at least 500 examples.

Include:

"No AC buses."
"Only non-AC services."
"Not a sleeper."
"Anything except Express."
"No, I said Tirumala, not Tirupati."
"Not tomorrow, the day after."
"Under 500 rupees."
"After 8 PM, not before."

Represent logical constraints explicitly.

Example:

{
  "text": "Anything except Express after 8 PM",
  "constraints": {
    "exclude_categories": ["EXPRESS"],
    "departure_after": "20:00"
  }
}

Ensure negated entities do not become positive filters.

---

# 11. ASR-ERROR STYLE DATA

Generate at least 500 synthetic ASR-like text examples.

Perturb clean English queries using realistic spelling and transcription patterns.

Examples:
- "nelore" instead of "Nellore"
- "super luxery" instead of "Super Luxury"
- "tirupathi" instead of "Tirupati"

Do not generate random character noise that a speech recognizer would never produce.

Where real Vosk transcripts are available, store them separately from synthetic corruptions.

Preserve both clean text and altered transcript.

Do not claim synthetic corruptions represent measured Vosk error rates.

---

# 12. ENTITY ANNOTATIONS

Each example must include structured labels where applicable.

Entities:
- Origin
- Destination
- Via location
- Operator
- Service category
- AC preference
- Sleeper preference
- Date
- Time
- Time period
- Passenger count
- Fare amount
- Service number
- Platform
- Accessibility requirement

When possible include character offsets for entity spans.

Example:

{
  "text": "Next AC bus from Guntur to Nellore after 7 PM",
  "intents": ["NEXT_BUS"],
  "entities": [
    {"type": "AC_PREFERENCE", "text": "AC", "value": true},
    {"type": "ORIGIN_CITY", "text": "Guntur", "canonical": "Guntur"},
    {"type": "DESTINATION_CITY", "text": "Nellore", "canonical": "Nellore"},
    {"type": "TIME", "text": "7 PM", "canonical": "19:00"}
  ]
}

Validate that character spans match the original text.

Do not assign fake canonical IDs.

Use IDs only when actual matching database records exist.

---

# 13. GENERATION ARCHITECTURE

Implement a reproducible local dataset generation pipeline.

Suggested structure:

training/
  datasets/
    raw/
    generated/
    reviewed/
    splits/
  generation/
    intent_generators/
    grammar_patterns/
    vocabulary/
    augmentations/
    dialogue_scenarios/
  validation/
    schema_validator.py
    duplicate_detector.py
    intent_validator.py
    entity_span_validator.py
    context_validator.py
    leakage_detector.py
  reports/

Use existing structures if present.

Prefer deterministic grammar templates, carefully authored phrase banks, compositional variations and controlled augmentation.

No external LLMs or web-generation services.

Use fixed random seeds.

Preserve generation provenance:
- Template family
- Generator version
- Seed
- Vocabulary source
- Augmentation type
- Dataset version

---

# 14. DIVERSITY CONTROL

Implement checks for:
- Exact duplicates
- Normalized duplicates
- Near duplicates
- Repeated sentence structures
- Overused station names
- Overused bus categories
- Unbalanced writing styles
- Intent contradictions
- Accidental label leakage
- Unrealistic grammar corruption

A dataset with 200 station-name substitutions of the same sentence must not pass diversity validation.

Calculate:
- Unique normalized text count
- Template-family diversity
- Lexical diversity
- N-gram overlap
- Intent distribution
- Style distribution
- Entity distribution

Use automated heuristics to flag suspicious cases for review.

Do not claim semantic uniqueness solely from string comparison.

If the configured generation resources cannot produce 200 genuinely diverse examples for an intent, report the shortfall instead of padding with duplicates.

---

# 15. DATASET FORMAT

Use UTF-8 JSONL as the canonical storage format.

Each record must include:

- example_id
- text
- language
- intent_codes
- dialogue_act
- dataset_type
- style
- entities
- context
- source_type
- generator_version
- template_family
- quality_status
- dataset_version

Optional:
- Parent example ID
- Clean transcript
- Noisy transcript
- Difficulty level
- Notes
- Review metadata

Support export to CSV and Hugging Face Dataset format.

Do not mix dataset metadata into the passenger text itself.

---

# 16. DATASET SPLITTING POLICY

Do not blindly random-split individual generated utterances.

Record sentence-template families and parent example IDs.

Prepare for family-level train/validation/test splitting.

Reserve genuinely independent human-collected examples for the final test set when available.

Synthetic test examples must be labelled as synthetic and are insufficient to establish real-world accuracy.

Actual split construction and full leakage audit will be completed in Phase 2C.

---

# 17. DATA QUALITY REPORT

Generate:

training/reports/PHASE_2B_DATASET_REPORT.md

Include:

1. Total examples generated.
2. Count by intent.
3. Count by dataset category.
4. Count by speaking style.
5. Count by template family.
6. Exact duplicate count.
7. Near-duplicate count.
8. Entity annotation coverage.
9. Ambiguity counts.
10. Multi-intent coverage.
11. Unreviewed example count.
12. Known quality limitations.

Include examples of failed validation.

Do not invent review completion percentages.

---

# 18. AUTOMATED TESTS

Test:

- All 60 intents have generation specifications.
- Intent labels exist in the registry.
- Entity annotations have valid spans.
- Examples are valid JSONL records.
- Unicode text is handled correctly.
- Data generation is reproducible.
- Negative constraints remain negative.
- Context examples contain required state.
- Multi-intent labels are valid.
- No exact duplicates remain.
- Templates do not leak across held-out families.
- Counts are measured, not hardcoded.

Run backend regression tests after generation.

Run Ruff and Mypy.

---

# 19. ACCEPTANCE CRITERIA

Phase 2B is complete when:

- At least 200 distinct, valid candidate examples exist for each of 60 intents.
- At least 12,000 valid single-intent examples exist.
- At least 1,000 multi-intent examples exist.
- At least 1,000 contextual follow-up examples exist.
- Additional challenge sets meet the specified counts.
- Dataset schema validation passes.
- Duplicate and diversity reports are generated.
- Entity annotations are consistent.
- Every record has provenance.
- Existing database and API tests continue passing.
- Dataset generation works fully offline.

If diversity or annotation quality cannot be established, report the limitation explicitly.

Do not misrepresent synthetic examples as human-reviewed.

Do not train models in this phase.

---

# 20. FINAL DELIVERABLES

Deliver:

1. Full 60-intent English dataset.
2. Multi-intent dataset.
3. Contextual dialogue dataset.
4. Negative and correction dataset.
5. Out-of-scope dataset.
6. ASR-style challenge dataset.
7. Entity annotation files.
8. Reproducible generation scripts.
9. Dataset validation scripts.
10. Diversity and coverage reports.
11. Dataset export utilities.
12. Phase 2C readiness report.

Execute generation and validation.

Report exact file paths and actual counts.

If the targets cannot be met without repetitive or low-quality examples, report PHASE 2B INCOMPLETE rather than fabricating progress.

Do not begin Phase 2C, Phase 2D training or Phase 4 UI.

Begin implementing in the existing repository immediately.