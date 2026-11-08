# Selective 60-intent SVM training snapshot v2

This directory contains separate, versioned training and validation data for a text-only candidate. It is synthetic and agent-authored, **not human-reviewed**. Do not promote its labels to REVIEWED. No speech component or audio model is used.

- Train: 653 single-intent records spanning all 60 labels, plus 118 out-of-scope records.
- Validation: 180 single-intent records (three per label), plus 60 out-of-scope records.
- Fresh test: a separately frozen 240-question set in `evaluation/english-svm-v2`; it was not opened by the trainer.

The new authoring banks are separate for each split. Only SINGLE_INTENT records from the earlier `2c-v1/train.jsonl` split were additionally admitted for training. Earlier validation/challenge/evaluation questions and simulation benchmarks are forbidden training/validation sources. ASR-style data was not imported. There are no augmented sibling questions randomly distributed between splits.

`protocol.json` fixed the feature choices, C grid, validation objective, rejection threshold grid and maximum validation OOS false-accept rate before fitting. `manifest.json` records hashes and distributions. `leakage-audit.json` records nearest lexical matches and every exclusion. Nine proposed train records were excluded: normalized duplicates or overlap with forbidden material. Training and validation retain all 60 labels. No validation or fresh-test questions were removed. Authored family IDs are split-specific; normalized cross-split duplicates are prohibited and character-ngram similarity >=0.85 is quarantined/excluded by the preparation step.

Original source-bank files are authoring artifacts. Train only from the checksummed JSONL snapshots. The earlier evaluation set remains evaluation-only; it was used solely as a forbidden-overlap reference, never as positive or negative training data. Lexical audits cannot prove semantic independence, and all banks were coauthored in the same work session.

From the repository root, with the existing English environment:

```powershell
# These creation commands refuse to overwrite frozen versions.
.\.venv-english\Scripts\python.exe scripts/prepare_selective_svm.py
.\.venv-english\Scripts\python.exe scripts/train_selective_svm.py
# Only after checkpoint and validation thresholds are frozen:
.\.venv-english\Scripts\python.exe scripts/evaluate_selective_svm.py
```

This version has already been built and evaluated. Re-running creation commands should report that the version exists. Reproduction in a clean workspace requires the source banks, original 2c-v1 train split, forbidden reference files and protocol. Future experiments should use a new version and a fresh test, not edit this corpus or tune against its test outcomes.

The model uses train-only word and character TF-IDF features, a 60-class LinearSVC and a binary domain LinearSVC. C and thresholds are selected using validation alone; train+validation are not pooled for a final refit. Selected C=0.5; domain acceptance margin >=0.5, top intent margin >=-1.0 and top-two gap >=0.0. The grid selected no extra gap/top-margin rejection beyond the domain gate in this version. Decision margins are not probabilities. Validation permitted at most 5% OOS false accepts; this is an empirical selection constraint, not a certified population bound.

The checkpoint, label map, threshold search, validation predictions, descriptor and dependency versions are under `models/english/nlp/selective-60-v2`. That folder remains subject to the repository's existing model-file ignore rules. No runtime dependency file, active model registry entry, prior model or prior split was changed.
