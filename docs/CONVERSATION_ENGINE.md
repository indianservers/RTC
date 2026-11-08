# Conversation engine

RTCNLPEngine remains the single text/dialogue implementation. RTCConversationEngine is a compatibility alias, and EnglishInferenceService is a facade exposing classify_intent, classify_multiple_intents, extract_entities, identify_dialogue_act, interpret_query, process_conversation and reset_session. Existing text APIs delegate interpretation/message/reset to the facade; no duplicate conversation tables or query engine were created.

Facts continue through the existing RTCEnquiryEngine and local database. DB templates label DEMO data and keep unknown/stale inventory and platforms explicit. Learned candidates are not promoted, so deterministic DB rules remain active. The English classifier adapter can load only a local approved descriptor with compatible labels and checksum; its fitted SVM cache is shared across instances and guarded by a process lock. Input length is bounded at 2000 characters. No inference download code exists.

Fixed ordinal selection so 'the first one' updates the selected result rather than accidentally running FIRST_BUS. Feature words in 'cheapest AC sleeper' remain constraints on CHEAPEST_BUS, unless the phrasing explicitly requests another question. Added three-turn composed database-request tests across routes and action combinations. Explicit selection is acknowledged without an unnecessary query; subsequent fare/status queries reuse its service. Missing morning departures produce no-results/clarification rather than an invented fare.

Existing 240 parameterized route/dialogue cases include 20 initial single-turn checks; the other 220 have follow-ups. Added 300 composed three-turn cases, giving at least 520 cases with follow-up turns. These are synthetic parameterized regression scenarios, not 520 independently reviewed natural conversations. No original assertion was weakened. New test assumptions that every command must execute SQL and every morning route must have a fare were corrected to verify selection acknowledgements and unavailable data explicitly.

Remaining: complete measured entity F1, representative dialogue/answer correctness, stronger same-session concurrency control, broad multi-intent decomposition quality, complete operational handler coverage and multilingual model readiness. A pass count alone is not an end-to-end passenger accuracy estimate.


Four concurrent independent SQLite conversations were executed and preserved distinct session IDs/destinations while applying separate filters. Same-session concurrent-update serialization is still not guaranteed.
