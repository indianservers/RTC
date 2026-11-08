# Missing model components and safest next actions

No downloads, installations, retraining, deletions or registry repairs were performed.

## MuRIL

Missing final `models/muril-base/pytorch_model.bin` (no alternative safetensors). Config (411), vocabulary (3162999), tokenizer_config (206), special_tokens_map (113), README (9037) bytes are present. Stored MODEL_SETUP.md reports expected PyTorch checkpoint size 953477430 bytes at revision afd9f36c7923d54e97903922ff1b260d091d202f; this is historical local metadata, not freshly queried authoritative size. Largest cache partial is 178257920 bytes, 18.6956% of that reported expectation; remaining 775219510 bytes relative to that one partial. Other partials are 41943040 and zero bytes. They may overlap; do not sum them into completion percentage. Current local weight loader fails; forward inference unavailable. Resume script: `scripts/download_muril.py` (snapshot_download pinned revision). Future authorized action: validate pinned upstream metadata, resume without deleting partials, verify hash, load/forward locally, then separately plan RTC fine-tuning.

## IndicConformer Telugu

Missing final `models/indicconformer-telugu/indicconformer_stt_te_hybrid_rnnt_large.nemo`. Main resumable `.nemo.part`: 128372736 bytes of locally recorded expected 523192320, 24.5364%; remaining 394819584 bytes. Hidden .parts/0..7 contain additional transfer fragments whose coverage/integrity is not established; do not count them as additional assembled bytes. No complete archive exists to integrity-test.

NeMo runtime not installed, hydra-core absent (first failure when loading existing source), Triton absent, PyTorch CPU-only, WSL absent. Historical Windows Triton install failure remains relevant but is not a fresh installation test. No valid local Telugu reference audio: AUDIO_TEST_NOT_POSSIBLE. `scripts/download_asr.py` supports Range resume and refuses non-206 responses on an existing partial; checks final byte length before rename, but length alone is not cryptographic integrity. Future authorized work: establish a supported Linux/runtime separately, validate official checkpoint metadata, resume and checksum, then restore and transcribe reviewed Telugu audio.

## English classifiers

No missing grouped checkpoint/vectorizer/tokenizer/head files. Both SVM and TextCNN structurally match all 60 labels. Missing release components: reviewed training data at required scale, human-reviewed independent test set, validated uncertainty threshold/calibration, promotion approval, OS-isolated runtime proof. Existing lifecycle gate requires 10000 reviewed examples, independent macro-F1 >=0.95, validation-derived threshold and OS offline evidence. These are repository policy requirements, not claims of achieved quality. Thirty grouped CNN epochs do not compensate for poor synthetic validation metrics. Pilot models lack 25 canonical labels and have nine obsolete codes; exact lists in audit-training.json. Do not change active selection until quality and gate requirements are actually met.

## Voice and optional model

Vosk: no missing runtime/model component detected; both initialized/transcribed. Need representative local RTC/Indian-English audio and reviewed transcripts for WER, plus application integration and OS offline verification. Windows SAPI TTS synthesis works with OS voices; no Piper installed/ONNX voice found, and no installation is needed to prove the existing SAPI path. New synthesized output is docs/audit-tts.wav; no listening quality claim. IndicBERT v2: no local checkpoint discovered; optional for English-only release, defer downloading.

## Registry/quality tooling

Reconcile stale Vosk status and directory-versus-ZIP checksum semantics after reviewing this report. Add manifest coverage of hidden partial fragments if desired; never label partials complete. Preserve current model hashes and source dataset/version semantics. Reconcile preprocessing metadata with actual embedded transformations. Strict Mypy lacks joblib stubs; documented --ignore-missing-imports run passes. No dependencies were installed to silence this finding.
