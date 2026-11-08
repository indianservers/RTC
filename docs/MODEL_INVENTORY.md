# Model inventory

Audited 2026-11-08T14:27:08.451980+05:30; paths below are absolute. Exact unabridged file enumeration, sizes and modification timestamps: `audit-file-inventory.json`; wider repository artifact search: `audit-workspace-artifacts.json`. The inventory includes hidden per-model Hugging Face caches and downloaded NeMo source.

## Host

Windows 11 Pro 10.0.26200; Intel i5-12400F, six cores/12 logical processors. RAM 33389184 KiB total (~31.84 GiB); free fluctuated around 13 GiB. Disk C: ~319.9 billion bytes free at inspection. NVIDIA RTX 3050, 6144 MiB VRAM; NVIDIA driver 610.88, advertised CUDA driver capability 13.3. PyTorch is CPU-only (torch.version.cuda=null, cuda_available=false); TensorFlow reports native Windows GPU unsupported. WSL not installed.

## Python environments

Only Python 3.12.10 registered by py launcher. `.venv-english` uses system-site-packages=true and inherits some global application packages; `.venv-models` is isolated (false). `.model-downloader` is a pip target directory, not a virtual environment.

### C:\Indian Servers\RTC\.venv-english\Scripts\python.exe

Python: 3.12.10 (tags/v3.12.10:0cc8128, Apr  8 2025, 12:21:36) [MSC v.1943 64 bit (AMD64)]

- torch: NOT INSTALLED
- tensorflow: 2.21.0
- keras: 3.15.1
- transformers: NOT INSTALLED
- scikit-learn: 1.9.1
- vosk: 0.3.45
- nemo_toolkit: NOT INSTALLED
- numpy: 2.4.5
- tokenizers: NOT INSTALLED
- triton: NOT INSTALLED
- piper-tts: NOT INSTALLED
- pyttsx3: 2.99
- hydra-core: NOT INSTALLED
- ruff: 0.17.4
- mypy: 2.4.1
- pytest: 9.2.0
- fastapi: 0.162.2
- sqlalchemy: 2.1.8

### C:\Indian Servers\RTC\.venv-models\Scripts\python.exe

Python: 3.12.10 (tags/v3.12.10:0cc8128, Apr  8 2025, 12:21:36) [MSC v.1943 64 bit (AMD64)]

- torch: 2.15.0
- tensorflow: NOT INSTALLED
- keras: NOT INSTALLED
- transformers: 5.22.2
- scikit-learn: NOT INSTALLED
- vosk: NOT INSTALLED
- nemo_toolkit: NOT INSTALLED
- numpy: 2.5.4
- tokenizers: 0.23.3
- triton: NOT INSTALLED
- piper-tts: NOT INSTALLED
- pyttsx3: NOT INSTALLED
- hydra-core: NOT INSTALLED

## Registry and artifacts

Registry: `C:\Indian Servers\RTC\config\model_registry.yaml`. Canonical labels: `C:\Indian Servers\RTC\training\config\intent_registry.yaml`. Model output folders include grouped-60-v1, pilot-v1 and pilot-v2. Existing verification scripts are `scripts/verify.py`, verify_tokenizer.py, verify_muril.py, verify_asr.py, verify_english.py, verify_english_tts.py and offline_guard.py; some overwrite historical benchmarks, so this audit used equivalent direct read-only inference and wrote separate audit evidence.

- `C:\Indian Servers\RTC\models`: exists=True; 2633 files; 1124854505 bytes.
- `C:\Indian Servers\RTC\.model-downloader`: exists=True; 1117 files; 27594854 bytes.
- `C:\Users\Sai Satish\.cache\huggingface`: exists=True; 3 files; 5779 bytes.
- `C:\Users\Sai Satish\.cache\torch`: exists=False; 0 files; 0 bytes.
- `C:\Users\Sai Satish\.cache\pip`: exists=False; 0 files; 0 bytes.

No HF_/HUGGINGFACE/TRANSFORMERS/TORCH/CUDA cache override variables were present before testing. User HF hub contains only version.txt, no snapshots; torch cache absent. User Windows pip cache is at AppData/Local/pip/Cache (http-v2, wheels, selfcheck); package cache presence is not proof of a model checkpoint. No whole-drive absence claim is made.

## Model asset file sizes

- `C:\Indian Servers\RTC\models\english\tts-verification.wav` — 130698 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph.manifest.json` — 298 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph.zip` — 130557655 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15.manifest.json` — 295 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15.zip` — 41205931 bytes
- `C:\Indian Servers\RTC\models\indicconformer-telugu\indicconformer_stt_te_hybrid_rnnt_large.nemo.part` — 128372736 bytes
- `C:\Indian Servers\RTC\models\muril-base\config.json` — 411 bytes
- `C:\Indian Servers\RTC\models\muril-base\README.md` — 9037 bytes
- `C:\Indian Servers\RTC\models\muril-base\special_tokens_map.json` — 113 bytes
- `C:\Indian Servers\RTC\models\muril-base\tokenizer_config.json` — 206 bytes
- `C:\Indian Servers\RTC\models\muril-base\vocab.txt` — 3162999 bytes
- `C:\Indian Servers\RTC\models\english\samples\vosk-official-test.wav` — 265914 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\README` — 159 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\README` — 199 bytes
- `C:\Indian Servers\RTC\models\english\nlp\grouped-60-v1\comparison.json` — 603529 bytes
- `C:\Indian Servers\RTC\models\english\nlp\grouped-60-v1\evaluation.json` — 160042 bytes
- `C:\Indian Servers\RTC\models\english\nlp\grouped-60-v1\label_map.json` — 1202 bytes
- `C:\Indian Servers\RTC\models\english\nlp\grouped-60-v1\svm.joblib` — 2778792 bytes
- `C:\Indian Servers\RTC\models\english\nlp\grouped-60-v1\textcnn.keras` — 15598461 bytes
- `C:\Indian Servers\RTC\models\english\nlp\grouped-60-v1\training_history.json` — 1886 bytes
- `C:\Indian Servers\RTC\models\english\nlp\pilot-v1\evaluation.json` — 14757 bytes
- `C:\Indian Servers\RTC\models\english\nlp\pilot-v1\label_map.json` — 898 bytes
- `C:\Indian Servers\RTC\models\english\nlp\pilot-v1\svm.joblib` — 403160 bytes
- `C:\Indian Servers\RTC\models\english\nlp\pilot-v1\textcnn.keras` — 15580791 bytes
- `C:\Indian Servers\RTC\models\english\nlp\pilot-v1\training_history.json` — 371 bytes
- `C:\Indian Servers\RTC\models\english\nlp\pilot-v2\evaluation.json` — 14857 bytes
- `C:\Indian Servers\RTC\models\english\nlp\pilot-v2\label_map.json` — 898 bytes
- `C:\Indian Servers\RTC\models\english\nlp\pilot-v2\svm.joblib` — 393160 bytes
- `C:\Indian Servers\RTC\models\english\nlp\pilot-v2\textcnn.keras` — 15580761 bytes
- `C:\Indian Servers\RTC\models\english\nlp\pilot-v2\training_history.json` — 370 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\am\final.mdl` — 73728293 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\am\tree` — 880976 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\conf\mfcc.conf` — 154 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\conf\model.conf` — 293 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\graph\disambig_tid.int` — 234 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\graph\Gr.fst` — 47168231 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\graph\HCLr.fst` — 66551106 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\graph\phones.txt` — 2176 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\graph\words.txt` — 5722620 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\ivector\final.dubm` — 168048 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\ivector\final.ie` — 19757687 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\ivector\final.mat` — 44975 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\ivector\global_cmvn.stats` — 1080 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\ivector\online_cmvn.conf` — 95 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\ivector\splice.conf` — 35 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-en-us-0.22-lgraph\graph\phones\word_boundary.int` — 2454 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\am\final.mdl` — 15962575 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\conf\mfcc.conf` — 131 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\conf\model.conf` — 290 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\graph\disambig_tid.int` — 102 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\graph\Gr.fst` — 24013795 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\graph\HCLr.fst` — 22416994 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\ivector\final.dubm` — 168048 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\ivector\final.ie` — 8288887 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\ivector\final.mat` — 44975 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\ivector\global_cmvn.stats` — 1080 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\ivector\online_cmvn.conf` — 95 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\ivector\splice.conf` — 35 bytes
- `C:\Indian Servers\RTC\models\english\vosk-model-small-en-us-0.15\graph\phones\word_boundary.int` — 1761 bytes
- `C:\Indian Servers\RTC\models\indicconformer-telugu\.parts\0` — 14680064 bytes
- `C:\Indian Servers\RTC\models\indicconformer-telugu\.parts\1` — 12582912 bytes
- `C:\Indian Servers\RTC\models\indicconformer-telugu\.parts\2` — 15728640 bytes
- `C:\Indian Servers\RTC\models\indicconformer-telugu\.parts\3` — 12582912 bytes
- `C:\Indian Servers\RTC\models\indicconformer-telugu\.parts\4` — 12582912 bytes
- `C:\Indian Servers\RTC\models\indicconformer-telugu\.parts\5` — 10485760 bytes
- `C:\Indian Servers\RTC\models\indicconformer-telugu\.parts\6` — 14680064 bytes
- `C:\Indian Servers\RTC\models\indicconformer-telugu\.parts\7` — 15728640 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\.gitignore` — 1 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\CACHEDIR.TAG` — 195 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\download\config.json.metadata` — 104 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\download\pytorch_model.bin.lock` — 0 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\download\Q1p2l2BzM1m6P5jKvr8WTq1TUio=.e65e3b7aaa3ce16d23fc4218783efd0417880655f8f398e6cb1a111a0de0c95f.350cff19.incomplete` — 0 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\download\Q1p2l2BzM1m6P5jKvr8WTq1TUio=.e65e3b7aaa3ce16d23fc4218783efd0417880655f8f398e6cb1a111a0de0c95f.c27cdf67.incomplete` — 41943040 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\download\Q1p2l2BzM1m6P5jKvr8WTq1TUio=.e65e3b7aaa3ce16d23fc4218783efd0417880655f8f398e6cb1a111a0de0c95f.ef55a9b1.incomplete` — 178257920 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\download\README.md.metadata` — 102 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\download\special_tokens_map.json.metadata` — 104 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\download\tokenizer_config.json.metadata` — 104 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\download\vocab.txt.metadata` — 103 bytes
- `C:\Indian Servers\RTC\models\muril-base\.cache\huggingface\trees\afd9f36c7923d54e97903922ff1b260d091d202f.json` — 1602 bytes

## Training dates recorded by registry

- English SVM: 2026-11-08T05:51:32.900790+00:00 UTC.
- English TextCNN: 2026-11-08T05:51:32.908293+00:00 UTC.
- english-svm-grouped-60-v1: 2026-11-08T06:25:06.887419+00:00 UTC.
- english-textcnn-grouped-60-v1: 2026-11-08T06:25:06.890418+00:00 UTC.

Grouped training saved around 11:55 IST on 2026-11-08; pilot-v2 registry dates correspond to around 11:21 IST. Registry timestamps and artifact modification times are distinct evidence; neither alone proves execution, which was separately verified by loading/inference.

## Concurrently created preparation folder

The following appeared during this audit and are not training-completion evidence:

- `C:\Indian Servers\RTC\training\datasets\selective-60-v2\oos-train-bank.txt` — 5192 bytes; modified 2026-11-08T14:24:33.566507.
- `C:\Indian Servers\RTC\training\datasets\selective-60-v2\oos-validation-bank.txt` — 3263 bytes; modified 2026-11-08T14:24:33.567508.
- `C:\Indian Servers\RTC\training\datasets\selective-60-v2\protocol.json` — 2383 bytes; modified 2026-11-08T14:21:42.060131.
- `C:\Indian Servers\RTC\training\datasets\selective-60-v2\train-bank.txt` — 24267 bytes; modified 2026-11-08T14:21:42.062131.
- `C:\Indian Servers\RTC\training\datasets\selective-60-v2\validation-bank.txt` — 14146 bytes; modified 2026-11-08T14:24:33.564508.
