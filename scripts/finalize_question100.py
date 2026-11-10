"""Register only inactive batch candidates and record auditable execution evidence."""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from prepare_english_recovery import dump, normalize, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    if not args.register and not args.record:
        parser.error("Choose --register, --record, or both")
    if not args.version or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for c in args.version
    ):
        parser.error("Invalid version")
    out = ROOT / "evaluation" / args.version
    folder = ROOT / "models/english/nlp" / args.version
    data = ROOT / "training/datasets" / args.version
    read = lambda path: json.loads(path.read_text(encoding="utf-8-sig"))
    comparison = read(out / "model-comparison.json")
    manifest = read(data / "manifest.json")
    descriptors = []
    for kind in ("svm", "textcnn"):
        row = read(folder / (kind + "-descriptor.json"))
        artifact = (ROOT / row["local_path"]).resolve()
        if not artifact.is_relative_to(ROOT) or sha(artifact) != row["sha256"]:
            raise ValueError("Candidate path/checksum failed")
        descriptors.append((kind, row))
    registry_path = ROOT / "config/model_registry.yaml"
    registry = read(registry_path)
    if args.register:
        if any(r.get("version") == args.version for r in registry["models"]):
            raise ValueError("Version already registered; refusing replacement")
        (folder / "registry-before.json").write_bytes(registry_path.read_bytes())
        for kind, row in descriptors:
            row.update(
                name=args.version + " " + kind + " candidate",
                evaluation_report=(out / "model-comparison.json")
                .relative_to(ROOT)
                .as_posix(),
                approved=False,
                independent_evaluation=False,
                promotion_eligible=False,
                human_reviewed=False,
                deployment_status="CANDIDATE",
                download_status="LOCAL_TRAINED",
                load_verification_status="VERIFIED_OFFLINE",
                training_question_count=100,
                classifier_training_question_count=manifest[
                    "added_single_label_or_oos"
                ],
                structured_dialogue_multi_targets=manifest[
                    "structured_dialogue_or_multi"
                ],
                human_test_metrics=None,
            )
            if kind == "textcnn":
                calibration = comparison["cnn_calibration"]
                row.update(
                    threshold_source="validation",
                    calibration_feasible=calibration is not None,
                    rejection_policy="REJECT_ALL_CALIBRATION_FAILED"
                    if calibration is None
                    else "VALIDATION_THRESHOLD_UNAPPROVED",
                    decision_threshold=calibration["softmax_threshold"]
                    if calibration
                    else None,
                )
            registry["models"].append(row)
        temporary = registry_path.with_suffix(".batch.tmp")
        dump(temporary, registry)
        os.replace(temporary, registry_path)
    if args.record:
        import httpx

        before, control, after = [
            read(out / name)
            for name in ("before.json", "previous-shadow.json", "after-shadow.json")
        ]
        all_questions = []
        for path in (ROOT / "evaluation").glob("question100-v*/expected.json"):
            all_questions.extend(normalize(r["question"]) for r in read(path))
        if len(all_questions) != len(set(all_questions)):
            raise ValueError("Cross-batch duplicate detected")
        previous = read(
            ROOT
            / "training/datasets"
            / manifest["base_dataset_version"]
            / "manifest.json"
        )
        unchanged = all(
            previous["files"][s]["sha256"] == manifest["files"][s]["sha256"]
            for s in ("validation", "synthetic_challenge")
        )
        if not unchanged:
            raise ValueError("Holdout changed during training")
        with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False) as client:
            health = client.get("/api/v1/nlp/health").json()
        if health["data"]["statistical_model"] != "NOT_APPROVED":
            raise ValueError(
                "Unexpected production model state; inspect before reporting"
            )
        entries = [
            r for r in read(registry_path)["models"] if r.get("version") == args.version
        ]
        if len(entries) != 2 or any(
            r["deployment_status"] != "CANDIDATE"
            or r["approved"]
            or r["independent_evaluation"]
            for r in entries
        ):
            raise ValueError("Registry is not an inactive candidate pair")
        report = {
            "recorded_at": datetime.now(UTC).isoformat(),
            "batch": args.version,
            "new_unique_questions": 100,
            "total_unique_across_batches": len(all_questions),
            "expectations_frozen_before_live_questions": True,
            "live_checks_passed": before["passed"],
            "previous_candidate_shadow": control["passed"],
            "trained_candidate_shadow": after["passed"],
            "training_specific_gain": after["passed"] - control["passed"],
            "before_by_kind": before["by_kind"],
            "after_by_kind": after["by_kind"],
            "setup_requests_per_run": before["supporting_setup_requests"],
            "classifier_examples_added": manifest["added_single_label_or_oos"],
            "structured_dialogue_multi_targets_added": manifest[
                "structured_dialogue_or_multi"
            ],
            "total_classifier_training_records": manifest["files"]["train"]["count"],
            "all_100_learned_by_single_label_loss": False,
            "human_reviewed": False,
            "independent_test_available": False,
            "heldout_hashes_unchanged": unchanged,
            "synthetic_holdout_raw_accuracy": {
                m: r["synthetic_holdout"]["raw_in_scope_accuracy"]
                for m, r in comparison["models"].items()
            },
            "cnn_calibration": comparison["cnn_calibration"],
            "remaining_failed_ids": [
                r["id"] for r in after["records"] if not r["evaluation"]["passed"]
            ],
            "tests": ET.parse(out / "tests.xml").getroot()[0].attrib,
            "ruff": (out / "ruff.txt").read_text(encoding="utf-8-sig").strip(),
            "mypy": (out / "mypy.txt").read_text(encoding="utf-8-sig").strip(),
            "production_health": health,
            "deployed": False,
            "recommendation": "Retain production rules pending independent review, uncertainty and conversation release gates",
            "evaluation_protocol": "Second-option test starts from first selection; selection retention must not ask for clarification",
        }
        dump(out / "verification.json", report)
        print(
            json.dumps(
                {
                    k: report[k]
                    for k in (
                        "batch",
                        "total_unique_across_batches",
                        "live_checks_passed",
                        "previous_candidate_shadow",
                        "trained_candidate_shadow",
                    )
                }
            )
        )


if __name__ == "__main__":
    main()
