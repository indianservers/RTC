# RTC SMART ENQUIRY — MAJOR CONVERSATIONAL AI UPGRADE
## Persistent Context, Intelligent Follow-Ups, Journey Memory and Chat UX

You are a senior conversational AI architect, NLP engineer, Python backend specialist and React UI developer.

Work in the EXISTING RTC Smart Enquiry repository.

The current application is running at:
http://127.0.0.1:8000

The user has provided a screenshot showing this real problem:

User: "2"
Assistant: "Selected journey option 2."

User: "What is the fare?"
Assistant: "Demo schedule/data: No matching information is available for that enquiry."

This is unacceptable when a journey has already been selected and the relevant fare exists in the database.

Your objective is to transform the application into a genuinely conversational, context-aware, offline RTC enquiry assistant.

This is a functional conversation-engine upgrade, not merely a visual redesign.

## CRITICAL REQUIREMENTS

- 100% offline.
- English text only for now.
- No GPT, cloud AI or external APIs.
- Use the existing trained local NLP model where available.
- Preserve deterministic fallback.
- Preserve existing RTC database.
- Preserve APIs and migrations wherever practical.
- No hardcoded timetable or fare answers.
- No simulated AI replies in production.
- Do not duplicate existing dialogue or enquiry modules.
- Do not silently introduce a new model or framework.
- Build on the existing React/FastAPI architecture.

# 1. AUDIT THE CURRENT CONVERSATION FAILURE

Trace the complete sequence:

1. Passenger searches for a journey.
2. Backend returns a list of journeys.
3. Passenger selects option 2.
4. System confirms the selection.
5. Passenger asks "What is the fare?"
6. Backend returns "No matching information."

Inspect:
- Frontend session ID management
- Conversation API request/response
- Context persistence
- Result-list storage
- Selection resolution
- Selected trip/journey ID
- Origin and destination
- Boarding and alighting segments
- Travel date
- Fare lookup invocation
- NLP intent detection
- Response formatting

Identify the actual root cause using logs and tests.

Potential causes to investigate:
- Selected journey is saved only in frontend state.
- Result list is lost between requests.
- Session ID changes between messages.
- Fare enquiry doesn't inherit selected journey.
- Fare service expects origin/destination rather than trip ID.
- Selection only saves the option number.
- Multi-leg journey fares are not aggregated.
- Trip reference becomes invalid after context updates.

Do not assume which one is responsible without examining code.

Fix the underlying defect and add a regression test reproducing the exact screenshot sequence.

If selected service has no applicable fare record, respond accurately:
"The fare for that service is not available in the current database."

Do not fabricate a fare merely to pass the test.

# 2. PERSISTENT CONVERSATION MEMORY

Create or strengthen ConversationState.

Store:
- session_id
- current_station_id
- operator_id
- origin_id
- destination_id
- travel_date
- time_window
- filters
- last_intents
- current_result_set
- selected_result_id
- selected_trip_id
- selected_journey_id
- selected_segment
- current_ranking
- pending_clarification
- last_question
- last_answer
- last_activity_at
- state_version

Store enough information to correctly reconstruct the selected journey.

Do not store only the text "option 2".

Distinguish:
- User-specified values
- Default station context
- Inherited values
- Confirmed selections
- Unconfirmed inferred values

Keep sessions isolated.

Use database-backed or appropriate local persistence so state survives separate API requests.

Define expiration and cleanup rules.

Do not expose another passenger's session.

# 3. CONVERSATION CONTEXT ENGINE

Implement structured slot updates:

SET
REPLACE
CLEAR
INHERIT
CONFIRM
REJECT
RESET
SELECT_RESULT

Examples:

"Next bus to Nellore?"
→ destination=Nellore.

"Only AC."
→ retain Nellore, ac=true.

"Tomorrow morning."
→ retain Nellore and AC, update date/time.

"No, Tirupati."
→ replace destination, invalidate selected trip.

"Cheapest one?"
→ rank current valid results by known fare.

"Second one."
→ resolve selected result using current result set.

"How much?"
→ use selected journey and boarding/alighting segment.

"Does it stop at Ongole?"
→ use selected journey route stops.

"Same bus tomorrow?"
→ search whether equivalent service operates tomorrow; do not assume the same dated trip exists.

Every context modification must have explicit invalidation rules.

# 4. STABLE JOURNEY REFERENCES

Store query results with stable identifiers.

For each result record keep:
- Result ID
- Result-list version
- Trip ID or itinerary reference
- Service ID
- Boarding station
- Alighting station
- Travel date
- Departure timestamp
- Bus category
- Applicable fare reference, when available

When user selects "2":
- Resolve the second result in the latest displayed list.
- Save the actual journey identity and travel segment.
- Confirm selection.
- Keep it available for subsequent enquiries.

Handle:
- First one
- Second one
- Third option
- Last one
- Cheapest one
- Fastest one
- That bus
- This bus
- Same service
- Previous option

Never use stale option indexes after sorting, filtering or changing destination.

# 5. FOLLOW-UP INTENT UNDERSTANDING

Support short and elliptical utterances:

"Fare?"
"How much?"
"AC?"
"Sleeper?"
"What about tomorrow?"
"Any earlier?"
"Any cheaper?"
"Which platform?"
"Does it stop there?"
"How long?"
"Next one?"
"What about the second bus?"

Resolve using conversation context.

Do not treat each message as a fresh independent enquiry.

Use a combination of:
- Trained intent classifier
- Deterministic follow-up rules
- Contextual slot filling
- Typed database enquiry tools

Never make the NLP model invent facts.

# 6. MULTI-TURN CONVERSATION FLOWS

Implement these scenarios.

A:
"Next bus to Nellore?"
"Second one."
"What is the fare?"
"Which platform?"
"Does it stop at Ongole?"

B:
"Any AC bus to Hyderabad tonight?"
"Cheapest?"
"How long does it take?"
"What about tomorrow?"
"Is sleeper available?"

C:
"I want to go to Tirumala."
"Any direct service?"
"What if I change at Tirupati?"
"Which arrives first?"
"Select the first option."
"Fare?"

D:
"Next bus to Vizag."
"No, I meant Kakinada."
"Only Super Luxury."
"After 7 PM."
"What is the fare?"

E:
"Show the next three buses."
"Second one."
"Actually, the first one."
"Does that bus have AC?"
"Is it cancelled?"

Test the complete conversation state after every turn.

# 7. INTELLIGENT CLARIFICATIONS

Ask one focused question only when essential context is missing.

Examples:

User: "How much?"
No selected route or journey:
"Which destination or bus would you like the fare for?"

User: "Second one."
No valid result list:
"Please search for buses first so I can identify the second option."

User: "Which platform?"
Multiple equally relevant trips:
"Which service are you asking about?"

User: "Tomorrow."
Active enquiry exists:
Update travel date and repeat the enquiry.

Avoid repetitive requests for the source station when the app already knows the selected current bus stand.

# 8. CONVERSATIONAL RESPONSE ENGINE

Make replies sound natural and helpful.

Instead of:
"Selected journey option 2."

Prefer:
"You've selected the 3:15 PM Super Luxury service to Nellore. What would you like to know about it?"

Only include fields actually known.

Instead of:
"Demo schedule/data: No matching information is available for that enquiry."

Prefer a specific explanation:
"I found the selected service, but its fare is not recorded."

Or:
"I couldn't find any matching buses for tomorrow morning."

Or:
"Which bus would you like the fare for?"

Provide direct answers rather than generic database error messages.

Do not repeat "Demo schedule/data" at the beginning of every sentence.

Use a visible DEMO badge on appropriate results and keep operational provenance in response metadata.

# 9. CHAT UI REDESIGN

Use the uploaded screenshot as the current-state reference.

Preserve the existing branding, navigation and overall styling, but improve the main conversation workspace.

Make the experience resemble a modern conversational assistant.

Requirements:
- Larger usable conversation area.
- Less unnecessary whitespace.
- Clear assistant and passenger message alignment.
- Better message grouping.
- Natural, readable chat bubbles.
- Sticky message composer.
- Smooth scroll-to-latest.
- Visible selected journey context.
- Compact expandable service cards.
- Contextual follow-up buttons.
- Clarification choices.
- Loading and error states.
- New conversation/reset.
- Conversation history within active session.

Show a compact context strip:

Vijayawada → Nellore
Tomorrow morning
AC only
Selected: Super Luxury

Allow the passenger to clear/change context through real backend actions.

Do not let the context strip become an independent, inconsistent source of truth.

Remove redundant headings and excessive vertical padding.

Keep the app visually premium, compact and easy to read.

# 10. SMART FOLLOW-UP SUGGESTIONS

Generate suggestions from current context and available capabilities.

After showing buses:
- Cheapest one?
- Any AC?
- What about tomorrow?
- Show stops.

After selecting a bus:
- What is the fare?
- Which platform?
- Does it stop at Ongole?
- What is the arrival time?

After a fare enquiry:
- Any cheaper option?
- Compare other categories.

After no results:
- Search later
- Try tomorrow
- Show connecting buses
- Remove an optional filter

All suggestions must call the actual conversation API.

Do not show actions that the backend cannot support.

# 11. API CONTRACT

Reuse or improve:

POST /api/v1/conversation/message

Return:
- session_id
- message_id
- response_text
- detected_intents
- detected_entities
- current_context
- selected_journey
- result_set
- follow_up_suggestions
- pending_clarification
- data_source
- warnings

Use typed Pydantic schemas.

Ensure session IDs remain stable between turns.

When updating context, use atomic transactions or version-safe operations.

Protect against messages arriving out of order.

# 12. SESSION SECURITY AND PRIVACY

For shared kiosks:
- Expire idle sessions.
- Clear history on reset.
- Do not show previous passenger's conversation.
- Do not expose session identifiers unnecessarily.
- Use unpredictable session IDs.
- Enforce session isolation on the backend.

For a personal browser:
- Restore current session where appropriate.
- Allow explicit new conversation.

Make kiosk versus personal-browser behavior configurable.

# 13. ERROR RECOVERY

Handle:
- Selected journey no longer exists.
- Selected trip is cancelled.
- Fare record missing.
- Platform unknown.
- Date changes.
- Result list expired.
- Backend restarted.
- Session expired.
- Database unavailable.
- NLP confidence too low.
- No buses found.

Explain the exact problem where possible.

Offer one useful next action.

Never silently discard context.

# 14. AUTOMATED REGRESSION TESTS

Create tests reproducing the screenshot issue exactly.

Test:
1. Search a destination.
2. Receive multiple results.
3. Select option 2.
4. Ask "What is the fare?"
5. Confirm fare is looked up for option 2 and its correct boarding/alighting segment.
6. Confirm correct response when fare is unknown.
7. Ask "Which platform?"
8. Confirm the same selected trip is used.
9. Change destination.
10. Confirm outdated trip selection is cleared.

Also test:
- Session persistence.
- Concurrent sessions.
- Context expiry.
- Multi-intent queries.
- Short follow-ups.
- Result reordering.
- Destination corrections.
- Date corrections.
- Selected journey comparisons.
- Kiosk reset.
- No fabricated data.

Add at least 100 multi-turn regression scenarios.

Include real FastAPI + database integration tests, not only mocked functions.

# 15. VERIFY END-TO-END

Run the local application.

Use actual labelled demo records.

Execute this sequence:

"Next bus to Nellore?"
"2"
"What is the fare?"
"Is it AC?"
"Does it stop at Ongole?"
"What about tomorrow?"
"Cheapest option?"
"No, I meant Tirupati."

Verify after every turn:
- Session ID
- Context slots
- Selected journey
- Invoked database query
- Response content
- Demo status

Run:
- Backend tests
- Frontend tests
- Playwright tests
- Ruff
- Mypy
- Offline smoke tests

Do not hardcode expected responses in the frontend.

# FINAL DELIVERABLES

Deliver:
1. Persistent conversation context.
2. Correct journey selection handling.
3. Contextual fare lookup.
4. Multi-turn follow-up intelligence.
5. Correction and invalidation logic.
6. Natural response templates.
7. Improved chat interface.
8. Smart follow-up suggestions.
9. Session security.
10. Automated regression tests.
11. Updated documentation.
12. Completion report.

Most important acceptance criterion:

After selecting option 2, asking "What is the fare?" MUST use that exact selected journey, date and boarding/alighting segment.

If fare data is missing, explain that specifically instead of returning a generic "no matching information" message.

Do not stop at UI changes or mockup generation.

Identify and fix the underlying backend context issue.

Begin implementation immediately in the existing repository.