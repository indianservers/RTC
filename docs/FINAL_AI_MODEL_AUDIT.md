# RTC AI model audit — actual status

Audit time: 2026-11-08T14:27:08.451980+05:30 (Asia/Calcutta). Root: `C:\Indian Servers\RTC`. Independent inspection of current artifacts; prior reports are historical evidence only.

## Definitive status matrix

| Model | Downloaded | Installed | Loads | Inference | Trained for RTC | Offline Verified | Active |
|---|---|---|---|---|---|---|---|
| Deterministic English rules | NOT_APPLICABLE | PASS | PASS | PASS | NOT_APPLICABLE | PARTIAL | PASS |
| SVM grouped-60-v1 | PASS | PASS | PASS | PASS | PASS | PARTIAL | FAIL |
| TextCNN grouped-60-v1 | PASS | PASS | PASS | PASS | PASS | PARTIAL | FAIL |
| SVM pilot-v1 / pilot-v2 | PASS | PASS | PASS | PASS | PARTIAL | PARTIAL | FAIL |
| TextCNN pilot-v1 / pilot-v2 | PASS | PASS | PASS | PASS | PARTIAL | PARTIAL | FAIL |
| MuRIL Base | PARTIAL | PASS | FAIL | FAIL | FAIL | NOT_TESTED | FAIL |
| IndicConformer Telugu | PARTIAL | FAIL | FAIL | NOT_TESTED | NOT_APPLICABLE | NOT_TESTED | FAIL |
| Vosk small English | PASS | PASS | PASS | PASS | NOT_APPLICABLE | PARTIAL | NOT_APPLICABLE |
| Vosk lgraph English | PASS | PASS | PASS | PASS | NOT_APPLICABLE | PARTIAL | NOT_APPLICABLE |
| Windows SAPI English TTS | NOT_APPLICABLE | PASS | PASS | PASS | NOT_APPLICABLE | PARTIAL | NOT_APPLICABLE |
| Piper English | FAIL | FAIL | NOT_TESTED | NOT_TESTED | NOT_APPLICABLE | NOT_TESTED | FAIL |
| IndicBERT v2 | FAIL | NOT_TESTED | NOT_TESTED | NOT_TESTED | FAIL | NOT_TESTED | FAIL |

PASS for inference means a real execution returned output, not that predictions are correct or release quality is established. Trained for RTC means saved RTC training occurred, not approval. Pilot PARTIAL reflects obsolete 44-class taxonomy. Active applies to the selected NLP path; voice runtime integration was not established. Offline PARTIAL means environment flags plus Python socket guarding, never OS isolation. Installed for MuRIL means its PyTorch/Transformers runtime, not complete weights. IndicBERT absence is scoped to inspected workspace and configured/default caches.

## Executive finding

No statistical English model is ACTIVE or approved. `EnglishIntentModel.descriptor()` returned null and prediction returned NOT_READY. `EnglishInferenceService.classify_intent()` demonstrably uses DETERMINISTIC_RULES. The conversation path uses the deterministic fallback. No active model was changed.

The 60-class SVM and TextCNN are loadable candidate experiments. Both pilot versions also reload, but each has only 44 classes, 25 missing canonical codes and nine obsolete extra codes. Exact differences are in `audit-training.json`. All six checkpoints executed the ten requested inputs.

## Training and evaluation

Canonical registry: 60 intents. Source corpus: 449 synthetic/unreviewed records, authored banks version bounded-authored-banks-v1. Frozen splits physically contain 234 training, 76 validation, 139 challenge records. The single-intent/ASR-style classifier filter uses 67 of the challenge records, producing 377 eligible examples total. Independent field/human-reviewed test count: zero. DB utterances: 63 English RULE/PENDING, 300 English TAXONOMY_SEED/PENDING_HUMAN_REVIEW, 13 mixed RULE/PENDING, two te-Latn RULE/PENDING; all have no assigned dataset split. These DB counts are not additional reviewed training examples.

Grouped TextCNN history has 30 loss/validation-loss entries and a saved model with optimizer state, embedded TextVectorization vocabulary and a 60-output softmax head. Both pilots have eight epochs recorded; pilot-v1 trained on 65 rule phrases, pilot-v2 on 63; neither has validation/test data. Saved fitted vectorizers, SVM coefficients, CNN weights/history and successful reloads establish that training occurred. Historical training dates are recorded in the registry; filesystem modification times are in the inventory. No independent training scheduler completion log was found; checkpoints/history demonstrate completed saved runs.

Recomputed grouped SVM on current frozen data: validation accuracy 0.2368421053, macro-F1 0.1775396825 (76 records); synthetic challenge accuracy 0.2985074627, macro-F1 0.2126190476 (67 records). Training accuracy 1.0 on 234 examples is resubstitution, not generalization. Recorded grouped TextCNN validation accuracy 0.0394736842, macro-F1 0.0146969697; synthetic challenge accuracy 0.0895522388, macro-F1 0.0716666667. CNN metrics are existing evaluation values, not recomputed full-split metrics in this audit. Ten smoke predictions are not an accuracy estimate.

Existing `evaluation/english-svm-v1/results.json` contains a separate 200-question agent-authored holdout (180 intent, 20 out of scope), one exact overlap, no near overlaps at its declared threshold. It explicitly lacks human adjudication/field provenance. It is not an independent real-world accuracy certification.

## Actual ten-question inference

Every row below is a fresh direct artifact prediction. SVM values are raw multiclass decision margins; CNN values are raw softmax outputs. Neither has calibrated confidence. Contextual/destination-correction rows are diagnostic standalone classifier outputs only; the conversation-context test is evaluated separately.

### svm grouped-60-v1

Artifact: `C:\Indian Servers\RTC\models\english\nlp\grouped-60-v1\svm.joblib`; 2778792 bytes; load 0.5311 seconds; label/head match: True. Error: none.

| Passenger question | Expected intent/dialogue act | Predicted | Raw score | Duration ms |
|---|---|---|---|---|
| When is the next bus to Tirupati? | NEXT_BUS | NEXT_BUS | 0.642102100 | 40.2076 |
| What is the fare to Nellore? | GET_FARE | GET_FARE | -0.439612649 | 12.6537 |
| What time is the last bus to Vizag? | LAST_BUS | LAST_BUS | 0.482043947 | 3.3584 |
| Are AC sleeper buses available tonight? | AC_BUS_AVAILABILITY + SLEEPER_AVAILABILITY + tonight constraint | SLEEPER_AVAILABILITY | 0.177610379 | 3.0431 |
| Does this bus stop at Ongole? | INTERMEDIATE_STOP | INTERMEDIATE_STOP | -0.243466034 | 2.5081 |
| Which is the cheapest bus to Hyderabad? | CHEAPEST_BUS | CHEAPEST_BUS | 0.362287397 | 3.8363 |
| Is the bus delayed? | BUS_DELAY | BUS_DELAY | 0.001664650 | 2.5038 |
| Which platform is the bus on? | BUS_PLATFORM | BUS_PLATFORM | 0.552197498 | 3.2345 |
| I want to change my destination to Tirumala. | destination correction dialogue act | DIRECT_BUS | -0.501035734 | 15.0897 |
| What about tomorrow morning? | contextual date/time refinement; retain preceding intent | FIRST_BUS | 0.206568483 | 4.3067 |

### textcnn grouped-60-v1

Artifact: `C:\Indian Servers\RTC\models\english\nlp\grouped-60-v1\textcnn.keras`; 15598461 bytes; load 0.5204 seconds; label/head match: True. Error: none.

| Passenger question | Expected intent/dialogue act | Predicted | Raw score | Duration ms |
|---|---|---|---|---|
| When is the next bus to Tirupati? | NEXT_BUS | NEXT_BUS | 0.779884517 | 416.6848 |
| What is the fare to Nellore? | GET_FARE | CHEAPEST_BUS | 0.208801359 | 17.2448 |
| What time is the last bus to Vizag? | LAST_BUS | LAST_BUS | 0.301200956 | 21.9402 |
| Are AC sleeper buses available tonight? | AC_BUS_AVAILABILITY + SLEEPER_AVAILABILITY + tonight constraint | SLEEPER_AVAILABILITY | 0.241496474 | 19.0314 |
| Does this bus stop at Ongole? | INTERMEDIATE_STOP | ALIGHTING_POINT | 0.083107039 | 22.3291 |
| Which is the cheapest bus to Hyderabad? | CHEAPEST_BUS | CHEAPEST_BUS | 0.455163866 | 32.7796 |
| Is the bus delayed? | BUS_DELAY | BUS_DELAY | 0.097831964 | 49.0523 |
| Which platform is the bus on? | BUS_PLATFORM | BUS_PLATFORM | 0.604945660 | 29.5538 |
| I want to change my destination to Tirumala. | destination correction dialogue act | NON_AC_BUS_AVAILABILITY | 0.134931728 | 39.5225 |
| What about tomorrow morning? | contextual date/time refinement; retain preceding intent | FIRST_BUS | 0.140448228 | 17.6517 |

### svm pilot-v1

Artifact: `C:\Indian Servers\RTC\models\english\nlp\pilot-v1\svm.joblib`; 403160 bytes; load 0.0078 seconds; label/head match: True. Error: none.

| Passenger question | Expected intent/dialogue act | Predicted | Raw score | Duration ms |
|---|---|---|---|---|
| When is the next bus to Tirupati? | NEXT_BUS | NEXT_BUS | 0.576650643 | 3.6080 |
| What is the fare to Nellore? | GET_FARE | TICKET_FARE | 0.440014856 | 2.1950 |
| What time is the last bus to Vizag? | LAST_BUS | LAST_BUS | 0.583819567 | 1.9944 |
| Are AC sleeper buses available tonight? | AC_BUS_AVAILABILITY + SLEEPER_AVAILABILITY + tonight constraint | SLEEPER_BUS_AVAILABILITY | 0.009042197 | 2.0544 |
| Does this bus stop at Ongole? | INTERMEDIATE_STOP | INTERMEDIATE_STOP | -0.469357249 | 2.0078 |
| Which is the cheapest bus to Hyderabad? | CHEAPEST_BUS | CHEAPEST_BUS | 0.416111767 | 1.8950 |
| Is the bus delayed? | BUS_DELAY | BUS_DELAY | -0.386412505 | 2.0554 |
| Which platform is the bus on? | BUS_PLATFORM | BUS_PLATFORM | 0.392309108 | 1.8636 |
| I want to change my destination to Tirumala. | destination correction dialogue act | JOURNEY_DURATION | -0.788977484 | 2.0472 |
| What about tomorrow morning? | contextual date/time refinement; retain preceding intent | FIRST_BUS | -0.819747881 | 1.9627 |

### textcnn pilot-v1

Artifact: `C:\Indian Servers\RTC\models\english\nlp\pilot-v1\textcnn.keras`; 15580791 bytes; load 0.4051 seconds; label/head match: True. Error: none.

| Passenger question | Expected intent/dialogue act | Predicted | Raw score | Duration ms |
|---|---|---|---|---|
| When is the next bus to Tirupati? | NEXT_BUS | ALIGHTING_POINT | 0.033087187 | 28.3013 |
| What is the fare to Nellore? | GET_FARE | ALIGHTING_POINT | 0.033435680 | 11.9335 |
| What time is the last bus to Vizag? | LAST_BUS | ALIGHTING_POINT | 0.033484913 | 19.9939 |
| Are AC sleeper buses available tonight? | AC_BUS_AVAILABILITY + SLEEPER_AVAILABILITY + tonight constraint | ALIGHTING_POINT | 0.033684663 | 19.6989 |
| Does this bus stop at Ongole? | INTERMEDIATE_STOP | ALIGHTING_POINT | 0.032616604 | 27.8899 |
| Which is the cheapest bus to Hyderabad? | CHEAPEST_BUS | ALIGHTING_POINT | 0.032921579 | 26.9177 |
| Is the bus delayed? | BUS_DELAY | ALIGHTING_POINT | 0.032622889 | 11.7144 |
| Which platform is the bus on? | BUS_PLATFORM | ALIGHTING_POINT | 0.032753251 | 56.1458 |
| I want to change my destination to Tirumala. | destination correction dialogue act | ALIGHTING_POINT | 0.033042748 | 13.3031 |
| What about tomorrow morning? | contextual date/time refinement; retain preceding intent | ALIGHTING_POINT | 0.033042748 | 27.5385 |

### svm pilot-v2

Artifact: `C:\Indian Servers\RTC\models\english\nlp\pilot-v2\svm.joblib`; 393160 bytes; load 0.0060 seconds; label/head match: True. Error: none.

| Passenger question | Expected intent/dialogue act | Predicted | Raw score | Duration ms |
|---|---|---|---|---|
| When is the next bus to Tirupati? | NEXT_BUS | NEXT_BUS | 0.576197205 | 3.8179 |
| What is the fare to Nellore? | GET_FARE | TICKET_FARE | 0.433975860 | 2.6698 |
| What time is the last bus to Vizag? | LAST_BUS | LAST_BUS | 0.583680502 | 2.5908 |
| Are AC sleeper buses available tonight? | AC_BUS_AVAILABILITY + SLEEPER_AVAILABILITY + tonight constraint | SLEEPER_BUS_AVAILABILITY | 0.008304464 | 9.1378 |
| Does this bus stop at Ongole? | INTERMEDIATE_STOP | INTERMEDIATE_STOP | -0.468877098 | 3.0090 |
| Which is the cheapest bus to Hyderabad? | CHEAPEST_BUS | CHEAPEST_BUS | 0.416410566 | 2.5133 |
| Is the bus delayed? | BUS_DELAY | BUS_DELAY | -0.385267493 | 2.7289 |
| Which platform is the bus on? | BUS_PLATFORM | BUS_PLATFORM | 0.393055602 | 3.4504 |
| I want to change my destination to Tirumala. | destination correction dialogue act | JOURNEY_DURATION | -0.785653717 | 2.6624 |
| What about tomorrow morning? | contextual date/time refinement; retain preceding intent | ROUTE_STOPS | -0.814098663 | 2.7100 |

### textcnn pilot-v2

Artifact: `C:\Indian Servers\RTC\models\english\nlp\pilot-v2\textcnn.keras`; 15580761 bytes; load 0.2757 seconds; label/head match: True. Error: none.

| Passenger question | Expected intent/dialogue act | Predicted | Raw score | Duration ms |
|---|---|---|---|---|
| When is the next bus to Tirupati? | NEXT_BUS | AVAILABLE_BUS_TYPES | 0.027030623 | 13.6006 |
| What is the fare to Nellore? | GET_FARE | AVAILABLE_BUS_TYPES | 0.025152136 | 13.9548 |
| What time is the last bus to Vizag? | LAST_BUS | FIRST_BUS | 0.027800979 | 11.7992 |
| Are AC sleeper buses available tonight? | AC_BUS_AVAILABILITY + SLEEPER_AVAILABILITY + tonight constraint | FIRST_BUS | 0.025840834 | 12.9924 |
| Does this bus stop at Ongole? | INTERMEDIATE_STOP | FIRST_BUS | 0.027046861 | 11.7243 |
| Which is the cheapest bus to Hyderabad? | CHEAPEST_BUS | AVAILABLE_BUS_TYPES | 0.026855076 | 14.4431 |
| Is the bus delayed? | BUS_DELAY | FIRST_BUS | 0.026870238 | 12.0185 |
| Which platform is the bus on? | BUS_PLATFORM | FIRST_BUS | 0.027011326 | 18.5065 |
| I want to change my destination to Tirumala. | destination correction dialogue act | LUGGAGE_RULES | 0.025067816 | 11.8991 |
| What about tomorrow morning? | contextual date/time refinement; retain preceding intent | LUGGAGE_RULES | 0.025067816 | 11.7783 |

## Application and context verification

FastAPI TestClient entered ASGI lifespan successfully. Model-status, NLP-status, station-list, database enquiry, and conversation endpoints all returned HTTP 200. This verifies in-process backend startup/routing, not a separately bound Uvicorn TCP server. The source `rtc.db` was opened read-only and backed up into RAM; conversation writes occurred only in RAM. Source DB SHA-256 was unchanged across the guarded API test.

With station context Vijayawada, “When is the next bus to Tirupati?” produced NEXT_BUS. Follow-up “What about tomorrow morning?” retained NEXT_BUS and Tirupati, changed travel_date to 2026-11-09, selected morning, and set the before-noon filter. This is a successful contextual date/time refinement, not a new FIRST_BUS classification. Both responses correctly returned DEMO/NO_RESULTS for the requested route/time. A separate existing Vijayawada–Guntur database enquiry returned five rows (HTTP 200), proving nonempty DB retrieval; that additional check used offline environment flags only. These are demo schedules, not verified live RTC operating information.

Classifier facade details, including ambiguities on AC+sleeper and unmatched standalone stop/delay questions, are preserved in `audit-api.json`. These facade results must not be confused with full conversation routing.

## Multilingual and speech results

MuRIL tokenizer loaded and encoded Telugu. Transformers emitted a tokenizer regex warning; it was preserved without altering files or flags. Actual local-only AutoModel loading failed: no model.safetensors or pytorch_model.bin. Forward inference could not execute. MuRIL is neither a complete downloaded pretrained encoder nor an RTC-fine-tuned classifier. Full diagnostic: `audit-multilingual.json`.

IndicConformer final `.nemo` is absent. Its .part file remains 128372736 bytes; runtime source is present but package is not installed. Normal import: No module named nemo. Adding the existing source path for a diagnostic import reaches No module named hydra. Triton is also absent; the earlier Triton installation error remains historical, not the current first import failure. WSL is not installed. Python is 3.12.10 on native Windows. No validated Telugu speech recording or reference manifest was found; bundled NeMo English TTS tutorial audio does not establish Telugu ASR. AUDIO_TEST_NOT_POSSIBLE. No transcription or restore claim is made.

Vosk `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph` initialized in 2.826s and transcribed the 16 kHz, mono, 16-bit, 132928-frame local official sample in 9.153s: `one zero zero zero one nine oh two one oh zero one eight zero three`.

Vosk `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15` initialized in 1.052s and transcribed the 16 kHz, mono, 16-bit, 132928-frame local official sample in 1.944s: `one zero zero zero one nah no to i know zero one eight zero three`.

No WER was computed: no independently reviewed RTC/Indian-English reference set. The audit discovery glob also attempted to initialize the adjacent .zip/.manifest.json files and correctly failed; these are audit harness candidate-selection errors, not broken Vosk model directories. Raw errors are retained.

Windows pyttsx3/SAPI initialized David and Zira en-US voices and synthesized `docs/audit-tts.wav`: 138504 bytes, 69229 frames, 22050 Hz mono, 3.1396371882086167 seconds. Playback/intelligibility was not verified. Voice resources are OS registry-provided assets, not bundled Piper ONNX models; no Piper runtime/model found. IndicBERT v2 was not found in searched artifact/cache locations. No download attempted.

## Offline limits

HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1, HF_DATASETS_OFFLINE=1 used for model tests, with existing Python audit-hook socket blocking. The strict guard blocked Windows asyncio socketpair setup; API tests were rerun with a Python audit hook allowing loopback and denying non-loopback socket connect/sendto. Neither blocks native-library networking at OS level. Windows firewall profiles were enabled but outbound defaults were NotConfigured; no task-specific OS/container egress isolation was established. Read-only scope excluded host firewall changes. Therefore OFFLINE_NOT_FULLY_VERIFIED for the deployment. Local-only model/API execution is demonstrated with the stated limits.

## Registry discrepancies and repairs needed

- Vosk entries simultaneously claim `status=downloaded_not_loaded`, `workflow_status=VERIFIED_SAMPLE_INFERENCE`, and `load_verification_status=LOADED_AND_TRANSCRIBED`. Fresh inference confirms the last two; the first is stale.
- Vosk registry SHA/byte fields refer to ZIP downloads while local_path points to extracted directories. Directory checksums are not directly equivalent; sidecar manifests list the extracted content.
- MuRIL and IndicConformer incomplete/deferred registry statuses remain accurate. MuRIL current partial sizes are missing from the registered file list; IndicConformer sibling .parts segments are not registered. Do not add segment sizes as unique assembled progress.
- All directly registered file checksums tested matched existing files, including grouped model and label-map hashes. No registered checkpoint path was physically broken. TTS intentionally has no checkpoint local_path.
- Grouped entries honestly remain CANDIDATE, approved=false, decision_threshold=null. The active gate rejects them. No untrained statistical model was found marked ACTIVE. Model-status API mirrors registry text rather than independently proving health.
- Pilot labels are incompatible with the current canonical set despite structurally valid label maps. Use grouped artifacts only for controlled evaluation.
- Registry dataset_sha256 and training evaluation dataset.sha256 use different hash subjects (source corpus versus serialized eligible records); do not interpret these as interchangeable file hashes. Split file SHA-256 values recomputed in this audit match the frozen manifest.
- `preprocessing_version=nfkc-casefold-v1` is metadata. Saved sklearn pipeline contains word/character TF-IDF with default lowercase behavior and LinearSVC; no explicit NFKC/casefold preprocessing stage is embedded. TextCNN has embedded standard TextVectorization. This preprocessing claim needs reconciliation before promotion.
- No calibrated confidence/decision threshold or human-reviewed independent release evaluation exists. Never promote based on these smoke tests.

## Validation commands and evidence

Full regression: `.venv-english/Scripts/python.exe -B -m pytest -p no:cacheprovider -q` (`audit-pytest.txt`). Ruff: `python -B -m ruff check --no-cache backend scripts training` passed. Strict Mypy `python -B -m mypy --cache-dir=nul backend/app` found one missing joblib typing stub. The documented README command adds `--ignore-missing-imports`; this configured run passed all 46 source files (`audit-mypy-configured.txt`). Both environments passed `pip check`; this does not establish NeMo installation compatibility. Test/cache settings avoided pytest/Ruff/Mypy repo caches and bytecode writes; existing tests may create their normal temporary test databases. No application code, model files, migrations, registry, active selection, or dependencies were edited.

See MODEL_INVENTORY.md and MODEL_MISSING_COMPONENTS.md. Raw current evidence: audit-file-inventory.json, audit-workspace-artifacts.json, audit-env-english.json, audit-env-models.json, audit-hardware.json, audit-training.json, audit-english-inference.json, audit-multilingual.json, audit-nemo-source-import.txt, audit-api.json, audit-db-enquiry.json, audit-tts.json.

## Final regression outcome and snapshot boundary

Fresh full regression completed: **1459 passed, one warning in 322.50 seconds**. Warning: Starlette TestClient deprecates its httpx integration in favor of httpx2; no dependency was changed. Documented Mypy command passed 46 files.

Concurrent workspace activity was observed: backend/app/imports.py and models/benchmarks/phase4b-final-backend-pytest.txt changed/appeared, and training/datasets/selective-60-v2/ was created during this audit. These were not written by this audit. Its protocol.json and authored train/validation/OOS banks are new preparation artifacts, not proof of a new trained checkpoint. At the final inspection, models/english/nlp still contained only grouped-60-v1, pilot-v1 and pilot-v2, and registry modification time remained 11:55:06 IST. This is a time-bounded snapshot, not an atomic frozen workspace certification. Regression ran against the concurrently changing checkout; no clean-checkout claim is made.
