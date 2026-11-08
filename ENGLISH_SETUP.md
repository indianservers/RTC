# English-first offline assistant

Status: INCOMPLETE. Previous multilingual source, aliases, registry entries and partial downloads are preserved and deferred.

## What works and was executed

- Existing database-backed text conversation via terminal and APIs; rules, aliases and response templates are read from DB. Changes to active NLP rules/templates are visible without restarting the engine. Initial JSON phrases are setup seed material only, not a runtime rule source.
- Authenticated master CRUD/import now includes nlp-intents, nlp-rules and nlp-templates. GET /api/v1/admin/{resource} supplies IDs for edits. Use the existing RTC_ADMIN_TOKEN; no default credential is provided. Reviewed dataset_split fields can be maintained in nlp-rules records.
- Official Vosk small-en-us-0.15 and en-us-0.22-lgraph downloaded, ZIP integrity checked, extracted and initialized. Both transcribed the official Vosk example recording with Python socket egress blocked.
- Small Vosk: load 0.290 s, processing 0.922 s for 8.308 s audio, RTF 0.111. Lgraph: load 0.786 s, processing 4.740 s, RTF 0.571. Peak process working sets were approximately 189 MB and 534 MB respectively in one sequential benchmark process; these are cumulative process peaks, not isolated model allocations.
- Local Windows SAPI TTS produced a 2.963 s WAV from a database HELP template in 0.687 s. Playback/acoustic verification was not performed. Piper was not installed; native OS voices provide the Windows fallback. Voice redistribution rights are unverified; do not package OS voices.
- Typed terminal enquiry returned a stored DEMO service/fare. DEMO_NOTICE now comes from the database and prefixes demonstration schedule answers.
- Host: approximately 32 GiB RAM, 12 logical CPUs, NVIDIA RTX 3050 6 GB; these CPU benchmarks did not use GPU acceleration. Approximately 322 GB disk space was available before English downloads.

## Run

```powershell
$env:PYTHONPATH='backend'
python -m app.nlp_seed
.\.venv-english\Scripts\python scripts/english_assistant.py --station DEMO0
.\.venv-english\Scripts\python scripts/english_assistant.py --station DEMO0 --voice --speak --input-device 11 --input-rate 48000 --input-channels 2
```

DEMO0 is a seeded station code; use a configured real station code for an approved dataset. Voice operation is half-duplex: microphone stream closes before TTS, preventing direct speaker feedback. Vosk endpointing, partial transcripts and a 20-second utterance cap are implemented. Ctrl+C stops the terminal. Full barge-in, push-to-talk and output cancellation during runAndWait are not implemented. Device 11 is this machine's enumerated input; device IDs differ by machine. The 16 kHz mono format failed with PortAudio -9997; 48 kHz stereo format validation succeeded. A full live microphone spoken-enquiry test has NOT been executed.

## Training

training/english/train.py implements TF-IDF + LinearSVC and optional Keras Embedding/TextCNN on the same database train/validation/test partitions. It checks exact duplicate leakage and label coverage and emits classification reports, confusion matrices and SVM inference latency. It deliberately refuses missing reviewed data. Execution stopped with: `BLOCKED: reviewed train/validation/test utterances are missing in the database. No model trained.` No 8000-example dataset, trained English classifier, independent macro-F1, or model-selection result exists. Template-family leakage auditing and TextCNN latency benchmarking need further implementation.

```powershell
$env:PYTHONPATH='backend'
.\.venv-english\Scripts\python training/english/train.py
.\.venv-english\Scripts\python training/english/train.py --tensorflow
```

Only train after reviewing and partitioning English examples in nlp_utterances. Runtime still uses deterministic DB rules. SVM/TextCNN runtime adapters and classifier selection are unfinished.

## Verification and remaining acceptance gaps

scripts/verify_english.py records real sample transcription/load/RTF/memory measurements in models/benchmarks/english-vosk.json. No independently reviewed reference transcript was available, so WER is deliberately null. The recording is not an RTC or Indian-English evaluation corpus. Accuracy targets remain unachieved/unmeasured. No model quality claim follows from successful loading.

scripts/verify_english_tts.py records local synthesis, not audible playback. scripts/offline_guard.py blocks Python socket operations; it does not establish OS/native-library firewall isolation. Live-microphone, reviewed end-to-end answer accuracy, entity F1, complete forty-intent semantic coverage, OS-isolated inference, trained classifier comparison and PostgreSQL tests remain unverified/incomplete. The terminal uses the existing conversation implementation and inherits its documented clarification, context and query limitations. Do not treat this as a production-complete voice kiosk.

Dependency setup is separate from runtime. The .venv-english environment inherits base backend packages and adds English speech/ML dependencies locally; it is not a portable deployment image. Actual installed versions and installation logs are under models/benchmarks. Models and virtual environments are Git-ignored. No UI was introduced.

Sources: https://alphacephei.com/vosk/models (both checkpoints Apache-2.0); official sample https://github.com/alphacep/vosk-api/blob/master/python/example/test.wav. Check licences before redistribution. Piper's maintained runtime https://github.com/OHF-Voice/piper1-gpl is GPL-3.0 and individual voices need separate licence review.

TensorFlow 2.21.0 and Keras 3.15.1 installed successfully in .venv-english. TensorFlow import and a basic tensor-operation smoke test succeeded (sum=6). This verifies runtime availability, not TextCNN training or classification quality. Final regression suite: 151 passed with one Starlette/HTTPX deprecation warning; Ruff and application Mypy passed.
