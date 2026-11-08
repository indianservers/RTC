"""Local Vosk load/transcription benchmark under Python socket blocking."""

import json
import time
import wave
from pathlib import Path

from offline_guard import enforce_offline

enforce_offline()
import psutil
from vosk import KaldiRecognizer, Model

root = Path(__file__).resolve().parents[1]
report = []
for name in ["vosk-model-small-en-us-0.15", "vosk-model-en-us-0.22-lgraph"]:
    path = root / "models/english" / name
    if not (path / "am/final.mdl").is_file():
        report.append({"name": name, "status": "MODEL_NOT_PRESENT"})
        continue
    start = time.perf_counter()
    model = Model(str(path))
    loading = time.perf_counter() - start
    audio = root / "models/english/samples/vosk-official-test.wav"
    with wave.open(str(audio)) as wav:
        assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
        duration = wav.getnframes() / wav.getframerate()
        recognizer = KaldiRecognizer(model, wav.getframerate())
        segments = []
        start = time.perf_counter()
        while data := wav.readframes(4000):
            if recognizer.AcceptWaveform(data):
                segments.append(json.loads(recognizer.Result()).get("text", ""))
        segments.append(json.loads(recognizer.FinalResult()).get("text", ""))
        elapsed = time.perf_counter() - start
    report.append(
        {
            "name": name,
            "status": "LOADED_AND_TRANSCRIBED",
            "load_seconds": loading,
            "audio_seconds": duration,
            "processing_seconds": elapsed,
            "real_time_factor": elapsed / duration,
            "peak_memory_bytes": psutil.Process().memory_info().peak_wset,
            "transcript": " ".join(segments),
            "wer": None,
            "accuracy_limitation": "No independently reviewed reference transcript; no WER reported. Official Vosk example recording is not an RTC/Indian-English evaluation set.",
            "network_guard": "Python audit hook, not OS-level isolation",
        }
    )
    del model
(root / "models/benchmarks/english-vosk.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
