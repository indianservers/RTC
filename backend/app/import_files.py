"""Bounded local CSV/XLSX ingestion and schema-derived import templates."""

import csv
import hashlib
import io
import json
import zipfile
from datetime import date, datetime
from decimal import Decimal

from .imports import RESOURCES
from .publication import MAX_ROWS

MAX_BYTES = 10_000_000


def parse_file(filename, content):
    if len(content) > MAX_BYTES:
        raise ValueError("Maximum upload size is 10 MB")
    if filename.lower().endswith(".csv"):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV must use UTF-8 encoding") from exc
        reader = csv.reader(io.StringIO(text))
        try:
            headers = next(reader)
        except StopIteration as exc:
            raise ValueError("The file is empty") from exc
        values = []
        for line, row in enumerate(reader, 2):
            if len(values) >= MAX_ROWS:
                raise ValueError("Maximum 10000 rows")
            if len(row) != len(headers):
                raise ValueError(f"Column count differs on row {line}")
            values.append(row)
    elif filename.lower().endswith(".xlsx"):
        import openpyxl

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if (
                    len(archive.infolist()) > 1000
                    or sum(i.file_size for i in archive.infolist()) > 40_000_000
                ):
                    raise ValueError("Expanded XLSX exceeds safety limits")
            workbook = openpyxl.load_workbook(
                io.BytesIO(content), read_only=True, data_only=False, keep_links=False
            )
            try:
                if len(workbook.worksheets) != 1:
                    raise ValueError(
                        "Upload a workbook containing exactly one worksheet"
                    )
                sheet = workbook.worksheets[0]
                rows = sheet.iter_rows()
                headers = [str(c.value or "").strip() for c in next(rows)]
                values = []
                for row in rows:
                    if len(values) >= MAX_ROWS:
                        raise ValueError("Maximum 10000 rows")
                    if any(c.data_type == "f" for c in row):
                        raise ValueError(
                            "Formula cells are not accepted; export verified values"
                        )
                    values.append([c.value for c in row])
            finally:
                workbook.close()
        except (zipfile.BadZipFile, KeyError, StopIteration) as exc:
            raise ValueError("Invalid or empty XLSX workbook") from exc
    else:
        raise ValueError("Only .csv and .xlsx files are supported")
    if not headers or any(not h for h in headers) or len(headers) != len(set(headers)):
        raise ValueError("Missing or duplicate file headers")
    if not values:
        raise ValueError("No data rows")
    return (
        headers,
        [
            {
                h: v.isoformat()
                if isinstance(v, (date, datetime))
                else str(v)
                if isinstance(v, Decimal)
                else v
                for h, v in zip(headers, row)
            }
            for row in values
        ],
        hashlib.sha256(content).hexdigest(),
    )


def map_rows(resource, headers, rows, mapping=None, mode="insert_only"):
    if resource not in RESOURCES:
        raise ValueError("Unsupported import resource")
    fields = RESOURCES[resource][1].model_fields
    mapping = mapping or {h: h for h in headers}
    if set(mapping) - set(headers):
        raise ValueError("Column mapping refers to an unknown input header")
    targets = [v for v in mapping.values() if v]
    if len(targets) != len(set(targets)):
        raise ValueError("Two columns cannot map to the same field")
    if set(targets) - set(fields) - {"record_id"}:
        raise ValueError("Unknown mapped schema field")
    if mode not in {"insert_only", "update"}:
        raise ValueError("Choose insert_only or explicit update mode")
    commands = []
    for index, row in enumerate(rows, 2):
        values = {
            target: row.get(source) for source, target in mapping.items() if target
        }
        identifier = values.pop("record_id", None)
        if mode == "update" and not identifier:
            raise ValueError(f"Explicit update requires record_id on row {index}")
        if mode == "insert_only" and identifier:
            raise ValueError("record_id is only accepted in explicit update mode")
        values = {
            k: v
            for k, v in values.items()
            if v not in (None, "") or fields[k].is_required()
        }
        for name, value in values.items():
            if isinstance(value, str) and any(
                t in str(fields[name].annotation) for t in ("dict", "list")
            ):
                try:
                    values[name] = json.loads(value)
                except ValueError as exc:
                    raise ValueError(f"Invalid JSON in {name} on row {index}") from exc
        commands.append(
            {
                "resource": resource,
                "operation": "UPDATE" if mode == "update" else "CREATE",
                "id": identifier,
                "values": values,
                "row": index,
            }
        )
    return commands


def template(resource):
    _model, schema, keys = RESOURCES[resource]
    spec = schema.model_json_schema()
    return {
        "resource": resource,
        "required_columns": spec.get("required", []),
        "columns": spec["properties"],
        "natural_key": keys,
        "database_constraints": [
            str(c.sqltext)
            for c in _model.__table__.constraints
            if hasattr(c, "sqltext")
        ],
        "references": {
            column.name: fk.column.table.name
            for column in _model.__table__.columns
            for fk in column.foreign_keys
        },
        "operator_scope": "Global administrator for shared station/geographic definitions; otherwise the record's operator and all referenced parents must match the authorized scope.",
        "example_label": "FICTIONAL FORMAT EXAMPLES ONLY — NOT OFFICIAL RTC DATA",
        "rules": [
            "UTF-8 CSV or one-sheet XLSX; 10 MB/10000 rows",
            "No implicit overwrite: updates require explicit update mode and record_id",
            "All rows validate, independent approval, then atomic publication",
            "Amounts use Decimal; timestamps carry an explicit timezone; elapsed stop offsets may exceed 1440 for overnight trips",
            "Foreign keys use existing local IDs; no fuzzy station merge",
        ],
        "code_mappings": {
            "weekdays": "0=Monday through 6=Sunday",
            "dataset_source": "DEMO for fictional samples; official labels require a reviewed official source",
        },
    }


def csv_template(resource):
    _, schema, _ = RESOURCES[resource]
    stream = io.StringIO()
    writer = csv.writer(stream)
    names = list(schema.model_fields)
    writer.writerow(names)
    examples = []
    for name, field in schema.model_fields.items():
        if name == "dataset_source":
            value = "DEMO"
        elif name.endswith("_id"):
            value = "FICTIONAL-LOCAL-ID-REPLACE"
        elif name == "timezone":
            value = "Asia/Kolkata"
        elif name == "weekdays":
            value = "0123456"
        elif (
            field.default is not None
            and not field.is_required()
            and isinstance(field.default, (str, int, float, bool))
        ):
            value = field.default
        elif "date" in str(field.annotation) and "datetime" not in str(
            field.annotation
        ):
            value = "2030-01-01" if "from" in name else "2030-12-31"
        elif "datetime" in str(field.annotation):
            value = "2030-01-01T08:00:00+05:30"
        elif "bool" in str(field.annotation):
            value = "false"
        elif any(k in str(field.annotation) for k in ("int", "Decimal", "float")):
            value = "0"
        elif not field.is_required():
            value = ""
        else:
            value = "FICTIONAL-EXAMPLE-REPLACE"
        examples.append(value)
    writer.writerow(examples)
    return stream.getvalue()
