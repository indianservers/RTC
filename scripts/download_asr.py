"""Resume the official public Telugu checkpoint; never label partial data complete."""

import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://objectstore.e2enetworks.net/indicconformer/models/indicconformer_stt_te_hybrid_rnnt_large.nemo"
EXPECTED = 523192320
folder = ROOT / "models/indicconformer-telugu"
folder.mkdir(parents=True, exist_ok=True)
final = folder / "indicconformer_stt_te_hybrid_rnnt_large.nemo"
partial = final.with_suffix(".nemo.part")
if final.exists() and final.stat().st_size == EXPECTED:
    print("Checkpoint already complete")
    raise SystemExit(0)
start = partial.stat().st_size if partial.exists() else 0
request = urllib.request.Request(
    URL, headers={"Range": f"bytes={start}-"} if start else {}
)
with urllib.request.urlopen(request, timeout=60) as response:
    if start and response.status != 206:
        raise RuntimeError(
            "Server did not honor resume range; original partial file retained"
        )
    with partial.open("ab" if start else "wb") as out:
        while block := response.read(1024 * 1024):
            out.write(block)
            print(out.tell(), "/", EXPECTED, flush=True)
if partial.stat().st_size != EXPECTED:
    raise RuntimeError("Incomplete checkpoint; partial retained")
os.replace(partial, final)
print("Checkpoint transfer complete; run inventory and load verification next")
