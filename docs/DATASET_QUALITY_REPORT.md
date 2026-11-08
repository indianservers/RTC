# Dataset quality and preparation

PHASE 2 INCOMPLETE. Source: 449 schema-valid SYNTHETIC/PENDING_HUMAN_REVIEW candidates, including 300 reused Phase 2A questions. No human-reviewed examples or independently collected test set exists. Original generation quantity and diversity targets remain unmet.

Frozen snapshot: training/datasets/splits/2c-v1/manifest.json. Counts: 234 train, 76 validation, 139 synthetic challenge. Of the challenge records, 67 are suitable single-label classification questions; the remaining 72 include multi-intent, context, ambiguous, out-of-scope and constraint records. They were not forced into a single-label classifier.

Template families, parent/source examples and all normalized text near-duplicates at SequenceMatcher >=0.90 were joined transitively before assignment. Family indexes 0/1/2 train, 3 validation, 4 challenge define the deterministic policy; merged groups take the strongest holdout. No random individual-row split was used. Split seed metadata is 42, but assignment is deterministic by family rather than an RNG sample. Every group is checked to occur in only one split. Near-duplicate grouping is heuristic and cannot prove paraphrase independence.

JSONL snapshots have read-only file attributes and SHA-256 manifests. Training verifies checksums and rejects altered snapshots or crossing groups. This is not tamper-proof archival storage. No ambiguous labels were silently relabelled. More diverse independent questions are required before reliable model selection or calibration. Existing models and source datasets remain preserved.

Full earlier audit: training/reports/PHASE_2B_DATASET_REPORT.md. Existing schema, metadata, entity spans and real-ID checks are reused rather than reimplemented.
