"""English terminal demo. Microphone input is half-duplex during local speech."""

import argparse
import json
import queue
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.domain import database
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from sqlalchemy.orm import Session

parser = argparse.ArgumentParser()
parser.add_argument("--voice", action="store_true")
parser.add_argument("--station", required=True)
parser.add_argument("--model", default="models/english/vosk-model-small-en-us-0.15")
parser.add_argument("--speak", action="store_true")
parser.add_argument("--input-device", type=int)
parser.add_argument("--input-rate", type=int, default=48000)
parser.add_argument("--input-channels", type=int, choices=[1, 2], default=2)
args = parser.parse_args()
model = None
tts = None
if args.voice:
    import sounddevice as sd
    from vosk import KaldiRecognizer, Model

    path = (root / args.model).resolve()
    if not path.is_relative_to(root) or not path.is_dir():
        raise ValueError("Local Vosk model is missing")
    model = Model(str(path))
    if args.input_device is None:
        args.input_device = next(
            (
                i
                for i, d in enumerate(sd.query_devices())
                if d["max_input_channels"] >= args.input_channels
            ),
            None,
        )
    if args.input_device is None:
        raise RuntimeError("No microphone device is available")
    sd.check_input_settings(
        device=args.input_device,
        channels=args.input_channels,
        samplerate=args.input_rate,
        dtype="int16",
    )
if args.speak:
    import pyttsx3

    tts = pyttsx3.init()


def listen():
    # Stream closes before speech output: explicit half-duplex echo mitigation.
    audio = queue.Queue(maxsize=100)

    def receive(indata, frames, stamp, status):
        try:
            import numpy as np

            samples = np.frombuffer(indata, dtype=np.int16)
            if args.input_channels == 2:
                samples = samples.reshape(-1, 2).mean(axis=1).astype(np.int16)
            audio.put_nowait(samples.tobytes())
        except queue.Full:
            pass

    recognizer = KaldiRecognizer(model, args.input_rate)
    began = time.monotonic()
    with sd.RawInputStream(
        samplerate=args.input_rate,
        blocksize=args.input_rate // 4,
        dtype="int16",
        channels=args.input_channels,
        callback=receive,
        device=args.input_device,
    ):
        while time.monotonic() - began < 20:
            try:
                block = audio.get(timeout=1)
            except queue.Empty:
                continue
            if recognizer.AcceptWaveform(block):
                text = json.loads(recognizer.Result()).get("text", "")
                if text:
                    return text
            else:
                partial = json.loads(recognizer.PartialResult()).get("partial", "")
                if partial:
                    print("\rPartial:", partial, end="", flush=True)
    return json.loads(recognizer.FinalResult()).get("text", "")


sid = None
try:
    while True:
        text = listen() if args.voice else input("You> ")
        if text.strip().casefold() in ("exit", "quit"):
            break
        if not text:
            continue
        print("\nYou>", text)
        with Session(database()) as session, session.begin():
            response = RTCNLPEngine(session).process(
                NLPRequest(
                    text=text,
                    language="en",
                    session_id=sid,
                    station_context=args.station,
                ),
                datetime.now(UTC),
            )
        sid = response.session_id
        print("RTC>", response.answer)
        print("State:", response.state, "Intents:", ",".join(response.intents))
        if tts and response.answer:
            tts.say(response.answer)
            tts.runAndWait()
except (KeyboardInterrupt, EOFError):
    if tts:
        tts.stop()
