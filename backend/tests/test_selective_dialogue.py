from app.nlp.inference import EnglishInferenceService
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from sqlalchemy.orm import Session
from test_text_dialogue import NOW
from test_text_dialogue import text_db as _fixture

text_db = _fixture


def test_ood_does_not_fall_back_to_context_or_database(text_db, monkeypatch):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        first = engine.process(
            NLPRequest(
                text="Next bus to Guntur", station_context="DEMO0", language="en"
            ),
            NOW,
        )
        monkeypatch.setattr(
            engine.english_model,
            "predict",
            lambda text: {
                "status": "OUT_OF_SCOPE",
                "intents": [],
                "domain_margin": -0.5,
            },
        )

        def forbidden(*args):
            raise AssertionError("Rejected text reached database enquiry")

        monkeypatch.setattr(engine.orchestrator, "execute", forbidden)
        result = engine.process(
            NLPRequest(
                text="Explain mortgage refinancing in simple terms",
                session_id=first.session_id,
                language="en",
                debug=True,
            ),
            NOW,
        )
        assert result.state == "OUT_OF_SCOPE" and not result.results
        assert result.requires_clarification and not result.intents
        assert result.context["destination"] == first.context["destination"]
        assert result.debug["database_function"] is None
        assert "outside this scope" in result.answer


def test_uncertain_model_result_does_not_become_a_bus_answer(text_db, monkeypatch):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        monkeypatch.setattr(
            engine.english_model,
            "predict",
            lambda text: {"status": "CLARIFICATION_REQUIRED", "intents": []},
        )
        result = engine.process(
            NLPRequest(text="I need some further information please", language="en"),
            NOW,
        )
        assert (
            result.requires_clarification and not result.results and not result.intents
        )


def test_explicit_short_followup_uses_context_before_classifier(text_db, monkeypatch):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        first = engine.process(
            NLPRequest(
                text="Next bus to Guntur", station_context="DEMO0", language="en"
            ),
            NOW,
        )

        def forbidden(text):
            raise AssertionError(
                "Short explicit correction was sent to standalone classifier"
            )

        monkeypatch.setattr(engine.english_model, "predict", forbidden)
        result = engine.process(
            NLPRequest(text="No, Tirupati", session_id=first.session_id, language="en"),
            NOW,
        )
        assert result.context["destination"] != first.context["destination"]


def test_facade_does_not_replace_rejection_with_rule_guess(text_db, monkeypatch):
    with Session(text_db) as session:
        service = EnglishInferenceService(session)
        monkeypatch.setattr(
            service.engine.english_model,
            "predict",
            lambda text: {"status": "OUT_OF_SCOPE", "intents": []},
        )
        monkeypatch.setattr(
            service,
            "classify_multiple_intents",
            lambda text: (_ for _ in ()).throw(AssertionError("Rejection bypassed")),
        )
        assert service.classify_intent("Unrelated request")["status"] == "OUT_OF_SCOPE"
