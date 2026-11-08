# Improved text-only SVM and validation-calibrated rejection

Execution report — 8 November 2026 (Asia/Kolkata). The requested candidate training, rejection calibration and fresh held-out evaluation are complete. The candidate is not activated.

## Data separation and leakage controls

- Training: 653 single-intent examples over 60 labels and 118 OOS examples. New banks were supplemented only with SINGLE_INTENT rows from the previous 2c-v1 train split.
- Validation: 180 new single-intent questions (three per label) and 60 OOS questions. This split alone selected C and rejection thresholds; it was never merged into training.
- Fresh test: 180 new single-intent questions and 60 OOS questions, checksummed before fitting. The training command never opens its question file. A separate one-way evaluator scores only the frozen artifact and thresholds.
- Nine proposed training records were excluded by normalized duplicate / forbidden-overlap checks. No validation or fresh-test question was excluded. All splits cover all 60 labels. Authored families and normalized exact duplicates do not cross splits; character-ngram similarity >=0.85 is rejected by the pre-training preparation audit.
- Earlier evaluation questions, prior validation/challenge splits and simulation benchmarks were forbidden train/validation sources. They were read only as overlap-audit references. Their questions and expected results were not changed or copied into model training.
- Source labels are synthetic agent-authored and unreviewed. Shared authoring and related intent language limit independence; lexical checks do not establish semantic or field independence. No data was labelled REVIEWED.

## Model and validation selection

Train-only word (1,2) and char_wb (3,5) TF-IDF features feed a 60-class LinearSVC and a binary in-scope/OOS LinearSVC. Intent C values 0.5, 2 and 8 and a fixed rejection grid were declared in protocol.json before training. The validation objective maximized correctly accepted ID questions while limiting empirical OOS false accepts to 5%; ties favored fewer wrongly accepted ID questions, stronger closed-set macro F1 and deterministic parameter preferences.

Selected intent C=0.5; binary domain C=1. Thresholds: {'domain': 0.5, 'margin': -1.0, 'gap': 0.0}. In this version the selected top-margin/gap bounds add no effective ambiguity rejection beyond the domain gate; this is reported explicitly rather than implying calibrated label confidence.

- Validation forced-choice accuracy: 155/180 (86.11%); accepted ID 174/180, of which 150 correct. Validation OOS false accepts: 3/60 (5%).
- Training/calibration duration recorded by the trainer: 0.953 seconds, excluding corpus preparation and later evaluation.
- The wrapper returns KNOWN with one intent, OUT_OF_SCOPE with no intent, or CLARIFICATION_REQUIRED with no intent. Scores are SVM decision margins, not probabilities.
- Checkpoint, label map, validation search over 420 configurations, validation predictions, descriptor and dependency versions are in models/english/nlp/selective-60-v2. Existing checkpoints were not overwritten.

## Fresh held-out results

- Baseline grouped-60-v1: 89/180 ID questions correct (49.44%), macro F1 0.4764. It accepted all 60 OOS questions because it is forced-choice.
- New selective-60-v2 before rejection: 147/180 correct (81.67%), macro F1 0.8148. The paired comparison fixed 60 baseline errors and introduced 2 new errors.
- Accepted ID: 171/180 (95.00%). Correct among accepted: 138/171 (80.70%). Correct-acceptance coverage: 138/180 (76.67%). Nine valid bus questions were rejected; they count as missed answers.
- Selective macro F1, counting ID rejections against class recall: 0.7733.
- OOS rejected: 58/60 (96.67%); false accepts: 2/60 (3.33%). Approximate Wilson 95% interval for OOS FAR: 0.92% to 11.36%; the test does not certify a population FAR below 5%.
- With rejected inputs treated as positive OOS detections: precision 86.57%, recall 96.67%, F1 0.9134. The nine rejected ID inputs reduce this precision.
- Overall decision accuracy (correctly accepted ID + rejected OOS, with rejected ID counted as errors): 81.67%.
- Warm candidate prediction median 1.782 ms; p95 2.606 ms. Process RSS sampled during evaluation: 159,928,320 bytes; this is whole evaluator memory, not an incremental model-only footprint. Serialized artifact: 7,205,683 bytes.

The two fresh OOS false accepts were a bus-chassis warranty/purchase question classified OPERATOR_CONTACT and an electrical fuse question classified BUS_CANCELLATION. These failures were inspected for reporting only. No training text, hyperparameter, threshold or fresh-test expectation was changed after seeing test predictions. Earlier evaluation accuracy (65% on a different set) is not the baseline for the new test; the same-set baseline here is 49.44%.

Per-class precision/recall/F1, rejection-aware confusion matrices, all raw and selective predictions, score margins, hashes and uncertainty intervals are in evaluation/english-svm-v2/results.json. REPORT.md gives a concise view.

## Runtime integration, checks and scope

- EnglishIntentModel retains all existing approval, registry, checksum and label-map gates. A compatible approved selective bundle dispatches predict_selective; it does not fall back to forced-choice after rejection.
- The inference facade preserves OUT_OF_SCOPE. If the conversation fallback invokes an approved model and it rejects or is uncertain, no enquiry is executed and prior context is retained. Explicit short context updates remain ahead of standalone classification. Existing deterministic rules still run first; raw-model test metrics are not end-to-end rules-plus-context chat accuracy.
- The new model is a CANDIDATE with approved=false and independent_evaluation=false (no human-adjudicated independent field evaluation). Its descriptor is separate from the active registry; no runtime deployment entry was added or modified. The checkpoint does not meet the existing human-review, macro-F1 or OS-isolation approval requirements.
- Full backend regression: 1477 passed, 0 failures, 0 errors; JUnit duration 221.156 seconds. Includes adapter tests, OOS no-database/context-preservation tests, explicit corrections, legacy cache tests, lifecycle tests, corpus/hash checks and score-boundary/monotonicity checks.
- Ruff passed for backend and the four new scripts. Mypy passed for 47 app source files with --ignore-missing-imports. The existing Starlette/httpx deprecation warning remains.
- Reloading the saved artifact reproduced every frozen validation prediction exactly. Candidate CLI smoke returned AC_BUS_AVAILABILITY for a bus-AC question and OUT_OF_SCOPE for an investment question without modifying deployment.
- Training, evaluation and candidate CLI use the existing English virtual environment with Python socket egress denied. No network downloads, dependency changes, TensorFlow use, voice-model loading, speech changes, UI changes or database/schema changes were made. OS-level isolation was not exercised.

## Reproduction and files

Use the repository-root commands in README and training/datasets/selective-60-v2/README.md. Creation commands refuse to overwrite immutable versions. For candidate inspection: `.\.venv-english\Scripts\python.exe scripts/predict_selective_svm.py "your English text"`. Normal `python -m app.cli.chat` continues to use its existing approved-model/rule policy. Existing model directories remain ignored by Git; preserve the candidate folder and dependency metadata when copying the project.

New training sources/snapshots: training/datasets/selective-60-v2. Fresh evaluation: evaluation/english-svm-v2. New model bundle: models/english/nlp/selective-60-v2. Pure score wrapper: backend/app/nlp/selective_svm.py. Machine-readable summary: docs/selective-svm-report.json. Regression evidence: docs/selective-svm-tests.xml.

The requested experimental improvement is delivered; production activation remains out of scope. Real passenger data, independently human-adjudicated labels, broader ambiguity/short-context evaluation and a larger OOS challenge remain necessary before claiming high field accuracy.
