# Frozen English SVM held-out evaluation

New agent-authored English questions; not human-reviewed or an independent field study. No retraining, threshold tuning or promotion.

Overlap audit: 1 exact and 0 near-overlap rows excluded from primary scores; character ngram similarity cutoff 0.85.

## pilot-v2

- Classes: 44; scored questions: 180.
- Accuracy: 48/180 (26.67%); Wilson 95% interval 20.74%–33.57%.
- Macro F1 across 60 canonical labels: 0.2322.
- Out-of-scope false accepts: 19/19 with forced-choice predict; no rejection mechanism tested.
- Warm prediction median 1.033 ms, p95 1.555 ms.
- Full per-class metrics, confusion matrix, source hashes and all predictions: results.json.

## grouped-60-v1

- Classes: 60; scored questions: 180.
- Accuracy: 117/180 (65.00%); Wilson 95% interval 57.78%–71.59%.
- Macro F1 across 60 canonical labels: 0.6408.
- Out-of-scope false accepts: 19/19 with forced-choice predict; no rejection mechanism tested.
- Warm prediction median 1.034 ms, p95 1.580 ms.
- Full per-class metrics, confusion matrix, source hashes and all predictions: results.json.

Only three authored samples per class before exclusions; class-level scores are noisy. Related intent definitions share vocabulary. The lexical audit cannot rule out semantic template exposure. These results do not justify activating either candidate.
