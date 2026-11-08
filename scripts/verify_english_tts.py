import json
import time
import wave
from pathlib import Path

from offline_guard import enforce_offline

enforce_offline()
import sys

import pyttsx3
from sqlalchemy import select
from sqlalchemy.orm import Session

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.catalog import Template
from app.domain import database

with Session(database()) as session:
    text = session.scalar(
        select(Template.text).where(
            Template.language == "en",
            Template.response_status == "HELP",
            Template.active.is_(True),
        )
    )
if not text:
    raise RuntimeError("Missing English HELP template in local DB")
start = time.perf_counter()
engine = pyttsx3.init()
voices = [{"id": v.id, "name": v.name} for v in engine.getProperty("voices")]
path = root / "models/english/tts-verification.wav"
engine.save_to_file(text, str(path))
engine.runAndWait()
if not path.is_file():
    raise RuntimeError("TTS did not produce audio")
with wave.open(str(path)) as wav:
    duration = wav.getnframes() / wav.getframerate()
report = {
    "runtime": "Windows SAPI via pyttsx3",
    "seconds": time.perf_counter() - start,
    "audio_seconds": duration,
    "voices": voices,
    "status": "SYNTHESIZED_LOCAL_WAV",
    "playback_verified": False,
    "license": "OS-provided voice; redistribution rights not verified; do not package the voice",
    "network_guard": "Python socket audit hook",
}
(root / "models/benchmarks/english-tts.json").write_text(json.dumps(report, indent=2))
print(report)
