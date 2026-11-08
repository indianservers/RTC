# Fresh held-out selective SVM evaluation

New agent-authored English questions, frozen before training. Not a human-reviewed or field-collected benchmark. Neither the old evaluation set nor fresh-test results were used to train or calibrate this candidate.

## grouped-60-v1

- Closed-set intent accuracy: 89/180 (49.44%); macro F1 0.4764.
- In-scope accepted: 180/180 (100.00%). Accepted-ID accuracy: 49.44%.
- Correctly accepted ID / all ID: 89/180 (49.44%). Selective macro F1 (rejections count against recall): 0.4764.
- OOS rejected: 0/60 (0.00%); false accepts 60 (100.00%).
- Overall decision accuracy, including rejected OOS and counting rejected ID as errors: 37.08%.
- Warm prediction median 2.004 ms, p95 4.157 ms.

## selective-60-v2

- Closed-set intent accuracy: 147/180 (81.67%); macro F1 0.8148.
- In-scope accepted: 171/180 (95.00%). Accepted-ID accuracy: 80.70%.
- Correctly accepted ID / all ID: 138/180 (76.67%). Selective macro F1 (rejections count against recall): 0.7733.
- OOS rejected: 58/60 (96.67%); false accepts 2 (3.33%).
- Overall decision accuracy, including rejected OOS and counting rejected ID as errors: 81.67%.
- Warm prediction median 1.782 ms, p95 2.606 ms.

Per-class metrics, confusion matrices, hashes, margins and every raw/selective prediction are in results.json. Rejection thresholds were selected only on validation. Only three questions per intent and 60 OOS questions were tested; results do not establish field accuracy or certify a population false-acceptance limit. No checkpoint or approval registry entry was changed by evaluation.
