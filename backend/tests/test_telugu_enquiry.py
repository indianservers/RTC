from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.demo import enrich
from app.domain import Base, database
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from app.nlp.telugu import render_results
from app.nlp_seed import seed_nlp
from app.seed import seed


@pytest.fixture
def telugu_db(tmp_path):
    engine = database("sqlite:///" + str(tmp_path / "telugu.db"))
    Base.metadata.create_all(engine)
    seed(engine)
    enrich(engine)
    seed_nlp(engine)
    return engine


@pytest.mark.parametrize("question,intent", [
    ("గుంటూరుకు బస్సు ఎప్పుడు", "NEXT_BUS"),
    ("గుంటూరుకు మొదటి బస్సు ఎప్పుడు", "FIRST_BUS"),
    ("గుంటూరుకు చివరి బస్సు ఎప్పుడు", "LAST_BUS"),
    ("గుంటూరుకు టికెట్ ధర ఎంత", "TICKET_FARE"),
])
def test_telugu_passenger_question(telugu_db, question, intent):
    with Session(telugu_db) as session:
        reply = RTCNLPEngine(session).process(
            NLPRequest(text=question, language="te", station_context="DEMO0"),
            datetime(2026, 11, 8, tzinfo=UTC), persist=False,
        )
        assert intent in reply.intents
        assert reply.context.get("destination")
        assert reply.results and reply.results[0]["results"]
        assert any("\u0c00" <= char <= "\u0c7f" for char in reply.answer)


def test_telugu_platform_and_missing_information():
    assert "4" in render_results([{"intent": "BUS_PLATFORM", "results": [{"bay": "4"}]}])
    assert "నిర్ధారించబడలేదు" in render_results([{"intent": "BUS_PLATFORM", "results": [{}]}])
    answer = render_results([{"intent": "NEXT_BUS", "results": [{
        "service_number": "226V", "departure": "2026-11-08T10:20:00+05:30",
        "fare": 55, "dataset_source": "DEMO",
    }]}])
    assert "10:20" in answer and "55" in answer and "ప్రదర్శన" in answer
    assert "ప్లాట్" not in answer
