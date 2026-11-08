"""Phase 5A real SQLite publication, imports, authorization and query regression."""

import base64
import io
from datetime import date

import pytest
from app import main
from app.domain import (
    Base,
    Category,
    Fare,
    Operator,
    Route,
    Service,
    Station,
    Stop,
    database,
)
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = {"Authorization": "Bearer phase5a-test-root"}


@pytest.fixture(params=["sqlite", "postgres"])
def managed(tmp_path, monkeypatch, request):
    import os
    from uuid import uuid4

    from sqlalchemy.schema import CreateSchema, DropSchema

    admin_engine = None
    schema = None
    if request.param == "postgres":
        url = os.getenv("RTC_TEST_POSTGRES_URL")
        if not url:
            pytest.skip(
                "Set RTC_TEST_POSTGRES_URL for the dedicated local test database"
            )
        from sqlalchemy.engine import make_url

        parsed = make_url(url)
        if parsed.database != "rtc_phase5a_tests":
            raise RuntimeError("PostgreSQL fixture only operates in rtc_phase5a_tests")
        schema = "phase5a_" + uuid4().hex
        admin_engine = database(url)
        with admin_engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = database(
            parsed.update_query_dict({"options": "-csearch_path=" + schema})
        )
    else:
        engine = database("sqlite:///" + (tmp_path / "managed.db").as_posix())
    Base.metadata.create_all(engine)
    with Session(engine) as s, s.begin():
        s.add_all(
            [
                Operator(
                    id="op-a",
                    code="DEMO-A",
                    name="FICTIONAL Operator A",
                    dataset_source="DEMO",
                ),
                Operator(
                    id="op-b",
                    code="DEMO-B",
                    name="FICTIONAL Operator B",
                    dataset_source="DEMO",
                ),
                Station(id="a", code="DEMO-A", name="Alpha", dataset_source="DEMO"),
                Station(id="b", code="DEMO-B", name="Beta", dataset_source="DEMO"),
            ]
        )
        s.flush()
        s.add(
            Category(
                id="cat",
                operator_id="op-a",
                name="Configurable category",
                dataset_source="DEMO",
            )
        )
        s.add(
            Route(
                id="route", operator_id="op-a", code="DEMO-ROUTE", dataset_source="DEMO"
            )
        )
        s.flush()
        s.add_all(
            [
                Stop(
                    id="stop-a",
                    route_id="route",
                    station_id="a",
                    sequence=0,
                    offset_minutes=0,
                    distance_km=0,
                    dataset_source="DEMO",
                ),
                Stop(
                    id="stop-b",
                    route_id="route",
                    station_id="b",
                    sequence=1,
                    offset_minutes=120,
                    distance_km=100,
                    dataset_source="DEMO",
                ),
            ]
        )
        s.flush()
        s.add(
            Service(
                id="svc",
                operator_id="op-a",
                category_id="cat",
                route_id="route",
                number="DEMO-1",
                departure_minutes=1380,
                valid_from=date(2026, 1, 1),
                valid_to=date(2035, 12, 31),
                dataset_source="DEMO",
            )
        )
        s.flush()
        s.add(
            Fare(
                id="fare",
                service_id="svc",
                origin_id="a",
                destination_id="b",
                amount=100,
                valid_from=date(2026, 1, 1),
                valid_to=date(2035, 12, 31),
                dataset_source="DEMO",
            )
        )
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setenv("RTC_ADMIN_TOKEN", "phase5a-test-root")
    monkeypatch.setenv("RTC_ALLOW_DEMO_DIRECT_WRITES", "0")
    with TestClient(main.app, client=("phase5a-" + uuid4().hex, 50000)) as client:
        result = client.post(
            "/api/v1/admin/data/users",
            headers=ROOT,
            json={
                "username": "reviewer-a",
                "role": "APPROVER",
                "operator_ids": ["op-a"],
            },
        )
        assert result.status_code == 201, result.text
        approver = {"Authorization": "Bearer " + result.json()["data"]["token"]}
        yield client, engine, approver
    engine.dispose()
    if admin_engine:
        with admin_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()


def stage(client, commands, operator="op-a"):
    result = client.post(
        "/api/v1/admin/data/changes",
        headers=ROOT,
        json={
            "commands": commands,
            "operator_id": operator,
            "reason": "Reviewed fixture update",
        },
    )
    assert result.status_code == 201, result.text
    return result.json()["data"]


def action(client, batch, verb, headers=ROOT, expected=200):
    result = client.post(
        f"/api/v1/admin/imports/batches/{batch['id']}/{verb}",
        headers=headers,
        json={"revision": batch["revision"], "reason": "Verified local test action"},
    )
    assert result.status_code == expected, result.text
    return result.json().get("data", result.json())


def publish(client, batch, approver):
    batch = action(client, batch, "validate")
    assert not batch["validation_report"]["errors"], batch
    batch = action(client, batch, "approve", approver)
    return action(client, batch, "publish")


def fare_values(amount=125):
    return {
        "service_id": "svc",
        "origin_id": "a",
        "destination_id": "b",
        "amount": amount,
        "valid_from": "2026-01-01",
        "valid_to": "2035-12-31",
        "dataset_source": "DEMO",
    }


def test_draft_requires_independent_approval_and_changes_live_fare(managed):
    client, engine, approver = managed
    batch = stage(
        client,
        [
            {
                "resource": "fares",
                "id": "fare",
                "operation": "UPDATE",
                "values": fare_values(),
            }
        ],
    )
    with Session(engine) as s:
        assert s.get(Fare, "fare").amount == 100
    action(client, batch, "publish", expected=409)
    batch = action(client, batch, "validate")
    action(client, batch, "approve", expected=403)
    batch = action(client, batch, "approve", approver)
    batch = action(client, batch, "publish")
    with Session(engine) as s:
        assert s.get(Fare, "fare").amount == 125
    rows = client.get(
        "/api/v1/enquiry/next-bus",
        params={"origin": "a", "destination": "b", "at": "2030-01-01T22:00:00+05:30"},
    ).json()["data"]
    assert rows[0]["fare"] == "125.00"
    audit = client.get(
        "/api/v1/admin/data/audit", headers=ROOT, params={"batch_id": batch["id"]}
    ).json()["data"]
    change = next(r for r in audit if r.get("version"))
    assert (
        str(change["previous_values"]["amount"]) == "100"
        and "amount" in change["changed_fields"]
    )
    action(client, batch, "rollback", approver)
    with Session(engine) as s:
        assert s.get(Fare, "fare").amount == 100


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_valid_file_is_staged_then_published_and_searchable(managed, extension):
    client, _engine, approver = managed
    headers = ["station_id", "name", "dataset_source"]
    if extension == "csv":
        content = (",".join(headers) + "\na,Alpha historical alias,DEMO\n").encode()
    else:
        import openpyxl

        book = openpyxl.Workbook()
        sheet = book.active
        sheet.append(headers)
        sheet.append(["a", "Alpha historical alias", "DEMO"])
        stream = io.BytesIO()
        book.save(stream)
        content = stream.getvalue()
    body = {
        "filename": "aliases." + extension,
        "content_base64": base64.b64encode(content).decode(),
        "operator_id": "op-a",
    }
    response = client.post(
        "/api/v1/admin/imports/files/station-aliases", headers=ROOT, json=body
    )
    assert response.status_code == 201, response.text
    batch = response.json()["data"]
    assert (
        client.get("/api/v1/stations/search", params={"q": "historical alias"}).json()[
            "data"
        ]
        == []
    )
    batch = publish(client, batch, approver)
    assert (
        client.get("/api/v1/stations/search", params={"q": "historical alias"}).json()[
            "data"
        ][0]["id"]
        == "a"
    )
    duplicate = client.post(
        "/api/v1/admin/imports/files/station-aliases", headers=ROOT, json=body
    ).json()["data"]
    assert duplicate["id"] == batch["id"]


@pytest.mark.parametrize(
    "filename,content",
    [
        ("bad.exe", b"x"),
        ("bad.csv", b"name,name\na,b"),
        ("bad.csv", b"\xff"),
        ("bad.xlsx", b"not a zip"),
    ],
)
def test_invalid_files_are_rejected(managed, filename, content):
    client, _, _ = managed
    response = client.post(
        "/api/v1/admin/imports/files/stations",
        headers=ROOT,
        json={
            "filename": filename,
            "content_base64": base64.b64encode(content).decode(),
        },
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "values",
    [
        {"code": "ONLY"},
        {"code": "X", "name": "X", "dataset_source": "DEMO", "timezone": "No/SuchZone"},
    ],
)
def test_row_errors_prevent_publication(managed, values):
    client, engine, _ = managed
    batch = stage(client, [{"resource": "stations", "values": values}])
    batch = action(client, batch, "validate")
    assert batch["workflow_state"] == "DRAFT" and batch["validation_report"]["errors"]
    action(client, batch, "publish", expected=409)
    with Session(engine) as s:
        assert s.scalar(select(Station).where(Station.code == values["code"])) is None


def test_invalid_rows_roll_back_the_whole_batch(managed):
    client, engine, _ = managed
    batch = stage(
        client,
        [
            {
                "resource": "stations",
                "values": {"code": "NEW", "name": "New", "dataset_source": "DEMO"},
            },
            {
                "resource": "stations",
                "values": {
                    "code": "DEMO-A",
                    "name": "Conflicting",
                    "dataset_source": "DEMO",
                },
            },
        ],
    )
    batch = action(client, batch, "validate")
    assert batch["validation_report"]["errors"]
    with Session(engine) as s:
        assert s.scalar(select(Station).where(Station.code == "NEW")) is None


def test_operator_scopes_and_editor_permissions(managed):
    client, _, _ = managed
    user = client.post(
        "/api/v1/admin/data/users",
        headers=ROOT,
        json={"username": "editor-b", "role": "EDITOR", "operator_ids": ["op-b"]},
    ).json()["data"]
    editor = {"Authorization": "Bearer " + user["token"]}
    assert client.get("/api/v1/admin/schedules", headers=editor).json()["data"] == []
    assert (
        client.get(
            "/api/v1/admin/schedules?operator_id=op-a", headers=editor
        ).status_code
        == 403
    )
    batch = stage(
        client,
        [
            {
                "resource": "fares",
                "id": "fare",
                "operation": "UPDATE",
                "values": fare_values(),
            }
        ],
    )
    assert (
        client.get(
            f"/api/v1/admin/imports/batches/{batch['id']}", headers=editor
        ).status_code
        == 403
    )
    action(client, batch, "approve", editor, 403)
    assert (
        client.post(
            "/api/v1/admin/data/users",
            headers=editor,
            json={"username": "attack", "role": "APPROVER", "operator_ids": ["op-a"]},
        ).status_code
        == 403
    )


def test_rollback_does_not_overwrite_later_changes(managed):
    client, _, approver = managed
    first = publish(
        client,
        stage(
            client,
            [
                {
                    "resource": "fares",
                    "id": "fare",
                    "operation": "UPDATE",
                    "values": fare_values(120),
                }
            ],
        ),
        approver,
    )
    publish(
        client,
        stage(
            client,
            [
                {
                    "resource": "fares",
                    "id": "fare",
                    "operation": "UPDATE",
                    "values": fare_values(130),
                }
            ],
        ),
        approver,
    )
    action(client, first, "rollback", approver, 409)


def test_conflicting_fare_dates_are_rejected(managed):
    client, _, _ = managed
    batch = stage(client, [{"resource": "fares", "values": fare_values(80)}])
    batch = action(client, batch, "validate")
    assert "overlap" in str(batch["validation_report"]["errors"]).lower()


def test_stop_times_are_overnight_and_publish_immediately(managed):
    client, _, approver = managed
    commands = [
        {
            "resource": "stop-times",
            "values": {
                "service_id": "svc",
                "stop_id": stop,
                "arrival_offset": offset,
                "departure_offset": offset,
                "dataset_source": "DEMO",
            },
        }
        for stop, offset in [("stop-a", 0), ("stop-b", 180)]
    ]
    publish(client, stage(client, commands), approver)
    rows = client.get(
        "/api/v1/enquiry/next-bus",
        params={"origin": "a", "destination": "b", "at": "2030-01-01T22:00:00+05:30"},
    ).json()["data"]
    assert rows[0]["departure"].startswith("2030-01-01T23:00")
    assert rows[0]["arrival"].startswith("2030-01-02T02:00")


@pytest.mark.parametrize(
    "kind,operates,details",
    [
        ("CANCELLED_SERVICE", False, {}),
        ("CHANGED_DEPARTURE", True, {"departure_minutes": 1300}),
        ("BOARDING_RESTRICTION", True, {"boarding_restricted_stop_ids": ["stop-a"]}),
        ("PARTIAL_STOP_CANCELLATION", True, {"cancelled_stop_ids": ["stop-b"]}),
    ],
)
def test_approved_exceptions_change_passenger_results(managed, kind, operates, details):
    client, _, approver = managed
    batch = stage(
        client,
        [
            {
                "resource": "calendar-exceptions",
                "values": {
                    "service_id": "svc",
                    "service_date": "2030-01-01",
                    "operates": operates,
                    "exception_type": kind,
                    "reason": "DEMO verified disruption",
                    "details": details,
                    "dataset_source": "DEMO",
                },
            }
        ],
    )
    publish(client, batch, approver)
    rows = client.get(
        "/api/v1/enquiry/next-bus",
        params={"origin": "a", "destination": "b", "at": "2030-01-01T20:00:00+05:30"},
    ).json()["data"]
    if kind == "CHANGED_DEPARTURE":
        assert rows[0]["departure"].startswith("2030-01-01T21:40")
    else:
        assert not any(r["service_date"] == "2030-01-01" for r in rows)


def test_template_is_generated_from_actual_schema(managed):
    client, _, _ = managed
    result = client.get("/api/v1/admin/data/templates/stop-times", headers=ROOT).json()[
        "data"
    ]
    assert "arrival_offset" in result["required_columns"]
    assert "FICTIONAL" in result["example_label"]
    csv = client.get("/api/v1/admin/data/templates/stations?format=csv", headers=ROOT)
    assert "dataset_source" in csv.text and "DEMO" in csv.text


def test_explicit_mapping_and_utf8_station_data(managed):
    client, engine, approver = managed
    text = "Code,Station label,Source\nUTF8,తిరుపతి format example,DEMO\n"
    response = client.post(
        "/api/v1/admin/imports/files/stations",
        headers=ROOT,
        json={
            "filename": "utf8.csv",
            "content_base64": base64.b64encode(text.encode()).decode(),
            "operator_id": "op-a",
        },
    )
    batch = response.json()["data"]
    mapped = client.put(
        f"/api/v1/admin/imports/batches/{batch['id']}/mapping",
        headers=ROOT,
        json={
            "revision": batch["revision"],
            "mapping": {
                "Code": "code",
                "Station label": "name",
                "Source": "dataset_source",
            },
        },
    )
    assert mapped.status_code == 200, mapped.text
    publish(client, mapped.json()["data"], approver)
    with Session(engine) as s:
        assert s.scalar(select(Station).where(Station.code == "UTF8")).name.startswith(
            "తిరుపతి"
        )


def test_stale_approval_is_rejected_after_other_publication(managed):
    client, _, approver = managed
    old = action(
        client,
        stage(
            client,
            [
                {
                    "resource": "fares",
                    "id": "fare",
                    "operation": "UPDATE",
                    "values": fare_values(110),
                }
            ],
        ),
        "validate",
    )
    old = action(client, old, "approve", approver)
    publish(
        client,
        stage(
            client,
            [
                {
                    "resource": "fares",
                    "id": "fare",
                    "operation": "UPDATE",
                    "values": fare_values(120),
                }
            ],
        ),
        approver,
    )
    action(client, old, "publish", expected=409)


def test_editor_cannot_stage_another_operators_change(managed):
    client, _, _ = managed
    user = client.post(
        "/api/v1/admin/data/users",
        headers=ROOT,
        json={"username": "writer-b", "role": "EDITOR", "operator_ids": ["op-b"]},
    ).json()["data"]
    result = client.put(
        "/api/v1/admin/fares/fare",
        headers={"Authorization": "Bearer " + user["token"]},
        json=fare_values(),
    )
    assert result.status_code == 403, result.text


def test_route_bundle_add_and_sequence_validation(managed):
    client, _, approver = managed
    commands = [
        {
            "resource": "routes",
            "id": "r2",
            "values": {
                "operator_id": "op-a",
                "code": "DEMO-R2",
                "dataset_source": "DEMO",
            },
        },
        {
            "resource": "stops",
            "values": {
                "route_id": "r2",
                "station_id": "a",
                "sequence": 0,
                "offset_minutes": 0,
                "distance_km": 0,
                "dataset_source": "DEMO",
            },
        },
        {
            "resource": "stops",
            "values": {
                "route_id": "r2",
                "station_id": "b",
                "sequence": 1,
                "offset_minutes": 1500,
                "distance_km": 100,
                "boarding": False,
                "alighting": True,
                "dataset_source": "DEMO",
            },
        },
    ]
    publish(client, stage(client, commands), approver)
    with Session(managed[1]) as s:
        assert (
            s.scalar(
                select(Stop).where(Stop.route_id == "r2", Stop.sequence == 1)
            ).offset_minutes
            == 1500
        )
    commands[0]["id"] = "r3"
    commands[0]["values"]["code"] = "DEMO-R3"
    for command in commands[1:]:
        command["values"]["route_id"] = "r3"
    commands[1]["values"]["offset_minutes"] = 1600
    invalid = action(client, stage(client, commands), "validate")
    assert invalid["validation_report"]["errors"]


def test_invalid_stop_time_order_and_calendar_overlap(managed):
    client, _, approver = managed
    commands = [
        {
            "resource": "stop-times",
            "values": {
                "service_id": "svc",
                "stop_id": stop,
                "arrival_offset": arr,
                "departure_offset": dep,
                "dataset_source": "DEMO",
            },
        }
        for stop, arr, dep in [("stop-a", 0, 200), ("stop-b", 100, 120)]
    ]
    invalid = action(client, stage(client, commands), "validate")
    assert invalid["validation_report"]["errors"]
    calendar = {
        "service_id": "svc",
        "valid_from": "2030-01-01",
        "valid_to": "2030-02-01",
        "weekdays": "0123456",
        "departure_minutes": 900,
        "dataset_source": "DEMO",
    }
    publish(
        client, stage(client, [{"resource": "calendars", "values": calendar}]), approver
    )
    calendar["valid_from"] = "2030-01-15"
    assert action(
        client,
        stage(client, [{"resource": "calendars", "values": calendar}]),
        "validate",
    )["validation_report"]["errors"]


def test_demo_source_cannot_be_relabelled(managed):
    client, _, _ = managed
    values = fare_values()
    values["dataset_source"] = "OFFICIAL"
    assert action(
        client,
        stage(
            client,
            [
                {
                    "resource": "fares",
                    "id": "fare",
                    "operation": "UPDATE",
                    "values": values,
                }
            ],
        ),
        "validate",
    )["validation_report"]["errors"]


def test_xlsx_formulas_are_rejected(managed):
    import openpyxl

    client, _, _ = managed
    workbook = openpyxl.Workbook()
    workbook.active.append(["code", "name", "dataset_source"])
    workbook.active.append(["X", "=1+1", "DEMO"])
    stream = io.BytesIO()
    workbook.save(stream)
    response = client.post(
        "/api/v1/admin/imports/files/stations",
        headers=ROOT,
        json={
            "filename": "formula.xlsx",
            "content_base64": base64.b64encode(stream.getvalue()).decode(),
        },
    )
    assert response.status_code == 422


def test_large_import_limits_and_row_level_errors(managed):
    import os

    from app.import_files import parse_file

    with pytest.raises(ValueError, match="10000"):
        parse_file(
            "too-many.csv",
            ("code,name,dataset_source\n" + "X,X,DEMO\n" * 10001).encode(),
        )
    client, engine, _ = managed
    rows = int(os.getenv("RTC_IMPORT_TEST_ROWS", "500"))
    assert 1 <= rows <= 10000
    commands = [
        {
            "resource": "stations",
            "values": {
                "code": f"LARGE-{i}",
                "name": f"DEMO station {i}",
                "dataset_source": "DEMO",
            },
        }
        for i in range(rows)
    ]
    batch = action(client, stage(client, commands), "validate")
    assert batch["validation_report"]["valid_rows"] == rows
    assert batch["validation_report"]["preview_truncated"]
    with Session(engine) as s:
        assert s.scalar(select(Station).where(Station.code == "LARGE-0")) is None
    invalid = action(
        client,
        stage(
            client,
            [
                {"resource": "stations", "values": {"code": "M1"}},
                {"resource": "stations", "values": {"code": "M2"}},
            ],
        ),
        "validate",
    )
    assert {e["row"] for e in invalid["validation_report"]["errors"]} == {2, 3}


def test_global_independent_approver_handles_shared_records(managed):
    client, _, _ = managed
    user = client.post(
        "/api/v1/admin/data/users",
        headers=ROOT,
        json={"username": "global-reviewer", "role": "APPROVER", "global_scope": True},
    ).json()["data"]
    reviewer = {"Authorization": "Bearer " + user["token"]}
    batch = stage(
        client,
        [
            {
                "resource": "stations",
                "values": {
                    "code": "GLOBAL",
                    "name": "Shared station DEMO",
                    "dataset_source": "DEMO",
                },
            }
        ],
        operator=None,
    )
    publish(client, batch, reviewer)
    users = client.get("/api/v1/admin/data/users", headers=ROOT).json()["data"]
    assert all("password_hash" not in row and "token" not in row for row in users)
    client.delete("/api/v1/admin/data/users/" + user["id"], headers=ROOT)
    assert client.get("/api/v1/admin/stations", headers=reviewer).status_code == 401


def test_rule_fare_preview_is_transactional_and_decimal(managed):
    client, engine, approver = managed
    commands = [
        {
            "resource": "fare-tables",
            "id": "table",
            "values": {
                "operator_id": "op-a",
                "category_id": "cat",
                "name": "DEMO tariff",
                "fare_class": "DEMO",
                "dataset_source": "DEMO",
            },
        },
        {
            "resource": "fare-rules",
            "values": {
                "table_id": "table",
                "per_km": "1.23",
                "minimum": "10.00",
                "flat_surcharge": "2.00",
                "percent_surcharge": "5",
                "valid_from": "2030-01-01",
                "valid_to": "2030-12-31",
                "dataset_source": "DEMO",
            },
        },
    ]
    batch = action(client, stage(client, commands), "validate")
    assert not batch["validation_report"]["errors"]
    preview = client.post(
        "/api/v1/admin/data/fare-preview",
        headers=ROOT,
        json={
            "batch_id": batch["id"],
            "service_id": "svc",
            "origin_id": "a",
            "destination_id": "b",
            "travel_date": "2030-01-01",
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"]["total"] == "107.00"
    from app.records import FareRule

    with Session(engine) as s:
        assert s.scalar(select(FareRule)) is None
    batch = action(client, batch, "approve", approver)
    action(client, batch, "publish")
    actual = client.get(
        "/api/v1/enquiry/next-bus",
        params={"origin": "a", "destination": "b", "at": "2030-01-01T22:00:00+05:30"},
    ).json()["data"]
    assert actual[0]["fare"] == "107.00"


def test_calendar_preview_and_copy_service(managed):
    client, engine, approver = managed
    result = client.post(
        "/api/v1/admin/data/copy-service/svc",
        headers=ROOT,
        json={"number": "DEMO-COPY"},
    )
    assert result.status_code == 200, result.text
    publish(client, result.json()["data"], approver)
    with Session(engine) as s:
        assert (
            s.scalar(select(Service).where(Service.number == "DEMO-COPY")) is not None
        )
    result = client.get(
        "/api/v1/admin/data/calendar-preview/svc?start=2030-01-01&end=2030-01-07",
        headers=ROOT,
    )
    assert len(result.json()["data"]) == 7 and all(
        r["operates"] for r in result.json()["data"]
    )


def test_platform_reassignment_and_audit(managed):
    client, _, approver = managed
    commands = [
        {
            "resource": "data-sources",
            "id": "src",
            "values": {
                "operator_id": "op-a",
                "code": "DEMO-SOURCE",
                "name": "DEMO operations",
                "is_demo": True,
                "is_official": False,
                "dataset_source": "DEMO",
            },
        },
        {
            "resource": "trips",
            "id": "trip",
            "values": {
                "service_id": "svc",
                "service_date": "2030-01-01",
                "status": "scheduled",
                "dataset_source": "DEMO",
            },
        },
        {
            "resource": "bays",
            "id": "bay1",
            "values": {"station_id": "a", "code": "1", "dataset_source": "DEMO"},
        },
        {
            "resource": "bays",
            "id": "bay2",
            "values": {"station_id": "a", "code": "2", "dataset_source": "DEMO"},
        },
        {
            "resource": "platform-assignments",
            "id": "platform",
            "values": {
                "trip_id": "trip",
                "bay_id": "bay1",
                "source_id": "src",
                "verified": True,
                "effective_at": "2030-01-01T00:00:00Z",
                "expires_at": "2030-01-02T23:59:00Z",
                "dataset_source": "DEMO",
            },
        },
    ]
    publish(client, stage(client, commands), approver)
    params = {"trip_id": "trip", "station": "a", "at": "2030-01-01T12:00:00Z"}
    assert (
        client.get("/api/v1/enquiry/platform", params=params).json()["data"]["bay"]
        == "1"
    )
    values = commands[-1]["values"].copy()
    values["bay_id"] = "bay2"
    publish(
        client,
        stage(
            client,
            [
                {
                    "resource": "platform-assignments",
                    "id": "platform",
                    "operation": "UPDATE",
                    "values": values,
                }
            ],
        ),
        approver,
    )
    assert (
        client.get("/api/v1/enquiry/platform", params=params).json()["data"]["bay"]
        == "2"
    )
    events = client.get(
        "/api/v1/admin/data/audit", headers=ROOT, params={"entity_id": "platform"}
    ).json()["data"]
    assert any(e.get("previous_values", {}).get("bay_id") == "bay1" for e in events)


def test_exports_are_scoped_and_do_not_leak_credentials(managed):
    client, _, _ = managed
    response = client.get(
        "/api/v1/admin/data/export/schedules?operator_id=op-a", headers=ROOT
    )
    assert (
        response.status_code == 200
        and "record_id" in response.text
        and "DEMO-1" in response.text
    )
    assert (
        client.get("/api/v1/admin/data/export/admin_users", headers=ROOT).status_code
        == 404
    )


@pytest.mark.parametrize(
    "resource,values",
    [
        ("fares", fare_values(-1)),
        (
            "schedules",
            {
                "operator_id": "op-a",
                "category_id": "cat",
                "route_id": "route",
                "number": "DEMO-1",
                "departure_minutes": 1200,
                "valid_from": "2030-01-01",
                "valid_to": "2031-01-01",
                "dataset_source": "DEMO",
            },
        ),
    ],
)
def test_negative_fare_and_duplicate_service_block_publication(
    managed, resource, values
):
    client, _, _ = managed
    result = action(
        client, stage(client, [{"resource": resource, "values": values}]), "validate"
    )
    assert result["validation_report"]["errors"]


@pytest.mark.parametrize(
    "kind", ["ADDED_SERVICE", "FESTIVAL_EXTRA", "TEMPORARY_SUSPENSION"]
)
def test_special_exception_types_are_real_calendar_changes(managed, kind):
    client, engine, reviewer = managed
    with Session(engine) as s, s.begin():
        s.get(Service, "svc").weekdays = "6"
    operates = kind != "TEMPORARY_SUSPENSION"
    batch = stage(
        client,
        [
            {
                "resource": "calendar-exceptions",
                "values": {
                    "service_id": "svc",
                    "service_date": "2030-01-01",
                    "operates": operates,
                    "exception_type": kind,
                    "reason": "DEMO seasonal exception",
                    "dataset_source": "DEMO",
                },
            }
        ],
    )
    publish(client, batch, reviewer)
    preview = client.get(
        "/api/v1/admin/data/calendar-preview/svc?start=2030-01-01&end=2030-01-01",
        headers=ROOT,
    ).json()["data"]
    assert preview[0]["operates"] is operates


def test_route_variant_diversion_and_copy(managed):
    client, engine, reviewer = managed
    with Session(engine) as s, s.begin():
        s.get(Stop, "stop-b").sequence = 2
        s.add(Station(id="mid", code="MID", name="DEMO middle", dataset_source="DEMO"))
        s.flush()
        s.add(
            Stop(
                id="stop-mid",
                route_id="route",
                station_id="mid",
                sequence=1,
                offset_minutes=60,
                distance_km=50,
                dataset_source="DEMO",
            )
        )
    commands = [
        {
            "resource": "route-variants",
            "id": "variant",
            "values": {
                "route_id": "route",
                "name": "DEMO bypass",
                "dataset_source": "DEMO",
            },
        }
    ]
    commands.extend(
        {
            "resource": "variant-stops",
            "values": {
                "variant_id": "variant",
                "stop_id": stop,
                "dataset_source": "DEMO",
            },
        }
        for stop in ("stop-a", "stop-b")
    )
    publish(client, stage(client, commands), reviewer)
    batch = stage(
        client,
        [
            {
                "resource": "calendar-exceptions",
                "values": {
                    "service_id": "svc",
                    "service_date": "2030-01-01",
                    "operates": True,
                    "exception_type": "ROUTE_DIVERSION",
                    "reason": "DEMO alternate approved path",
                    "details": {"variant_id": "variant"},
                    "dataset_source": "DEMO",
                },
            }
        ],
    )
    publish(client, batch, reviewer)
    request = {
        "intent": "ROUTE_STOPS",
        "service_id": "svc",
        "travel_date": "2030-01-01",
        "at": "2030-01-01T12:00:00Z",
    }
    stops = client.post("/api/v1/enquiry", json=request).json()["results"]
    assert [s["id"] for s in stops] == ["stop-a", "stop-b"]
    copied = client.post(
        "/api/v1/admin/data/copy-variant/variant",
        headers=ROOT,
        json={"name": "DEMO copied bypass"},
    )
    assert copied.status_code == 200, copied.text
    publish(client, copied.json()["data"], reviewer)


def test_trip_override_is_date_specific_and_operator_fare_reuses_decimal(managed):
    client, _, reviewer = managed
    commands = [
        {
            "resource": "trips",
            "id": "trip-override",
            "values": {
                "service_id": "svc",
                "service_date": "2030-01-01",
                "status": "scheduled",
                "dataset_source": "DEMO",
            },
        },
        {
            "resource": "trip-fare-overrides",
            "values": {
                "trip_id": "trip-override",
                "origin_id": "a",
                "destination_id": "b",
                "amount": "199.99",
                "dataset_source": "DEMO",
            },
        },
    ]
    publish(client, stage(client, commands), reviewer)
    day = client.post(
        "/api/v1/admin/data/fare-preview",
        headers=ROOT,
        json={
            "service_id": "svc",
            "origin_id": "a",
            "destination_id": "b",
            "travel_date": "2030-01-01",
        },
    ).json()["data"]
    next_day = client.post(
        "/api/v1/admin/data/fare-preview",
        headers=ROOT,
        json={
            "service_id": "svc",
            "origin_id": "a",
            "destination_id": "b",
            "travel_date": "2030-01-02",
        },
    ).json()["data"]
    assert day["total"] == "199.99" and next_day["total"] == "100.00"


def test_failed_import_reports_are_persisted_and_visible_in_quality(managed):
    client, _, _ = managed
    batch = action(
        client,
        stage(client, [{"resource": "stations", "values": {"code": "MISSING"}}]),
        "validate",
    )
    stored = client.get(
        f"/api/v1/admin/imports/batches/{batch['id']}", headers=ROOT
    ).json()["data"]
    assert (
        stored["validation_error_count"] == 1
        and stored["validation_report"]["errors"][0]["row"] == 2
    )
    quality = client.get("/api/v1/admin/ui/data-quality", headers=ROOT).json()["data"]
    assert (
        next(c for c in quality["checks"] if c["code"] == "FAILED_STAGED_IMPORT")[
            "count"
        ]
        == 1
    )


def test_concurrent_publications_are_serialized_without_lost_updates(managed):
    from concurrent.futures import ThreadPoolExecutor

    client, engine, reviewer = managed
    batches = []
    for amount in (111, 122):
        batch = action(
            client,
            stage(
                client,
                [
                    {
                        "resource": "fares",
                        "id": "fare",
                        "operation": "UPDATE",
                        "values": fare_values(amount),
                    }
                ],
            ),
            "validate",
        )
        batches.append(action(client, batch, "approve", reviewer))

    def commit(batch):
        return client.post(
            f"/api/v1/admin/imports/batches/{batch['id']}/publish",
            headers=ROOT,
            json={"revision": batch["revision"]},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(commit, batches))
    assert sorted(results) == [200, 409]
    with Session(engine) as session:
        assert session.get(Fare, "fare").amount in (111, 122)


def test_apsrtc_setup_is_configuration_only_and_unpublished(managed):
    client, engine, reviewer = managed
    response = client.post("/api/v1/admin/data/apsrtc-configuration", headers=ROOT)
    assert response.status_code == 200, response.text
    batch = response.json()["data"]
    assert batch["workflow_state"] == "DRAFT"
    with Session(engine) as session:
        assert session.scalar(select(Operator).where(Operator.code == "APSRTC")) is None
    batch = action(client, batch, "validate")
    assert not batch["validation_report"]["errors"]
    changes = batch["validation_report"]["preview"]
    assert len(changes) == 14
    assert all(row["resource"] in {"operators", "bus-types"} for row in changes)
    action(client, batch, "approve", reviewer, expected=403)
