import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "config/model_registry.yaml"
data = json.loads(path.read_text(encoding="utf-8"))
reports = json.loads((root / "models/benchmarks/english-vosk.json").read_text())
for item in data["models"]:
    if item["name"].startswith("Vosk English"):
        name = Path(item["local_path"]).name
        report = next(r for r in reports if r["name"] == name)
        item.update(
            load_verification_status=report["status"],
            workflow_status="VERIFIED_SAMPLE_INFERENCE",
            license="Apache-2.0",
        )
        manifest = root / "models/english" / (name + ".manifest.json")
        if manifest.exists():
            item.update(json.loads(manifest.read_text()))
    elif item["name"] in ["English SVM", "English TextCNN"]:
        item["workflow_status"] = "BLOCKED_REVIEWED_DATASET_REQUIRED"
    elif item["name"] == "English local TTS":
        item.update(
            workflow_status="LOCAL_WAV_SYNTHESIS_VERIFIED",
            version="OS-installed Microsoft David/Zira",
            redistribution="not_verified_do_not_package",
        )
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
