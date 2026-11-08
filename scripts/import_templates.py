"""Generate import headers directly from the validated schemas."""

import csv
from pathlib import Path

from app.imports import RESOURCES

for name, (_, schema, _) in RESOURCES.items():
    path = Path("data/import_templates") / (name + ".csv")
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerow(schema.model_fields)
