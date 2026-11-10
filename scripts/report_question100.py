"""Readable, versioned record of every expectation and actual bot reply."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="question100-v2")
    args = parser.parse_args()
    if not args.version or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for c in args.version
    ):
        parser.error("Invalid version")
    out = ROOT / "evaluation" / args.version
    read = lambda name: json.loads((out / name).read_text(encoding="utf-8"))
    before, control, after = (
        read("before.json"),
        read("previous-shadow.json"),
        read("after-shadow.json"),
    )
    comparison = read("model-comparison.json")
    manifest = json.loads(
        (ROOT / "training/datasets" / args.version / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    definitions = {
        r["code"]: r["definition"]
        for r in json.loads(
            (ROOT / "training/config/intent_registry.yaml").read_text(encoding="utf-8")
        )["intents"]
    }
    predecessor = manifest.get("previous_candidate_version", "question100-v1")
    base_dataset = manifest.get("base_dataset_version", predecessor)
    lines = [
        f"# {args.version}: 100 new questions and expectation-based training",
        "",
        f"Actual running bot: **{before['passed']}/100** automated intent/context checks. Previous candidate shadow: **{control['passed']}/100**. Newly trained candidate shadow: **{after['passed']}/100**. Training-specific change: **{after['passed'] - control['passed']:+d} checks**.",
        "",
        f"All 100 questions were checked for exact novelty against prior batches and training before asking. There were {before['supporting_setup_requests']} additional, separately counted setup requests to establish selected-service context. Every expected label/action was frozen before execution. These are agent-authored synthetic expectations, not human-reviewed independent data.",
        "",
        "## What was trained",
        "",
        f"Added 60 single-intent and 10 OOS examples to the previous corpus: **{manifest['files']['train']['count']} total training examples**. Kept 20 contextual and 10 multi-intent questions as structured regression targets outside the 60-way loss. Neither model learns a new dialogue state transition just because a structured target is stored. SVM and TextCNN were both retrained as versioned candidates; old weights and previous reports are preserved.",
        "",
        "The 100-question batch is training material. Results on it are memorization/integration diagnostics, not independent accuracy. The live bot remains on deterministic rules; shadow results are from isolated DB copies with outbound socket/DNS access denied. No candidate was deployed.",
        "",
        "## Separate synthetic holdout",
        "",
    ]
    for kind in ["svm", "cnn"]:
        previous = comparison["models"]["previous_" + kind]["synthetic_holdout"]
        trained = comparison["models"]["trained_" + kind]["synthetic_holdout"]
        lines.append(
            f"- {kind.upper()} raw in-scope accuracy on the unchanged 180-question synthetic holdout: **{previous['raw_in_scope_accuracy']:.2%} → {trained['raw_in_scope_accuracy']:.2%}**; macro-F1 **{previous['per_intent']['macro avg']['f1-score']:.4f} → {trained['per_intent']['macro avg']['f1-score']:.4f}**."
        )
    lines.extend(
        [
            "",
            f"CNN validation rejection calibration: **{'feasible empirical operating point' if comparison['cnn_calibration'] else 'failed; reject-all policy'}**. No independent human-reviewed validation/test set exists. The holdout is a previously exposed synthetic regression set; it was not used for this batch's fitting or threshold selection. All raw/selective decisions and confusion matrices are saved in model-comparison.json.",
            "",
            "## Interpretation and unresolved work",
            "",
            f"**{100 - after['passed']} checks remain unresolved.** Per-kind counts are stored in verification.json. These are automated assertions, not human semantic answer-quality ratings. Some checks only test retained state or intent labels; they do not prove completeness or appropriate wording. Selected context can make ordinary lexical rules dominate a statistical classifier. Contextual corrections and multi-intent handling still need separate dialogue/composition work; single-label fitting alone cannot fix them.",
            "",
            "Recommendation: keep production unchanged pending independent review, validated uncertainty, conversation regression and explicit approval. Inspect holdout and control results rather than attributing the whole rules-to-candidate difference to this training batch. Model weights stay excluded from Git.",
            "",
            "## Execution",
            "",
            f"`python scripts/question100.py baseline --version {args.version} --previous-version {predecessor} --base-dataset training/datasets/{base_dataset}` freezes expectations and asks the live bot. `prepare` with the same arguments freezes the cumulative dataset. Use the existing train_english_recovery.py with `--dataset training/datasets/{args.version} --output-version {args.version}` for svm and cnn. The evaluation and shadow scripts take the same version arguments; `shadow --previous` evaluates the fixed predecessor. No startup downloads or production activation is involved.",
            "",
            "## All questions, expected behavior and actual replies",
            "",
        ]
    )
    for initial, old, new in zip(
        before["records"], control["records"], after["records"], strict=True
    ):
        expectation = "; ".join(
            definitions.get(code, code.replace("_", " ").lower())
            for code in initial["expected"]
        )
        lines.extend(
            [
                f"### {initial['id']} — {initial['question']}",
                "",
                "Expected: "
                + expectation
                + ". Facts must come from current DB records; missing, stale or unsupported information must remain explicit.",
                f"Automated checks — live: {'PASS' if initial['evaluation']['passed'] else 'FAIL'}; predecessor: {'PASS' if old['evaluation']['passed'] else 'FAIL'}; trained candidate: {'PASS' if new['evaluation']['passed'] else 'FAIL'}.",
                "",
                "Live reply:",
                "",
                *["> " + s for s in initial["actual"]["answer"].splitlines()],
                "",
                "Trained candidate in isolated shadow:",
                "",
                *["> " + s for s in new["actual"]["answer"].splitlines()],
                "",
            ]
        )
    (out / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Saved all 100 actual replies and expectations to " + str(out / "REPORT.md"))


if __name__ == "__main__":
    main()
