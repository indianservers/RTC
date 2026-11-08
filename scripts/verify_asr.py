"""Run with the official AI4Bharat NeMo nemo-v2 runtime installed."""

import argparse
import json
import time
import wave
from pathlib import Path

from offline_guard import enforce_offline

parser = argparse.ArgumentParser()
parser.add_argument(
    "manifest",
    help="JSONL: audio_filepath, reference, kind; local 16 kHz mono WAV files",
)
args = parser.parse_args()
enforce_offline()
import nemo.collections.asr as nemo_asr

root = Path(__file__).resolve().parents[1]
checkpoint = (
    root / "models/indicconformer-telugu/indicconformer_stt_te_hybrid_rnnt_large.nemo"
)
start = time.perf_counter()
model = nemo_asr.models.ASRModel.restore_from(str(checkpoint), map_location="cpu")
model.freeze()
model.cur_decoder = "ctc"
load = time.perf_counter() - start
results = []
for line in Path(args.manifest).read_text(encoding="utf-8").splitlines():
    row = json.loads(line)
    audio = Path(row["audio_filepath"]).resolve()
    with wave.open(str(audio)) as wav:
        assert wav.getframerate() == 16000 and wav.getnchannels() == 1
        duration = wav.getnframes() / 16000
    start = time.perf_counter()
    prediction = model.transcribe(
        [str(audio)], batch_size=1, logprobs=False, language_id="te"
    )[0]
    results.append(
        {
            "audio": str(audio),
            "reference": row.get("reference"),
            "prediction": str(prediction),
            "audio_seconds": duration,
            "processing_seconds": time.perf_counter() - start,
            "kind": row.get("kind"),
        }
    )
(root / "models/benchmarks/asr-verification.json").write_text(
    json.dumps(
        {"load_seconds": load, "results": results}, ensure_ascii=False, indent=2
    ),
    encoding="utf-8",
)
