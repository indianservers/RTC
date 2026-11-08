# RTC SMART ENQUIRY — PHASE 5D
## Intelligent Error Recovery, Self-Improving NLP Feedback & Conversation Reliability

You are a senior conversational AI architect, NLP evaluation engineer, Python backend specialist, MLOps engineer and React application developer.

Continue working in the EXISTING RTC Smart Enquiry repository.

The user wants a highly intelligent, natural, fully offline bus stand enquiry assistant.

Previous development includes:
- Database-driven RTC enquiry services
- English NLP classification
- Multi-turn conversation memory
- Selected journey references
- Advanced route planning
- Passenger chat UI
- Data management and operational updates
- Natural response templates

Your task is to strengthen misunderstanding detection, conversation recovery, error analysis and supervised model improvement.

Do not replace the existing architecture.

## NON-NEGOTIABLE REQUIREMENTS

- Fully offline.
- English text only.
- No GPT, LLM or cloud AI.
- No speech development.
- Preserve existing database schema and migrations.
- Preserve existing API compatibility.
- Reuse existing trained classifier where available.
- Keep deterministic NLP fallback.
- No hardcoded RTC facts.
- No automatic unreviewed model retraining or deployment.
- No unnecessary visual redesign.

---

# 1. AUDIT EXISTING FAILURES

Inspect:
- NLP classifier
- Confidence calculation
- Entity extraction
- Dialogue acts
- Conversation state
- Query orchestrator
- Response rendering
- Error handling
- User feedback mechanisms
- Model registry
- Training dataset
- Evaluation pipeline

Identify failure categories:

INTENT_MISCLASSIFICATION
ENTITY_RESOLUTION_ERROR
MISSING_CONTEXT
AMBIGUOUS_REFERENCE
CONTRADICTORY_FILTERS
NO_MATCHING_SERVICE
DATA_NOT_AVAILABLE
STALE_OPERATIONAL_DATA
DATABASE_ERROR
MODEL_UNAVAILABLE
UNSUPPORTED_ENQUIRY

Create a reusable error taxonomy.

Do not treat every no-result enquiry as an NLP failure.

# 2. CONVERSATIONAL REPAIR ENGINE

Implement or improve:

ConversationRepairEngine

Handle corrections:

"No, I meant the last bus."

"I said Tirumala, not Tirupati."

"No, tomorrow morning."

"That's not the bus I selected."

"Not AC, ordinary."

"I asked for the fare, not the timing."

Apply targeted context changes.

Preserve valid existing context.

Invalidate dependent trip selections when necessary.

Do not restart the conversation for a simple correction.

# 3. UNCERTAINTY HANDLING

Use:
- Calibrated model confidence where available
- Intent score margins
- Rule conflicts
- Entity match ambiguity
- Missing required slots
- Context compatibility

Do not treat uncalibrated model scores as probabilities.

Implement states:

CONFIDENT
CLARIFICATION_REQUIRED
LOW_CONFIDENCE
OUT_OF_SCOPE
UNSUPPORTED

Tune thresholds on validation data.

For uncertain queries, ask a specific question.

Example:

"Do you want the first bus of the day or the next available bus?"

Avoid generic "I didn't understand" replies where a targeted clarification is possible.

# 4. NO-RESULT DIAGNOSIS

When an enquiry returns no services:

Determine whether:
- Destination is unknown
- Date is outside schedule coverage
- Bus category filter excludes all services
- Departure window is too restrictive
- Fare ceiling excludes known fares
- Direct services are unavailable
- All matching trips are cancelled
- Data is missing or unpublished

Explain the actual reason only when supported by diagnostic queries.

Offer appropriate recovery actions.

Examples:

"No AC services match your requested time window. I can search other categories or a later departure."

"I couldn't find a direct service. Would you like connecting options?"

Do not silently relax any hard constraint.

# 5. USER FEEDBACK CAPTURE

Add lightweight feedback to assistant replies:

Helpful
Not helpful
Incorrect information
Wrong destination
Wrong bus
Wrong fare
Wrong timing
Wrong intent
Other

Feedback must:
- Be optional
- Be stored locally
- Reference the relevant message/enquiry
- Preserve source/model version
- Avoid unnecessary personal identifiers
- Support configurable retention

Do not display complex feedback forms to passengers.

Use compact controls.

# 6. DATA VERSUS MODEL ERROR

Differentiate:

MODEL_ERROR:
The user's intent or entity was misunderstood.

DATA_ERROR:
The classified enquiry was correct, but database information was missing or inaccurate.

CONTEXT_ERROR:
A previous journey or passenger preference was incorrectly retained or discarded.

RESPONSE_ERROR:
Correct structured results were rendered incorrectly.

OPERATIONAL_ERROR:
The local backend could not execute the enquiry.

Maintain separate error statistics.

This classification should drive the corrective workflow.

# 7. REVIEW QUEUE

Create an admin-only NLP Review Queue.

Include:
- Original query, where retention is permitted
- Predicted intent
- Corrected intent
- Extracted entities
- Corrected entities
- Conversation context snapshot
- Error category
- User feedback
- Model version
- Dataset version
- Review status
- Reviewer notes

Statuses:

NEW
TRIAGED
NEEDS_DATA_FIX
NEEDS_LABEL_REVIEW
APPROVED_FOR_TRAINING
RESOLVED
REJECTED

Protect access to retained conversation data.

Provide anonymization and deletion controls.

# 8. ACTIVE LEARNING DATASET

Generate a reviewed feedback dataset.

Only include examples explicitly approved for training.

Support:
- Corrected intent labels
- Corrected entity spans
- Hard negative examples
- Similar-intent confusion cases
- Short follow-up utterances
- Contextual examples
- Out-of-scope examples

Track:
- Source
- Approval status
- Reviewer
- Model version
- Date
- Training eligibility

Do not append raw passenger feedback directly to the training dataset without review.

# 9. MODEL IMPROVEMENT PIPELINE

Implement an offline retraining workflow that can be initiated by an authorized administrator.

Flow:

Reviewed feedback
→ Dataset validation
→ Leakage check
→ Training candidate
→ Evaluation
→ Regression comparison
→ Manual approval
→ Deployment
→ Rollback support

Reuse the existing TensorFlow/SVM training infrastructure.

Do not retrain after every passenger message.

Do not automatically promote a new model.

Keep the previously active model for rollback.

# 10. EVALUATION AND DRIFT MONITORING

Track:
- Intent confusion rates
- Clarification frequency
- Out-of-scope detection
- No-result frequency
- Entity resolution failures
- Context repair frequency
- Feedback categories
- End-to-end answer correctness on reviewed cases

Detect shifts in question types and newly introduced station or category names.

Do not label missing feedback as positive feedback.

Do not claim model drift from tiny sample sizes.

# 11. RESPONSE QUALITY IMPROVEMENTS

Replace generic errors with specific, grounded responses.

Example:

Instead of:
"No matching information."

Say:
"I found the selected service, but the fare is not recorded in the current database."

Instead of:
"Invalid enquiry."

Say:
"Which destination would you like to travel to?"

Instead of:
"Unknown intent."

Say:
"I can help with bus timings, routes, fares and platforms. What would you like to know?"

Never fabricate information to sound helpful.

# 12. ADMIN DIAGNOSTICS

Create or enhance a developer/admin diagnostics page.

Show:
- Intent accuracy from actual labelled evaluations
- Entity extraction metrics
- Error type distribution
- Recent reviewed failures
- Feedback queue
- Model version
- Model readiness
- Dataset version
- Retraining candidates
- Deployment history

Metrics must use actual stored evidence.

Do not invent accuracy percentages.

# 13. CONVERSATION UI

Add:
- Compact feedback controls
- Clarification choices
- Correction acknowledgement
- Useful recovery suggestions
- Clear unknown-data messages
- Optional conversation summary

Preserve the current chat-first design.

Do not clutter the passenger screen with diagnostics.

# 14. TESTING

Create at least 250 recovery and failure scenarios.

Include:
- Wrong intent correction
- Wrong destination correction
- Wrong date correction
- Wrong bus selection
- Missing fare
- Missing platform
- No AC service
- No direct route
- Model unavailable
- Database unavailable
- Ambiguous station
- Ambiguous selected service
- Context expired
- Conflicting preferences
- Unsupported enquiry
- Out-of-scope enquiry
- Feedback storage
- Review approval
- Training dataset export
- Model rollback

Test real database integration.

Do not rely solely on mocked NLP outputs.

# 15. PERFORMANCE

Measure:
- Repair detection latency
- Clarification latency
- No-result diagnostic query overhead
- Feedback-write latency
- Overall response latency

Avoid expensive repeated database searches for every normal enquiry.

Only invoke diagnostics when necessary.

# 16. SECURITY AND PRIVACY

Ensure:
- Admin-only review access
- Operator-scoped data access
- Safe text storage
- Configurable retention
- Session isolation
- No cross-user context leakage
- No external telemetry
- No automatic model deployment

Do not store unnecessary personal details.

# 17. END-TO-END ACCEPTANCE

Using labelled demo data, test:

1. Passenger asks for next bus to Nellore.
2. Assistant returns available services.
3. Passenger says "No, I meant the last bus."
4. System changes intent but retains Nellore.
5. Passenger selects a service.
6. Passenger asks for the fare.
7. System uses the selected journey.
8. Passenger says "That's the wrong bus."
9. System asks which service they intended.
10. Passenger selects the correct one.
11. Passenger asks for platform.
12. System returns known platform or explains it is not confirmed.
13. Passenger marks an answer as incorrect.
14. Feedback appears in the local admin review queue.
15. Reviewer labels the failure.
16. Approved feedback becomes eligible for a future training run.

Verify every context transition and backend query.

# 18. DELIVERABLES

Deliver:
1. Conversation repair engine.
2. Uncertainty-based clarification.
3. No-result diagnostic engine.
4. Passenger feedback controls.
5. Admin review queue.
6. Error taxonomy.
7. Reviewed training feedback export.
8. Offline retraining workflow.
9. Model comparison and rollback.
10. Quality/drift reports.
11. UI integration.
12. Automated regression tests.
13. Phase 5D completion report.

Run backend and frontend tests.

Report actual pass/fail counts and performance results.

Do not declare completion based on generated documentation alone.

Do not begin Phase 5E or speech development.

Start implementation immediately.