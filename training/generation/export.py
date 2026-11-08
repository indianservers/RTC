"""Export candidates without promoting or constructing training splits."""

import argparse
import csv
import json
import shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--huggingface", action="store_true")
args = parser.parse_args()
rows = [json.loads(s) for s in args.source.read_text(encoding="utf-8").splitlines()]
args.output.mkdir(parents=True, exist_ok=True)
fields = list(rows[0])
with (args.output / "candidates.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                k: json.dumps(v, ensure_ascii=False)
                if isinstance(v, (dict, list))
                else v
                for k, v in row.items()
            }
        )
# Local JSON data-directory format accepted by datasets.load_dataset('json', data_files=...).
flat_rows = [
    {
        k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
        for k, v in row.items()
    }
    for row in rows
]
(args.output / "candidates.jsonl").write_text(
    "\n".join(json.dumps(row, ensure_ascii=False) for row in flat_rows) + "\n",
    encoding="utf-8",
)
shutil.copyfile(args.source, args.output / "canonical_records.jsonl")
(args.output / "README.md").write_text(
    '# RTC synthetic candidates\n\nUnreviewed candidates, no train/test split.\nLoad locally with datasets.load_dataset("json", data_files="candidates.jsonl").\nNested fields (entities, context, intent_codes, constraints, provenance) are JSON strings in the Hugging Face transport export; decode with json.loads. canonical_records.jsonl preserves the full typed canonical format. No Hugging Face upload or network access is needed.\n',
    encoding="utf-8",
)
if args.huggingface:
    from datasets import Dataset

    Dataset.from_list(flat_rows).save_to_disk(str(args.output / "huggingface"))
