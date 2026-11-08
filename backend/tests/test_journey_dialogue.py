from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from sqlalchemy.orm import Session
from test_text_dialogue import NOW
from test_text_dialogue import text_db as _fixture

text_db = _fixture


def test_full_itinerary_dialogue(text_db):
    with Session(text_db) as s:
        engine = RTCNLPEngine(s)
        first = engine.process(
            NLPRequest(
                text="How can I reach Tirupati?", station_context="DEMO0", language="en"
            ),
            now=NOW,
        )
        assert first.context["journey_mode"] and first.context["journey_candidates"]
        ids = {r["journey_id"] for r in first.context["journey_candidates"]}
        selected = engine.process(
            NLPRequest(text="First option", session_id=first.session_id, language="en"),
            now=NOW,
        )
        assert selected.context.get("selected_itinerary"), (
            selected.answer,
            len(first.context["journey_candidates"]),
            selected.context,
        )
        assert selected.context["selected_itinerary"]["journey_id"] in ids
        cheapest = engine.process(
            NLPRequest(
                text="Cheapest instead", session_id=first.session_id, language="en"
            ),
            now=NOW,
        )
        assert cheapest.context["journey_ranking"] == "LOWEST_FARE"
        assert all(
            r["total_fare"] is not None for r in cheapest.context["journey_candidates"]
        )
        tomorrow = engine.process(
            NLPRequest(text="Tomorrow", session_id=first.session_id, language="en"),
            now=NOW,
        )
        assert tomorrow.context["travel_date"] == "2026-11-09"
        assert not tomorrow.context.get("selected_itinerary")
        assert tomorrow.context["journey_candidates"]
