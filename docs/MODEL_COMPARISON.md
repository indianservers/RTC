# Model comparison — Phase 2 final

All evaluated holdouts are synthetic and unreviewed. No independent real-world test set exists. The production exact-taxonomy-example lookup was excluded from the rule-only baseline because it can access these seed questions. The same single-label subsets were used for every compared model.

## train

- svm: 234 examples; accuracy 1.000000; macro precision 1.000000; recall 1.000000; F1 1.000000. Full weighted/per-intent metrics and confusion matrix: models/english/nlp/grouped-60-v1/comparison.json.
- textcnn: 234 examples; accuracy 0.995726; macro precision 0.996667; recall 0.994444; F1 0.994815. Full weighted/per-intent metrics and confusion matrix: models/english/nlp/grouped-60-v1/comparison.json.
- deterministic_rule_only: 234 examples; accuracy 0.179487; macro precision 0.333552; recall 0.171944; F1 0.205082. Full weighted/per-intent metrics and confusion matrix: models/english/nlp/grouped-60-v1/comparison.json.
## validation

- svm: 76 examples; accuracy 0.236842; macro precision 0.159722; recall 0.233333; F1 0.177540. Full weighted/per-intent metrics and confusion matrix: models/english/nlp/grouped-60-v1/comparison.json.
- textcnn: 76 examples; accuracy 0.039474; macro precision 0.009259; recall 0.041667; F1 0.014697. Full weighted/per-intent metrics and confusion matrix: models/english/nlp/grouped-60-v1/comparison.json.
- deterministic_rule_only: 76 examples; accuracy 0.184211; macro precision 0.166667; recall 0.175000; F1 0.169444. Full weighted/per-intent metrics and confusion matrix: models/english/nlp/grouped-60-v1/comparison.json.
## synthetic_challenge

- svm: 67 examples; accuracy 0.298507; macro precision 0.188889; recall 0.266667; F1 0.212619. Full weighted/per-intent metrics and confusion matrix: models/english/nlp/grouped-60-v1/comparison.json.
- textcnn: 67 examples; accuracy 0.089552; macro precision 0.066667; recall 0.083333; F1 0.071667. Full weighted/per-intent metrics and confusion matrix: models/english/nlp/grouped-60-v1/comparison.json.
- deterministic_rule_only: 67 examples; accuracy 0.164179; macro precision 0.150000; recall 0.166667; F1 0.155000. Full weighted/per-intent metrics and confusion matrix: models/english/nlp/grouped-60-v1/comparison.json.

## Selection and calibration

SVM is the development winner by validation macro-F1. Neither model is approved or active. No threshold achieved at least 95% validation precision with ten accepted validation cases, so no executable high-confidence threshold was installed. SVM decision margins remain margins, not probabilities. Medium/low thresholds and production out-of-scope calibration remain incomplete.

Rule-only multi-intent exact match: 0.3125 on 16 synthetic questions. Rule-only out-of-scope rejection: 0.9500 on 20 synthetic questions. These are not independent safety estimates.

## Error analysis

Both learned models fit the tiny training set strongly but fail on different authored question families. TextCNN training accuracy is approximately 99.57% while validation accuracy is approximately 3.95%; this is severe overfitting, not evidence that a neural model is production-ready. SVM validation accuracy is approximately 23.68%. Only five authored examples per intent are available, so diverse reviewed data is the primary unmet need.

- SVM validation confusion: SLEEPER_AVAILABILITY → ALIGHTING_POINT: 2.
- SVM validation confusion: SERVICE_FREQUENCY → BUSES_OPERATING_TODAY: 2.
- SVM validation confusion: SERVICE_DISRUPTION → SERVICE_NUMBER_LOOKUP: 2.
- SVM validation confusion: PLATFORM_CHANGE → BUS_PLATFORM: 2.
- SVM validation confusion: NON_AC_BUS_AVAILABILITY → DIRECT_BUS: 2.
- SVM validation confusion: LUGGAGE_RULES → LOST_PROPERTY: 2.
- SVM validation confusion: LAST_BUS → NEXT_BUS: 2.
- SVM validation confusion: INTERMEDIATE_STOP → ALIGHTING_POINT: 2.
- SVM validation confusion: FASTEST_BUS → BUS_DEPARTED_STATUS: 2.
- SVM validation confusion: CHEAPEST_BUS → GET_FARE: 2.

## Performance

{
  "warm": {
    "svm": {
      "p50_ms": 1.3083000003462075,
      "p95_ms": 1.6961000001174398,
      "bytes": 2778792
    },
    "textcnn": {
      "p50_ms": 7.054700000480807,
      "p95_ms": 9.550100000524253,
      "bytes": 15598461
    }
  },
  "cold_load_seconds": {
    "svm": 0.10649469999952998,
    "textcnn": 0.2485725000005914
  },
  "peak_process_memory_bytes": 402743296
}

Peak memory is cumulative process memory for the combined benchmark. Models were loaded and exercised with Python socket audit blocking; TensorFlow import startup and native-library OS isolation are not certified.