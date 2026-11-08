# English model accuracy recovery v3

The new SVM and TextCNN have been trained and evaluated locally. **Keep DETERMINISTIC_RULES active. Neither candidate is approved for production.** The user confirmed that no independently human-reviewed test set is available. All expanded examples and all reported holdouts are synthetic and pending human review.

## Investigation

`dataset-audit.json` contains all 60 intent definitions, original training/validation support, baseline per-intent F1 and confusion counts. The original eligible corpus has 234 training, 76 validation and 67 single-intent synthetic challenge rows. All 60 training classes exist; the primary problem is not missing output classes. There are only three or four training examples per class, and 20.13% of validation word tokens do not appear in training.

Other causes matter:

- Closely related intent boundaries share vocabulary: scheduled arrival versus operational ETA; route passing versus an actual halt; one-bus travel versus connecting services; fare lookup versus fare comparison; cancellation policy versus an actual trip cancellation. Negation and contrast can reverse the intended class.
- Raw generated-record counts overstated effective classifier support. Contextual, multi-intent and out-of-scope rows cannot all become ordinary 60-way training targets, and changing place names does not add a new sentence family.
- Original training metadata claimed NFKC/casefold preprocessing while passing raw strings to the estimators. Recovery snapshots store the actual normalized text used by both training and evaluation. NFKC + casefold + whitespace collapse is an explicit candidate input contract.
- Original TextCNN training loss fell from about 4.098 to 0.544 while validation loss stayed near 4.03–4.10, close to the 60-class random-loss scale. That is poor generalization despite fitting training data. The original SVM also fits a tiny corpus much better than it generalizes.
- The original closed-set classifiers have no effective out-of-scope gate; every unrelated question can be forced into a bus label. A high softmax score is not automatically calibrated confidence.

The historical 23.68% SVM / 3.95% CNN validation figures refer to the original 76-row split. They must not be subtracted from scores on a different holdout to claim a controlled improvement. Comparisons below use identical later frozen synthetic sets for every model.

## Expanded corpus and leakage controls

`training/datasets/recovery-60-v3` contains **2,209 training records: 2,091 information-intent questions and 118 OOS questions**. Every intent has **34–35 training examples**. The new authored bank supplies 24 distinct sentence constructions per intent in addition to the existing eligible train-only corpus. It includes short, incomplete and polite/Indian-English forms, explicit contrasts and negation. It is not produced by multiplying destinations or adding superficial prefixes.

The validation split has **240 rows: 180 ID / 60 OOS**; synthetic challenge has the same counts. Each covers all 60 labels, only three questions per intent. These are the existing selective-v2 frozen validation and challenge sets. The challenge has been exposed in earlier development and is a **synthetic regression set, not a new blind or independent test**. No challenge result was used to choose model hyperparameters or thresholds. No further fitting was performed after challenge predictions were inspected.

Original families are retained; new authored families and their DB-entity substitutions remain train-only. Exact text/group disjointness is checked. Character 3–5-gram cosine similarity >=0.85 against validation/challenge excludes training rows; two proposed rows were excluded. Manifest/file hashes freeze the selected records. This guards lexical/template overlap, not semantic or author independence. Both evaluation sets share the taxonomy and synthetic authorship.

Station names/aliases are read from the local database vocabulary snapshot and substituted once in applicable authored questions. Bus categories are also captured from the DB, and a separate post-training category-grounding probe scored 11/12 raw SVM classifications using the actual four category names. That small probe is neither training data nor independent evidence. Operational facts and changing entity definitions remain database-owned; the classifier does not invent fares, locations or service availability.

Twelve contextual examples and sixteen multi-intent examples are kept in separate files, outside the single-label loss. Exact follow-ups “What about tomorrow?”, “No, Tirumala.”, “Second one.”, “How much?” and “Same bus.” are additionally checked through the real conversation manager. None is turned into an arbitrary standalone class merely to fill training quotas.

All provenance explicitly says synthetic/pending review. A representative **human-reviewed validation set is still missing**. The next corpus stage should progressively approach 200+ genuinely varied reviewed examples per intent; that target has not been manufactured by augmentation in this run. Use the existing approved-feedback workflow and fresh independent conversation groups to expand it.

No contradictory exact duplicate labels were found by the automated audit. That is not proof that every synthetic label is correct: the original and expanded banks still need human adjudication, particularly at the contrastive boundaries documented in the per-intent error files. No human-review status was assigned by this work.

## Actual candidates

The immutable local folder is `models/english/nlp/recovery-60-v3`. Old grouped-60-v1 and selective-60-v2 artifacts remain unchanged. Weights stay excluded from Git; manifests, source data, evaluation reports, hashes and registry metadata are retained in the repository.

**SVM:** word TF-IDF (1,2) + character-within-word TF-IDF (3,5), sublinear TF, balanced LinearSVC, seed 73421. Twelve train-only feature/C configurations were evaluated on validation. Selected C=0.25 and character weight=2 yielded validation accuracy 90.0%, macro-F1 0.8993. A separate binary domain SVM is fitted on training ID/OOS examples. Validation-only rejection selection requires at least 30 accepted ID records, >=95% accepted-ID precision and <=5% OOS false acceptance. Selected domain margin=1, top margin=-1, top-two gap=0.4. Margins are **not probabilities**.

**TextCNN:** two configurations were actually trained. Selected embedding width=96, 96 filters per width with parallel kernels 2/3/4/5, global max pools, dropout=0.4 and 60-way softmax. Training-only vocabulary has 1,328 tokens, capped at 6,000; sequence length=16 follows the training length distribution. Adam starts at 0.001, with learning-rate reduction and validation-loss early stopping/restored best weights. Class weights are unnecessary for the observed 34–35 support balance. Both histories and configurations are saved; no weaker trial is hidden. Seeds are 73421 and 73422, with shuffle seed 73421. Validation accuracy is 90.0%, macro-F1 0.8954.

CNN softmax/gap threshold search found **no validation operating point** meeting the same precision/OOS constraints. The candidate therefore has an explicit reject-all policy. This is not successful selective inference and does not mean the CNN has 100% safe intent recognition. A future version needs better OOS modelling and genuinely independent validation; thresholds were not weakened to show success.

Both 60-element output maps exactly match the actual active ENQUIRY registry in the local DB (`label-compatibility.json`). `config/model_registry.yaml` only appends two CANDIDATE entries with approved=false, independent_evaluation=false and promotion_eligible=false. Hashes prove all original registry entries are unchanged. The older registry regression now permits this verified append-only extension instead of incorrectly treating the entire registry file as permanently immutable.

## Identical synthetic challenge comparison

Closed-set accuracy / macro-F1 on the same **180 ID questions**:

- Current deterministic standalone rule classification: **10.56% / 0.1201**.
- Existing grouped SVM: **49.44% / 0.4764**.
- Existing selective SVM v2: **81.67% / 0.8148**.
- New recovery SVM: **92.78% / 0.9266**.
- Existing TextCNN: **9.44% / 0.0901**.
- New recovery TextCNN: **85.00% / 0.8479**.

The rule number is the standalone rule/classify-extra layer, counting ambiguity/rejection as incorrect; it is **not end-to-end production conversation accuracy**. Production also uses context, entity resolution, planning and clarification. Replacing the whole conversation manager based on this number would be invalid.

The new SVM accepts **131/180 ID questions**, correctly answering **128/131 (97.71%)**, rejecting 27.22% of ID, and falsely accepting **0/60 OOS**. Correctly accepted ID / all ID is **71.11%**; including OOS rejections, overall decision accuracy is **78.33%**. Existing selective-v2 has lower accepted-ID precision (80.70%) but higher coverage, with overall decision accuracy 81.67%. The new model trades coverage for fewer confident mistakes; it does **not** improve every operational metric.

The new CNN rejects all 180 ID questions under its failed-calibration policy; accepted precision is undefined, not 100%. Its raw 85% classification score is not usable production acceptance coverage. Original SVM/CNN force all 60 OOS questions into transport classes. Every raw/selective prediction, 63-label confusion matrix retaining abstentions, and all per-intent F1 scores are in `comparison.json` and `intent-confusions.json`.

Three confidently accepted SVM errors remain: connecting travel expressed with negation was labelled DIRECT_BUS; a fare comparison was labelled GET_FARE; and cancellation-policy wording was labelled actual BUS_CANCELLATION. The remaining raw errors include category/availability, frequency/distance, stop/via, and ETA/scheduled-arrival confusions. These justify more reviewed contrastive data in a new version, not edits to the already evaluated challenge.

Warm single-input medians in the common evaluation process were approximately **2.52 ms new SVM**, **10.86 ms new CNN**, **1.14 ms grouped SVM**, and **5.64 ms old CNN**. The final JSON retains exact timing samples/metrics, artifact sizes, cold load time and RSS increments. RSS is measured for the evaluation process with shared libraries/models loaded, not isolated model-only RAM. Short CPU measurements are not a bus-stand throughput SLA. TensorFlow ran on CPU in the existing Windows environment; no additional speech/encoder model was downloaded.

## Conversation, composition and offline verification

A private copy of the real local DB was exercised with socket/DNS egress denied. Shadow injections use actual loaded checkpoints only when the existing manager requests statistical fallback; they do not activate a registry entry. Seven checks cover a DB departure list, selected second service, exact recorded fare, retained service, date change, destination correction and a fallback paraphrase.

Results: rules **7/7**, grouped SVM **5/7**, new SVM **7/7**, old CNN **6/7**, new CNN rejection policy **6/7**. Each candidate path requested fallback twice. These seven synthetic checks are integration evidence, not field answer accuracy. Full step-level facts are in `conversation.json`.

The separate sixteen-example synthetic multi-intent check gives rule composition exact match **9/16 (56.25%)**. The statistical candidates remain single-label models and are not falsely evaluated as multi-label classifiers. Dialogue acts, slot updates and selected-result references stay in the shared conversation layer. A single-label checkpoint alone cannot solve composition or booking-system integration.

Training, checkpoint loading and comparison ran under the existing Python socket/DNS audit guard with HF/Transformers offline flags. No downloads were attempted. This is application-level offline enforcement, not OS-level network-isolation certification. Focused corpus/model tests, dialogue/offline tests, full backend regression, Ruff and Mypy results are recorded in `verification.json` and their raw/JUnit files. No UI was modified.

Executed results: full backend **2,327 passed**, focused dialogue/offline regression **679 passed**, corpus/model verification **25 passed**, all without failures. Counts overlap. The full suite includes the actual dedicated local PostgreSQL tests; the verification JSON records their count. Ruff passed; configured Mypy passed for **61 backend files** and an additional **five training/evaluation scripts**. The existing TestClient deprecation warning remains.

## Reproduction and promotion recommendation

Use the existing `.venv-english` environment (TensorFlow 2.21.0, scikit-learn 1.9.1, joblib 1.6.0) with locally installed dependencies. Scripts default to project-relative immutable files:

1. `python scripts/audit_english_recovery.py`
2. `python scripts/prepare_english_recovery.py` (refuses an already frozen corpus).
3. `python scripts/train_english_recovery.py svm` and `python scripts/train_english_recovery.py cnn` (refuse existing checkpoint files).
4. `python scripts/evaluate_english_recovery.py`
5. `python scripts/verify_recovery_conversation.py`
6. `python -m pytest`, with the dedicated local test PostgreSQL URL where available; `python -m ruff check` on the changed files and configured `python -m mypy backend/app --ignore-missing-imports`.

Use `--output-version A_NEW_VERSION --dataset PATH_TO_FROZEN_DATASET` for subsequent training rather than overwriting recovery-v3 or grouped-v1. Preserve the corpus/manifest, DB vocabulary and package-version snapshot. TensorFlow CPU reductions may not be bitwise reproducible across hardware; seeds, histories and immutable file checksums identify the actual run.

**Recommendation: retain rules; advance recovery SVM to human validation, not deployment. Do not promote the CNN.** Obtain independently human-reviewed representative validation and held-out test conversations, including negation, OOS, multi-intent/context and DB-grounded answers. Evaluate coverage/accuracy tradeoffs, uncertainty and regression gates, then seek explicit approval. No human review, independent evidence or production accuracy is fabricated. The 200+/intent expansion, reviewed validation and independent test set remain unfinished inputs.
