# RTC OFFLINE AI — PHASE 3A
## Advanced English Text Conversation & Dialogue Intelligence

You are a senior conversational AI engineer, NLP specialist, transportation-domain architect and Python backend developer.

Continue development in the EXISTING RTC Offline AI repository.

Phase 1 established the database, enquiry engine and model infrastructure.
Phase 2 established the English NLP dataset, classifier and text-based conversation foundation.

Your task is to strengthen the text conversation engine to handle complex, realistic, multi-turn bus stand enquiries.

IMPORTANT:
- Work in the existing repository.
- Inspect previous implementation before changing code.
- Preserve database migrations and existing API contracts.
- No GPT or cloud AI.
- No external runtime requests.
- English text only.
- Do not download or integrate speech models.
- Do not build graphical UI.
- No hardcoded answers.
- All operational information must originate from the local RTC database.

## 1. AUDIT THE EXISTING CONVERSATION ENGINE

Inspect:
- Trained English model and fallback classifier
- NLP intent registry
- Entity extractor
- Dialogue state manager
- Context manager
- RTC enquiry query orchestrator
- Response templates
- Conversation CLI
- Existing tests

Create a short implementation gap report.

Do not duplicate working modules.

## 2. STRUCTURED CONVERSATION STATE

Create or improve a strongly typed conversation state containing:

- Session ID
- Current bus stand
- Origin station
- Destination station
- Travel date
- Departure time window
- Bus category
- AC preference
- Sleeper preference
- Operator preference
- Maximum fare
- Passenger count
- Last recognised intents
- Last query filters
- Last result list
- Selected trip ID
- Selected route ID
- Pending clarification
- Last system question
- Conversation revision
- Last activity timestamp

Maintain a clear distinction between:
- Explicit user preferences
- Inherited context
- System defaults
- Inferred candidate values
- Confirmed selected services

Do not allow unconfirmed inferred values to silently become permanent context.

## 3. CONTEXT UPDATE ENGINE

Implement explicit operations:

SET_SLOT
REPLACE_SLOT
CLEAR_SLOT
CONFIRM_SLOT
REJECT_SLOT
RESET_CONTEXT
SELECT_RESULT
REFINE_RESULTS
SWITCH_INTENT

Examples:

"Only AC" → SET_SLOT(ac=true)

"No AC" → SET_SLOT(ac=false)

"Not sleeper" → SET_SLOT(sleeper=false)

"Actually, Tirupati" → REPLACE_SLOT(destination=Tirupati)

"Forget the price limit" → CLEAR_SLOT(max_fare)

"Same bus tomorrow" → change date and revalidate trip selection

Use a dependency graph to invalidate stale fields.

Changing the destination must invalidate selected trips, fares and platform references.

Changing the date must revalidate service availability.

Changing bus category must invalidate incompatible selected services.

## 4. REFERENTIAL UNDERSTANDING

Handle references such as:

"That bus"
"This one"
"The first one"
"The second one"
"The cheaper one"
"The fastest one"
"The previous one"
"Any other?"
"Same one tomorrow"
"What about that Express?"
"Does it stop there?"

Resolve references only from current, valid conversation results.

Never guess a result index when the previous list is unavailable or expired.

Maintain stable result identifiers when sorting and filtering.

If reference resolution is ambiguous, ask a targeted clarification question.

## 5. MULTI-INTENT EXECUTION

Examples:

"Next bus to Nellore and fare?"

"Which is the cheapest AC bus tomorrow, and when will it arrive?"

"Is the bus delayed and which platform should I use?"

"Show direct buses to Tirupati, but also tell me the fastest connecting option."

Implement an execution planner that can:
- Identify multiple intents
- Share extracted entities
- Resolve dependencies
- Reuse selected trip references
- Avoid repeated database queries
- Combine grounded results
- Return partial answers when some data is unavailable

Do not generate unrestricted SQL from model output.

## 6. TEMPORAL REASONING

Support:
- Today
- Tomorrow
- Day after tomorrow
- This evening
- Tonight
- Tomorrow morning
- After 8 PM
- Before 6 AM
- Around 9:30 PM
- In the next two hours
- Same time tomorrow
- First bus tomorrow
- Last bus tonight
- Next available after midnight

Use station-local timezone, not machine-local assumptions.

Preserve the original time expression and resolved timestamp.

Use a clock abstraction for deterministic testing.

Handle cross-midnight journeys correctly.

## 7. NEGATION AND CORRECTION

Examples:

"No, not Tirupati, Tirumala."

"Not the AC one."

"Anything except Express."

"I said tomorrow, not today."

"Actually, I need two seats, not three."

"Not before 8, after 8."

Apply explicit replacement and exclusion operations.

Do not treat negated words as positive filters.

Validate contradictory conditions.

## 8. SMART CLARIFICATION ENGINE

Ask one precise question when information is missing.

Examples:

"Next bus?"
→ "Where would you like to travel?"

"How much?"
→ Use selected trip if available; otherwise clarify which journey.

"Tomorrow."
→ Apply to the active enquiry.

"Which platform?"
→ Use the selected trip; otherwise identify the required service.

"Hyderabad bus."
→ Ask the intended enquiry if context does not make it clear.

Prioritize clarification of the field most necessary for query execution.

Do not ask for information already present in valid context.

## 9. BUS COMPARISON INTELLIGENCE

Allow contextual comparison:

"Which one is cheaper?"

"Is Super Luxury faster than Express?"

"Show only buses arriving before 10 PM."

"Which has sleeper berths?"

"Remove the first option."

"Show me the next three services."

Ensure comparisons use compatible journey segments and travel dates.

Unknown fares must not be treated as zero.

Missing arrival times must not be used in fastest-service ranking.

## 10. RESPONSE QUALITY

Responses must:
- Be brief and natural
- Answer the actual question
- Include useful service identifiers
- Include times with clear AM/PM formatting
- Include relevant fare information only when known
- Distinguish scheduled from live information
- Label DEMO operational data
- Ask for clarification only when necessary

Avoid repetitive introductions.

Do not return lengthy JSON to ordinary passengers.

Retain structured JSON for debug mode and API consumers.

## 11. CLI ENHANCEMENTS

Improve the existing terminal chat application.

Commands:

/help
/reset
/context
/results
/select 2
/debug
/station
/history
/exit

Allow selecting previous query results by number.

Display appropriate error messages.

Ensure UTF-8 output and compatibility with Windows terminals.

Do not build a graphical user interface.

## 12. CONVERSATION API

Reuse or extend:

POST /api/v1/conversation/message
POST /api/v1/conversation/reset
GET /api/v1/conversation/{session_id}/context

Provide:
- Session ID
- Recognized intents
- Applied context changes
- Clarification request, if any
- Matching services
- Selected trip
- Grounded response text
- Warning/source metadata
- Processing time

Protect sessions from cross-user leakage.

Avoid exposing sensitive debug details in standard responses.

## 13. AUTOMATED TESTING

Create at least 300 multi-turn conversation scenarios.

Cover:
- 2-turn enquiries
- 5-turn enquiries
- 10-turn enquiries
- Multiple changes of destination
- Multiple changes of date
- Bus-category changes
- Fare filtering
- Result selection
- Corrections
- Contradictions
- Negations
- Out-of-scope questions
- Ambiguous references
- Session expiry
- Concurrent sessions
- Missing data
- Cancelled services
- Overnight trips
- Reset and restart

Validate:
1. Intent accuracy
2. Entity resolution
3. Context transitions
4. Actual database query arguments
5. Returned service IDs
6. Response correctness

Do not validate success merely because the response contains expected keywords.

## 14. PERFORMANCE

Benchmark:
- NLP classification latency
- Context-update latency
- Database lookup latency
- Total text response time
- Memory usage
- Concurrent session behaviour

Use reproducible fixtures.

Record P50/P95/P99 latency where sufficient samples exist.

Do not invent performance numbers.

## 15. DELIVERABLES

Provide:
1. Advanced conversation state engine.
2. Context dependency and invalidation logic.
3. Referential result resolver.
4. Multi-intent execution planner.
5. Temporal reasoning improvements.
6. Negation and correction support.
7. Clarification engine.
8. Bus comparison intelligence.
9. Improved terminal CLI.
10. API enhancements.
11. 300+ multi-turn test scenarios.
12. Benchmark report.
13. Updated documentation.

Run all relevant tests, Ruff and Mypy.

Preserve previously working Phase 1 and Phase 2 functionality.

Clearly report any incomplete requirements.

Do not start Phase 3B, voice development or Phase 4 UI.

Begin implementation immediately.