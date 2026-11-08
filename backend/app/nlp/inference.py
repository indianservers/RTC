"""Reusable facade over the existing text/conversation engine, not a second engine."""

from datetime import datetime

from sqlalchemy import select

from ..catalog import Context, Intent
from .components import IntentClassifier, LanguageNormalizer
from .content import NLPContentRepository
from .entities import RTCEntityExtractor
from .pipeline import NLPRequest, RTCNLPEngine

RTCConversationEngine = RTCNLPEngine


class EnglishInferenceService:
    def __init__(self, session):
        self.session = session
        self.engine = RTCConversationEngine(session)

    def classify_multiple_intents(self, text):
        request = NLPRequest(text=text, language="en")
        normalized = LanguageNormalizer().normalize(request.text)
        return IntentClassifier(NLPContentRepository(self.session).rules()).classify(
            normalized
        )

    def classify_intent(self, text):
        try:
            prediction = self.engine.english_model.predict(text)
        except (ValueError, OSError, KeyError, ImportError):
            prediction = {"status": "NOT_READY", "intents": []}
        if prediction["status"] == "KNOWN":
            return {
                "status": "KNOWN",
                "intent": prediction["intents"][0],
                "source": "APPROVED_LOCAL_SVM",
                "decision_margin": prediction.get("decision_margin"),
                "probability": None,
            }
        if prediction["status"] == "OUT_OF_SCOPE":
            return {
                "status": "OUT_OF_SCOPE",
                "intent": None,
                "source": "APPROVED_LOCAL_SVM",
                "domain_margin": prediction.get("domain_margin"),
                "probability": None,
            }
        if prediction["status"] == "CLARIFICATION_REQUIRED":
            return {
                "status": "CLARIFICATION_REQUIRED",
                "candidates": [],
                "decision_margin": prediction.get("decision_margin"),
                "probability": None,
            }
        intents = self.classify_multiple_intents(text)
        if len(intents) == 1:
            return {
                "status": "KNOWN",
                "intent": intents[0],
                "source": "DETERMINISTIC_RULES",
                "probability": None,
            }
        return {
            "status": "CLARIFICATION_REQUIRED",
            "candidates": intents,
            "probability": None,
        }

    def extract_entities(self, text):
        request = NLPRequest(text=text, language="en")
        return RTCEntityExtractor(self.session).extract(
            LanguageNormalizer().normalize(request.text)
        )

    def identify_dialogue_act(self, text):
        normalized = LanguageNormalizer().normalize(NLPRequest(text=text).text)
        rows = self.session.scalars(
            select(Intent).where(
                Intent.registry_kind == "DIALOGUE_ACT", Intent.active.is_(True)
            )
        )
        return [
            r.code
            for r in rows
            if r.taxonomy
            and normalized
            in [
                LanguageNormalizer().normalize(x)
                for x in r.taxonomy.get("examples", [])
            ]
        ]

    def interpret_query(self, request: NLPRequest, now: datetime):
        return self.engine.process(request, now, persist=False)

    def process_conversation(self, request: NLPRequest, now: datetime):
        return self.engine.process(request, now, persist=True)

    def reset_session(self, session_id: str, owner_token=None):
        context = self.session.scalar(
            select(Context).where(Context.session_id == session_id)
        )
        if context:
            from .session_access import check_owner

            check_owner(context.values, owner_token)
            context.values = (
                {"_owner_hash": context.values["_owner_hash"]}
                if "_owner_hash" in context.values
                else {}
            )
        return {"reset": True}
