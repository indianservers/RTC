# RTC synthetic candidates

Unreviewed candidates, no train/test split.
Load locally with datasets.load_dataset("json", data_files="candidates.jsonl").
Nested fields (entities, context, intent_codes, constraints, provenance) are JSON strings in the Hugging Face transport export; decode with json.loads. canonical_records.jsonl preserves the full typed canonical format. No Hugging Face upload or network access is needed.
