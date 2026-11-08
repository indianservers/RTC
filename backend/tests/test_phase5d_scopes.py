"""Feedback/review scope and erasure on actual SQLite and PostgreSQL."""

from uuid import uuid4

from app.nlp_seed import seed_nlp
from app.taxonomy_seed import seed_taxonomy
from test_data_management import ROOT
from test_data_management import managed as _managed

managed = _managed


def test_feedback_review_operator_scope_and_erasure(managed, monkeypatch):
    client, engine, _ = managed
    seed_nlp(engine)
    seed_taxonomy(engine)
    monkeypatch.setenv("RTC_FEEDBACK_RETAIN_TEXT", "1")
    owner = uuid4().hex + uuid4().hex
    first = client.post(
        "/api/v1/conversation/message",
        json={
            "text": "Next bus to Beta tomorrow?",
            "station_context": "a",
            "language": "en",
            "owner_token": owner,
        },
    ).json()
    assert first["result_set"]
    saved = client.post(
        "/api/v1/conversation/feedback",
        json={
            "session_id": first["session_id"],
            "message_id": first["message_id"],
            "owner_token": owner,
            "category": "WRONG_INTENT",
            "retain_question": True,
        },
    )
    assert saved.status_code == 200, saved.text
    identifier = saved.json()["id"]

    def editor(operator):
        created = client.post(
            "/api/v1/admin/data/users",
            headers=ROOT,
            json={
                "username": "review-" + operator + uuid4().hex,
                "role": "EDITOR",
                "operator_ids": [operator],
            },
        )
        assert created.status_code == 201
        return {"Authorization": "Bearer " + created.json()["data"]["token"]}

    other = editor("op-b")
    own = editor("op-a")
    assert not client.get("/api/v1/admin/nlp/reviews", headers=other).json()["data"]
    assert client.get("/api/v1/admin/nlp/export", headers=other).text == ""
    assert (
        client.post(
            f"/api/v1/admin/nlp/reviews/{identifier}/anonymize",
            headers=other,
            json={"expected_version": 1},
        ).status_code
        == 403
    )
    queue = client.get("/api/v1/admin/nlp/reviews", headers=own).json()["data"]
    assert len(queue) == 1 and queue[0]["operator_id"] == "op-a"
    assert (
        client.post(
            f"/api/v1/admin/nlp/reviews/{identifier}/review",
            headers=own,
            json={
                "expected_version": 1,
                "status": "APPROVED_FOR_TRAINING",
                "error_group": "MODEL_ERROR",
                "corrected_intent": "NEXT_BUS",
                "notes": "DEMO fixture reviewer labels",
            },
        ).status_code
        == 403
    )
    approved = client.post(
        f"/api/v1/admin/nlp/reviews/{identifier}/review",
        headers=ROOT,
        json={
            "expected_version": 1,
            "status": "APPROVED_FOR_TRAINING",
            "error_group": "MODEL_ERROR",
            "corrected_intent": "NEXT_BUS",
            "notes": "DEMO fixture reviewer labels",
        },
    )
    assert approved.status_code == 200, approved.text
    exported = client.get("/api/v1/admin/nlp/export", headers=own)
    assert (
        "NEXT_BUS" in exported.text
        and owner not in exported.text
        and first["session_id"] not in exported.text
    )
    assert exported.headers["cache-control"] == "no-store"
    deletion = client.delete(
        f"/api/v1/admin/nlp/reviews/{identifier}?expected_version=2", headers=ROOT
    )
    assert deletion.status_code == 200
    assert client.get("/api/v1/admin/nlp/export", headers=own).text == ""
    record = client.get("/api/v1/admin/nlp/reviews", headers=own).json()["data"][0]
    assert (
        record["deleted"] and "text" not in record and not record["training_eligible"]
    )
