# Phase 2 final report

PHASE 2 INCOMPLETE. No production readiness or Phase 3 readiness is claimed.

Executed group-based dataset preparation and actual 60-label SVM/TextCNN training, followed by identical synthetic-holdout comparison. Preserved previous datasets, model versions, migrations and enquiry code. Candidate artifacts: models/english/nlp/grouped-60-v1/{svm.joblib,textcnn.keras,label_map.json,training_history.json,evaluation.json,comparison.json}. Dataset snapshot: training/datasets/splits/2c-v1/manifest.json. Registry: config/model_registry.yaml. Requirements matrix: docs/phase2_requirements.json.

Raw splits: 234 training, 76 validation, 139 synthetic challenge; zero independent test examples. Single-label comparison uses 234/76/67 examples respectively. Validation macro-F1: SVM 0.177540; TextCNN 0.014697; deterministic rule-only 0.169444. Synthetic-challenge macro-F1: SVM 0.212619; TextCNN 0.071667; rule-only 0.155000. SVM is a development winner only. No model reaches the 0.95 target or receives approval. Training accuracy is not used as promotion evidence. No executable confidence threshold passed the validation policy.

Warm median inference: SVM 1.3083 ms, TextCNN 7.0547 ms on the available CPU. Fixed-clock 30-run local text benchmark: median 32.4121 ms, P95 42.4970 ms with 100 fictional demo services. This excludes audio and is not an accuracy certificate. Full measurements, per-class errors and limitations: docs/MODEL_COMPARISON.md and models/benchmarks/phase2-final-end-to-end.json.

The existing deterministic DB fallback stays active. Ordinal-selection and feature-composition behavior improved; shared local model-cache and health checks added. None of these changes lets model output create SQL or fabricate service facts. No UI, cloud inference or Phase 3 audio orchestration was introduced.

Unresolved major requirements: sufficient reviewed diverse data, an independent test set, reliable model accuracy, calibrated production uncertainty, representative entity/dialogue/end-to-end accuracy, complete operational backend coverage, PostgreSQL execution and OS-enforced isolation. Phase 3 can use the existing interfaces experimentally only; production advancement is not recommended.

Reproduce: python training/preparation/prepare.py creates the immutable dataset version only when absent. With PYTHONPATH=backend and the English environment, run training/english/train.py --manifest training/datasets/splits/2c-v1/manifest.json --version <new-version> --tensorflow --epochs 30. Training refuses overwriting an existing checkpoint. training/english/compare.py currently targets grouped-60-v1. Never replace the independent test with the synthetic challenge split.


Final checks: 796 tests passed with one installed Starlette/HTTPX deprecation warning. Ruff passed. Mypy passed for application, preparation, generation, validation and English training/evaluation code. Dataset/taxonomy validation and SQLite integrity/foreign-key checks passed. PostgreSQL and OS-level network isolation were not executed.

The production compositional parser achieved 0.500 exact match on 16 unreviewed synthetic multi-intent questions; this separate diagnostic is not an answer-correctness estimate. Full cases: models/benchmarks/phase2-final-composition.json. It still needs substantial improvement before production.
