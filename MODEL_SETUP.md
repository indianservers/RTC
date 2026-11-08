# Local model setup — Phase 1C

PHASE 1C INCOMPLETE. Neither model has passed forward/load validation.

The AI environment is isolated in `.venv-models`; the backend dependencies and application startup are unchanged. Actual installed versions are recorded in `models/benchmarks/dependencies-lock.txt` (PyTorch 2.15.0+cpu, Transformers 5.22.2). The detected NVIDIA RTX 3050 has 6 GB VRAM; installed PyTorch is CPU-only. Free disk space before downloads was approximately 325 GB. Capacity requirements must be measured after complete loading; reserve several GB of disk and RAM rather than treating checkpoint size as peak inference memory.

## Sources and licences

MuRIL: https://huggingface.co/google/muril-base-cased, Apache-2.0; revision afd9f36c7923d54e97903922ff1b260d091d202f. Selected files: config.json, pytorch_model.bin, tokenizer_config.json, vocab.txt, special_tokens_map.json and README.md. No TensorFlow/Flax weights selected. The expected PyTorch weight size is 953477430 bytes.

IndicConformer: https://github.com/AI4Bharat/IndicConformerASR, MIT; Telugu checkpoint direct public URL listed by that repository. Expected checkpoint size: 523192320 bytes. The equivalent Hugging Face model repository requires user acceptance of access conditions. No acceptance was submitted and no gated access bypass was attempted. Public official objectstore download was used. Official NeMo source downloaded at nemo-v2 revision 8dce88cf8e94963e2033c3137f7b9993b51db88a.

Keep licence notices with any packaged models; this workspace is not a verified redistribution bundle.

## Setup and verification

```powershell
python -m venv .venv-models
.\.venv-models\Scripts\python -m pip install huggingface_hub transformers torch pyyaml psutil
.\.venv-models\Scripts\python scripts/download_muril.py
python scripts/download_asr.py
python scripts/model_registry.py
.\.venv-models\Scripts\python scripts/verify_tokenizer.py
.\.venv-models\Scripts\python scripts/verify_muril.py
```

Registry paths are relative to project root. SHA-256 values describe files actually present, including explicitly incomplete checkpoints; hashes of partial files are NOT trusted release checksums. Refresh the registry only when transfers are stopped or complete. Model weights, runtime checkout and virtual environments are ignored by Git.

## Measured results and blockers

- Five required Telugu/transliterated samples tokenized locally with Python socket egress blocked. Details: models/benchmarks/muril-tokenization.json.
- Transformers emitted a tokenizer regex warning. Tokenization completed; full tokenizer-quality validation is unresolved. Do not interpret this test as intent classification.
- MuRIL local model loading was attempted and failed because pytorch_model.bin had not completed downloading. No successful forward inference or prediction accuracy is claimed.
- Official AI4Bharat NeMo dependency resolution failed on Windows/Python 3.12: `No matching distribution found for triton`. Full log: models/benchmarks/official-nemo-install-check.txt. WSL is not installed. A supported Linux runtime with the official fork is required before ASR load verification can proceed.
- No local Telugu or mixed-language audio exists; the user confirmed samples are absent. ASR transcription, reference-based accuracy, loading time, peak memory and CPU/GPU utilization are unmeasured.
- Initial backend regression run: 17 tests passed, including a subprocess test proving the offline guard rejects socket connection attempts. This verifies Python-level blocking only.
- Process is not running as Windows administrator; an OS firewall/network-disabled inference run has NOT been performed. Python audit hooks do not prove native-code network isolation. Full offline acceptance remains unmet.

## Offline deployment

After all downloads and dependencies are verified, transfer the complete environment, source notices, registry and model folders to a disconnected machine. Set HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1. Verification scripts enforce those values and Transformers local_files_only=True before loading. Execute under an OS-enforced outbound deny/network-isolated environment and preserve its test output. No backend startup path imports model libraries or downloads weights.

For ASR, follow the official fork's nemo-v2 installation in a compatible Linux environment. `scripts/verify_asr.py` restores the local `.nemo` checkpoint, uses CTC decoding and accepts a JSONL manifest with local 16 kHz mono WAV paths, reference transcripts and sample kinds. No synthetic silence or invented transcripts are accepted as successful speech recognition.

## Phase 2 preparation

training/training_config.json defines intent dataset fields, disabled training, version format and checkpoint artifacts. training/preprocessing/validate_dataset.py checks JSONL records and split leakage. training/evaluation/evaluate.py evaluates reference/predicted intent pairs. These are preparation utilities, not a completed training pipeline or fine-tuned classifier. No training has been executed.

Final download state: large transfers were stopped before completion; they are not running in the background. MuRIL Hub partial cache is retained for resume. IndicConformer partial checkpoint is explicitly named `.nemo.part`; scripts/download_asr.py supports byte-range resume with size verification before final rename. Neither partial artifact is load-verified or suitable for packaging. These download failures to complete are separate from the independently observed NeMo dependency blocker.
