"""Setup-only official Vosk downloads; runtime never downloads models."""

import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / "models/english"
folder.mkdir(parents=True, exist_ok=True)
for name in ["vosk-model-small-en-us-0.15", "vosk-model-en-us-0.22-lgraph"]:
    archive = folder / (name + ".zip")
    partial = archive.with_suffix(".zip.part")
    url = "https://alphacephei.com/vosk/models/" + name + ".zip"
    print("Downloading", name, flush=True)
    if not archive.exists():
        urllib.request.urlretrieve(url, partial)
        with zipfile.ZipFile(partial) as z:
            if z.testzip():
                raise RuntimeError("Corrupt archive")
        partial.replace(archive)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            target = (folder / info.filename).resolve()
            if not target.is_relative_to(folder.resolve()):
                raise ValueError("Unsafe archive path")
        z.extractall(folder)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (folder / (name + ".manifest.json")).write_text(
        json.dumps(
            {
                "name": name,
                "url": url,
                "license": "Apache-2.0",
                "bytes": archive.stat().st_size,
                "sha256": digest,
                "status": "downloaded_not_loaded",
            },
            indent=2,
        )
    )
    print("Extracted", name, flush=True)
