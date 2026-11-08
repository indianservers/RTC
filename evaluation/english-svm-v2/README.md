# Fresh selective-SVM test v2

This fresh test was authored and checksummed before training: 180 single-intent English questions (three per canonical label) and 60 out-of-scope questions. It is independent of the training/validation files at the lexical/family level, but is agent-authored and not independently human-adjudicated or field-collected.

`manifest.json` records the pre-training checksum and protocol linkage. `holdout.jsonl` is frozen. `eligibility.json` records the pre-training overlap audit; all 240 questions were eligible. `results.json` and `REPORT.md` compare the unchanged grouped-60-v1 model with selective-60-v2 on identical questions.

Do not use these questions, their answers, false-accept cases or prediction errors for training, feature selection, threshold tuning or rule tuning. No model or threshold was modified in response to these results. Use a new version and a fresh test for future development. Earlier `english-svm-v1` questions remain protected and were not used for training or validation.

The evaluator refuses to overwrite results. Its job is to read frozen models and questions, record metrics and verify model/registry checksums remain unchanged. It never fits a model. Python socket egress is blocked; OS-level isolation was not tested.

Read the metrics carefully:

- Closed-set accuracy measures the forced best intent on in-scope questions before rejection.
- ID acceptance coverage is the fraction of valid bus questions for which an answer is allowed.
- Accepted-ID accuracy excludes rejected bus questions; correct-acceptance coverage also counts those rejections as missed answers.
- OOS false acceptance is the fraction of out-of-scope questions incorrectly allowed through.
- Selective macro F1 counts rejected ID questions as false negatives. Confusion matrices retain the rejection column.

The candidate reached 81.67% closed-set accuracy, versus 49.44% for the old 60-label baseline on this new test. It accepted 171/180 ID questions; 138 were correctly classified, giving 80.70% accepted-ID accuracy and 76.67% correct-acceptance coverage. It rejected 58/60 OOS questions. The 2/60 false-accept rate has an approximate Wilson 95% interval of 0.92% to 11.36%, so this test does not certify a population FAR below 5%. Only three questions per intent were tested; class-level estimates are noisy.

Raw model rejection does not by itself measure the complete rules-first conversation pipeline. Runtime rejection dispatch is covered by separate adapter/dialogue tests. The candidate was not activated; existing approval requirements still apply.
