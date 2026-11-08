# RTC OFFLINE AI — ENGLISH MODEL ACCURACY RECOVERY
## Improve Dataset, Retrain SVM and TensorFlow, Evaluate Before Promotion

Continue in the EXISTING RTC repository.

The independent audit confirms:

- Active model: DETERMINISTIC_RULES.
- SVM 60-intent validation accuracy: 23.68%, macro-F1: 0.1775.
- TextCNN validation accuracy: 3.95%, macro-F1: 0.0147.
- Actual eligible classifier dataset: 234 training, 76 validation, 67 synthetic challenge examples.
- No human-reviewed independent test set.
- Both statistical checkpoints load and run.
- 1,459 backend tests passed.

The priority is to improve actual English NLP accuracy, not to build more UI.

## Task 1 — Investigate model failure

Inspect actual training and validation examples.

Identify:
- Incorrect intent labels
- Missing classes
- Unbalanced intent distribution
- Repetitive templates
- Similar intents with overlapping definitions
- Train/validation vocabulary mismatch
- Preprocessing inconsistencies
- Underfitting and overfitting
- Out-of-scope classification weaknesses

Produce per-intent error analysis.

Do not assume insufficient dataset size is the only cause.

## Task 2 — Improve the training corpus

Use the existing 60-intent taxonomy.

First establish at least 30–50 genuinely varied, correctly labelled examples per intent, with a reviewed representative validation set.

Then progressively expand toward 200+ examples per intent.

Include:
- Natural English
- Indian English
- Short questions
- Incomplete enquiries
- Alternative sentence structures
- Negation and corrections
- Similar-intent contrastive examples
- Contextual follow-ups
- Out-of-scope examples
- Multiple enquiry intents

Use database station aliases and bus categories.

Avoid simply changing destination names in otherwise identical templates.

Separate synthetic examples from human-reviewed examples.

Do not fabricate human-review status.

## Task 3 — Fix dataset leakage and evaluation

Group related paraphrases and template families.

Prevent related examples from crossing training and validation splits.

Create:
- Training split
- Validation split
- Synthetic challenge split
- A separate independently reviewed test set when available

Keep all evaluation reproducible.

Report actual record counts and coverage.

## Task 4 — Retrain SVM

Train:
- Word n-gram TF-IDF
- Character n-gram TF-IDF
- Linear SVM

Tune preprocessing and hyperparameters using validation data.

Evaluate macro-F1 and per-intent confusion.

Save a new versioned candidate model.

Do not overwrite grouped-60-v1.

## Task 5 — Retrain TensorFlow TextCNN

Review:
- TextVectorization vocabulary
- Sequence lengths
- Embedding configuration
- CNN filters
- Learning rate
- Class imbalance
- Training and validation loss
- Early stopping

Verify that all 60 output labels match the registry.

Train and evaluate a new versioned candidate.

Do not assume TensorFlow must outperform SVM.

## Task 6 — Dialogue-aware intent handling

Do not force these into unrelated standalone enquiry labels:

"What about tomorrow?"
"No, Tirumala."
"Second one."
"How much?"
"Same bus."

Use dialogue acts, current conversation state and contextual intent resolution.

Keep multi-intent understanding separate from ordinary single-label classification where necessary.

## Task 7 — Evaluate the models

Compare:
- Existing deterministic rules
- Existing grouped SVM
- New SVM
- Existing TextCNN
- New TextCNN

Use identical evaluation data.

Report:
- Accuracy
- Macro-F1
- Per-intent F1
- Confusion matrix
- Rejection/clarification behaviour
- Inference latency
- Memory consumption
- End-to-end conversation correctness

Report results separately for synthetic and human-reviewed test data.

## Task 8 — Preserve production safety

Do not automatically activate new models.

Keep DETERMINISTIC_RULES active until a candidate:
- Passes the agreed release evaluation.
- Demonstrates meaningful improvement.
- Has validated uncertainty handling.
- Passes conversation regression tests.
- Is explicitly approved for promotion.

Do not lower existing release gates merely to report completion.

## Task 9 — Run regression tests

Run:
- Dataset validation
- Model evaluation
- Dialogue integration tests
- Backend tests
- Ruff
- Mypy
- Offline inference tests

Record actual results.

## Final deliverables

1. Dataset error analysis.
2. Expanded validated English training dataset.
3. Retrained SVM candidate.
4. Retrained TensorFlow candidate.
5. Comparative evaluation.
6. Updated model registry.
7. Intent confusion report.
8. Conversation integration evaluation.
9. Training and test documentation.
10. Production promotion recommendation.

Do not download MuRIL, IndicConformer or additional speech models.

Do not change the UI.

Start with the dataset and error analysis, then execute training and evaluation.

Report the actual measured results and remaining limitations. Do not claim production accuracy without independent evidence.