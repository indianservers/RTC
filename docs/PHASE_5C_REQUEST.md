# RTC SMART ENQUIRY — PHASE 5C
## Advanced Offline Conversation Intelligence, Human-Like Dialogue and Contextual Reasoning

You are a principal conversational AI engineer, NLP specialist, dialogue-systems architect, Python backend engineer and React full-stack developer.

Continue in the EXISTING RTC Smart Enquiry repository.

The previous phase focused on fixing persistent conversation memory, selected journey references and follow-up enquiries.

Your task is to substantially improve the quality of natural English text conversations so the assistant behaves like a knowledgeable bus stand enquiry officer.

Do not create a new chatbot architecture. Strengthen the existing engine.

## NON-NEGOTIABLE REQUIREMENTS

- 100% offline.
- English text only.
- No GPT, cloud AI, external LLMs or internet inference.
- No voice, microphone, ASR or TTS.
- Preserve existing RTC database, migrations and APIs.
- Reuse the trained local NLP classifier where available.
- Keep deterministic NLP fallback operational.
- Do not invent bus schedules, fares, seat availability, delays or platforms.
- No unnecessary redesign of administrative screens.
- Prioritize conversational correctness over visual effects.

---

# 1. AUDIT CURRENT CONVERSATION INTELLIGENCE

Inspect the existing implementation of:

- Intent classification
- Entity extraction
- Multi-intent detection
- Dialogue acts
- Conversation memory
- Selected-trip references
- Journey comparison
- Context invalidation
- Clarifications
- Response templates
- Follow-up suggestions
- Frontend session handling

Identify remaining failures using actual code and tests.

Do not assume functionality is complete based on previous prompts or documentation.

Create a concise conversation-capability gap matrix.

# 2. COMPOSITIONAL ENQUIRY UNDERSTANDING

Handle multiple enquiries in one passenger message.

Examples:

"Next bus to Tirupati, fare and platform?"

"Is the Hyderabad bus late, and are seats available?"

"Show the cheapest AC sleeper to Vizag tomorrow."

"Which bus arrives earliest, and does it stop at Ongole?"

Represent enquiries as structured plans:

{
  "primary_intent": "NEXT_BUS",
  "secondary_intents": ["GET_FARE", "BUS_PLATFORM"],
  "shared_entities": {
    "destination": "Tirupati"
  }
}

Distinguish secondary intents from filters.

For example:

"Cheapest AC sleeper"

is primarily CHEAPEST_BUS with AC and sleeper constraints.

Do not incorrectly classify AC and sleeper as unrelated standalone questions.

# 3. MULTI-INTENT QUERY PLANNING

Create or improve:

ConversationQueryPlanner

Responsibilities:
- Identify enquiry dependencies.
- Determine required database calls.
- Reuse previous results where valid.
- Avoid redundant service searches.
- Preserve consistent trip references.
- Aggregate results.
- Handle partially unavailable information.

For:

"Next bus to Nellore, fare and platform."

First identify matching services.

Then resolve applicable fares and platform assignments for those same trips.

Do not retrieve fare or platform data for unrelated services.

# 4. CONTEXTUAL COMPARISON ENGINE

Support:

"Which one is cheaper?"

"Is the first faster than the second?"

"Compare the two."

"Which one has AC?"

"Which arrives earlier?"

"How much more is Super Luxury?"

"Which is better for reaching before 8 AM?"

Compare only compatible journeys.

Use:
- Same origin/destination segment
- Correct travel date
- Known fare information
- Actual arrival/departure values
- Available amenity data
- Valid selected result references

Never conclude that unknown fare means cheaper.

Explain the reason for a recommendation using actual database fields.

# 5. DEEP REFERENCE RESOLUTION

Handle:

"That one"
"The other one"
"The next one"
"The one before it"
"The cheaper one"
"The Express"
"The 7 PM one"
"Both"
"Neither"
"The last option"
"The second service"

Use the current result set and conversation history.

When the reference is ambiguous, ask a focused clarification.

Do not arbitrarily select a service.

Store stable service/trip identifiers rather than only result positions.

# 6. MULTI-STEP CONVERSATIONAL REASONING

Support conversations such as:

Passenger:
"I need to reach Tirupati before 7 AM tomorrow."

Assistant:
Searches valid journeys with arrival deadline.

Passenger:
"Only AC."

Assistant:
Reapplies the deadline with AC constraint.

Passenger:
"Under 900."

Assistant:
Applies fare limit.

Passenger:
"What if I change at Kadapa?"

Assistant:
Searches feasible connecting journeys with that transfer preference.

Passenger:
"Which is fastest?"

Assistant:
Ranks valid candidates by arrival time.

Maintain all still-valid constraints.

Do not remove restrictions without explicit passenger instruction.

# 7. CONVERSATIONAL CORRECTIONS

Handle:

"No, Tirumala."

"Actually, Hyderabad."

"I meant tomorrow night."

"Not AC, ordinary."

"Two passengers, not three."

"Forget the earlier time."

"Remove the fare limit."

Implement explicit context operations.

Validate whether corrections invalidate:
- Selected trip
- Previous results
- Platform information
- Fare
- Journey ranking
- Transfer plans

Never leave conflicting stale state.

# 8. SMART CLARIFICATION STRATEGY

Ask only for information essential to continue.

Examples:

"How much?"
If selected bus exists:
Use it.

If route exists but multiple categories:
Provide known fare ranges or ask which category, based on actual data.

If no route context:
Ask destination or service.

"Is it available?"
Use selected trip when possible.

"What about tomorrow?"
Change travel date and repeat the active enquiry.

Avoid:
- Repeating already known details.
- Asking multiple questions at once unnecessarily.
- Generic "Please provide more information" replies.
- Restarting the conversation after corrections.

# 9. NATURAL RESPONSE GENERATION

Improve deterministic English templates.

Replies should resemble normal human conversation without pretending to have knowledge beyond the database.

Examples:

Instead of:
"Intent NEXT_BUS matched 3 results."

Say:
"I found three scheduled services to Nellore. The earliest leaves at 2:30 PM."

Instead of:
"NO_RESULTS."

Say:
"I couldn't find an AC service to Nellore after 9 PM in the current schedule."

Instead of:
"FARE_UNKNOWN."

Say:
"I found the selected bus, but its fare isn't available in the current database."

Instead of:
"CONTEXT_UPDATED."

Say:
"Okay, I've changed the destination to Tirumala."

Use data-driven templates.

Do not repeat all journey details on every turn.

Do not fabricate polite explanations or reasons for delays.

# 10. CONVERSATION SUMMARY

Support:

"What have we selected?"

"Summarize my journey."

"Which bus am I asking about?"

"Remind me of the options."

"Start over."

Return short summaries of the active conversation state.

Example:

"You're looking for an AC bus from Vijayawada to Tirupati tomorrow morning, under ₹800. No service has been selected yet."

Only state values confirmed or explicitly marked as defaults.

# 11. SMART SUGGESTIONS

Generate follow-up suggestions based on:
- Detected intent
- Available fields
- Current selected journey
- Valid backend capabilities
- Missing information
- Search outcome

After a selected bus:
- What is the fare?
- Which platform?
- Does it have AC?
- View stops.

After no results:
- Search tomorrow.
- Try later.
- Show connecting services.
- Remove one optional filter.

All suggestions must execute real backend actions.

Do not suggest unsupported operations.

# 12. HANDLE OUT-OF-SCOPE QUESTIONS

Examples:

"What's the weather?"
"Who is the Prime Minister?"
"Can you order food?"
"Tell me a joke."

Respond briefly:

"I can help with RTC bus schedules, fares, routes and station information."

Do not force unrelated questions into RTC intents.

Keep context intact unless the passenger requests reset.

# 13. HANDLE PARTIAL DATA

Examples:

- Fare known, platform unknown.
- Timetable known, seat availability unknown.
- Route known, live bus position unavailable.
- Service cancelled, alternatives available.

Provide known information while clearly identifying unknown fields.

Do not convert missing values to zero, false or confirmed negative.

# 14. CHAT UI IMPROVEMENTS

Preserve the established visual style.

Improve:
- Message grouping
- Readable assistant replies
- Selected journey context strip
- Multi-intent answer sections
- Expandable journey comparisons
- Contextual follow-up chips
- Clarification choices
- Conversation reset
- Scroll position
- Streaming/loading state where supported

Do not simulate word-by-word AI streaming unless the backend actually supports streaming responses.

Avoid unnecessary whitespace.

Keep the conversation area central and usable.

# 15. BACKEND CONTRACT

Reuse:

POST /api/v1/conversation/message

Support a structured response containing:
- Session ID
- Detected intents
- Dialogue act
- Context changes
- Selected journey
- Results
- Response text
- Follow-up suggestions
- Clarification request
- Source/freshness metadata

Keep backwards compatibility with existing frontend consumers.

Do not duplicate the conversation API.

# 16. CONVERSATION SECURITY

Ensure:
- Session isolation.
- Session expiry.
- No cross-user context leakage.
- Atomic context updates.
- Safe result references.
- Kiosk reset behavior.
- No unnecessary personal data retention.

Handle concurrent requests for the same session safely.

# 17. TESTING

Create at least 300 multi-turn conversational tests.

Include:

- Fare follow-up
- Platform follow-up
- AC filter
- Sleeper filter
- Changing destination
- Changing date
- Changing time
- Negation
- Selected result
- Two-service comparison
- Multi-intent questions
- Missing information
- Out-of-scope questions
- Conversation summaries
- Unknown data
- Conflicting filters
- Concurrent sessions
- Expired results
- Context reset

Measure:
- Intent correctness
- Entity correctness
- Context transition correctness
- Query plan correctness
- Final database answer correctness

Do not treat a keyword in the response as proof of success.

# 18. FINAL END-TO-END TEST

Using the local application:

1. "Next bus to Nellore?"
2. "Second one."
3. "How much?"
4. "Does it have AC?"
5. "When will it arrive?"
6. "Compare with the first one."
7. "What about tomorrow?"
8. "Only Super Luxury."
9. "No, I meant Tirupati."
10. "Summarize my journey."

Inspect the context and selected service after every turn.

Verify all operational values against the local database.

# 19. DELIVERABLES

Deliver:
1. Improved multi-intent parser.
2. Conversation query planner.
3. Contextual comparison engine.
4. Deep reference resolution.
5. Correction handling.
6. Clarification strategy.
7. Natural response templates.
8. Conversation summary.
9. Contextual suggestions.
10. UI integration.
11. Automated tests.
12. Completion report.

Run actual backend and frontend tests.

Report tests passed/failed, measured latency and remaining limitations.

Do not claim completion merely because example conversations sound natural.

Start implementation immediately.

Do not begin speech development or unrelated UI redesigns.