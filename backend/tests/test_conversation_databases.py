"""Selected-segment memory and concurrent turn checks on both real DB engines."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app.domain import Fare, Service
from app.nlp_seed import seed_nlp
from app.taxonomy_seed import seed_taxonomy
from sqlalchemy.orm import Session
from test_data_management import managed as _managed

managed = _managed


def test_database_selection_replay_and_row_lock(managed):
    client, engine, _ = managed
    seed_nlp(engine)
    seed_taxonomy(engine)
    with Session(engine) as session, session.begin():
        source = session.get(Service, "svc")
        session.add(
            Service(
                id="svc-two",
                number="DEMO-2",
                route_id=source.route_id,
                operator_id=source.operator_id,
                category_id=source.category_id,
                departure_minutes=1390,
                valid_from=source.valid_from,
                valid_to=source.valid_to,
                dataset_source="DEMO",
            )
        )
        session.flush()
        session.add(
            Fare(
                service_id="svc-two",
                origin_id="a",
                destination_id="b",
                amount=205,
                valid_from=source.valid_from,
                valid_to=source.valid_to,
                dataset_source="DEMO",
            )
        )
    owner = uuid4().hex + uuid4().hex
    previous = None

    def ask(text):
        nonlocal previous
        body = {
            "text": text,
            "station_context": "a",
            "language": "en",
            "owner_token": owner,
            "client_message_id": str(uuid4()),
            "expected_state_version": previous["context"]["state_version"]
            if previous
            else 0,
        }
        if previous:
            body["session_id"] = previous["session_id"]
        response = client.post("/api/v1/conversation/message", json=body)
        assert response.status_code == 200, response.text
        previous = response.json()
        assert client.post("/api/v1/conversation/message", json=body).json() == previous
        return previous

    first = ask("Next bus to Beta tomorrow?")
    assert len(first["result_set"]) == 2
    selected = ask("2")
    fare = ask("What is the fare?")
    assert fare["session_id"] == first["session_id"]
    assert selected["selected_journey"]["service_id"] == "svc-two"
    assert fare["results"][0]["query"]["segments"][0]["origin"] == "a"
    assert float(fare["results"][0]["results"][0]["amount"]) == 205
    engine.dispose()
    restore = client.post(
        "/api/v1/conversation/state",
        json={"session_id": fare["session_id"], "owner_token": owner},
    )
    assert restore.status_code == 200
    assert restore.json()["selected_journey"]["service_id"] == "svc-two"

    def submit(text):
        return client.post(
            "/api/v1/conversation/message",
            json={
                "session_id": fare["session_id"],
                "text": text,
                "language": "en",
                "owner_token": owner,
                "expected_state_version": 3,
                "client_message_id": str(uuid4()),
            },
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, ["Only AC", "Tomorrow"])) == [200, 409]
    current = client.post(
        "/api/v1/conversation/state",
        json={"session_id": fare["session_id"], "owner_token": owner},
    ).json()
    assert current["state_version"] == 4 and len(current["history"]) == 8
