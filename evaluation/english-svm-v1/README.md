# Frozen held-out English SVM evaluation v1

This is an evaluation-only artifact outside the training directory. Do not copy its questions into training, threshold tuning, model selection or rule tuning. The 200 questions were newly authored and frozen before obtaining predictions: three questions for each of 60 canonical intents plus 20 out-of-scope questions. These are agent-authored labels, not human-adjudicated passenger utterances or a field study.

`manifest.json` records the immutable holdout checksum and protocol. `authored.txt` is the original authoring source; `holdout.jsonl` is the scored version. No questions were changed after seeing predictions. The evaluator compares both pre-existing artifacts rather than using the scores to promote or choose a deployed model.

Reproduce from the repository root using the existing local English environment:

```powershell
.\.venv-english\Scripts\python.exe scripts/evaluate_svm_holdout.py
```

The script blocks Python socket egress. It loads only the two local scikit-learn SVM artifacts, never speech components or TensorFlow. It does not alter model bytes, training data, deployment approvals or classifier thresholds. It fits a character-ngram representation solely for lexical-overlap auditing; it does not fit either intent model.

Before loading either SVM, exact-normalized overlap and character-ngram cosine similarity are checked against all local `training/datasets/**/*.jsonl` text, the taxonomy examples and NLP rule phrases. Rows with exact overlap or similarity >=0.85 are excluded from primary scores. One out-of-scope question was an exact match and was excluded. All 180 single-intent questions and 19 out-of-scope questions remained eligible. Source file checksums, nearest-match text and source, audit decisions, model hashes and every prediction are in `results.json`.

The 44-label pilot includes a label outside the current 60-intent taxonomy. Confusion matrices retain such predictions as additional columns/rows rather than dropping them; primary accuracy counts them as errors. Macro F1 is computed over the 60 canonical labels. Legacy label aliases are normalized using the existing taxonomy mapping. The same eligible questions are used for both candidates.

Both classifiers use forced-choice `predict`. Out-of-scope false acceptance therefore measures this raw model interface, not the guarded runtime pipeline. No new abstention threshold was fitted or selected on this set. The runtime approval gate remains unchanged.

The Wilson accuracy intervals in REPORT.md assume independent Bernoulli outcomes; with three coauthored questions per class they are descriptive and do not establish performance on real passengers. Character similarity cannot rule out shared semantic templates or historical external exposure. A larger independently human-labelled corpus and a separately calibrated rejection mechanism remain necessary before deployment approval.
