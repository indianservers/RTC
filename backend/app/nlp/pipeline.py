import re
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from sqlalchemy import select

from ..catalog import Context, Conversation
from ..domain import Category, Service, Station
from ..engine import EnquiryRequest, RTCEnquiryEngine
from ..operations import Trip
from . import text_support
from .components import IntentClassifier, LanguageNormalizer, TemporalParser
from .content import NLPContentRepository
from .english_model import EnglishIntentModel
from .entities import RTCEntityExtractor

ROOT = Path(__file__).resolve().parents[3]


class NLPRequest(BaseModel):
    session_id: str | None = None
    text: str = Field(min_length=1, max_length=2000)
    language: Literal["auto", "te", "en", "te-Latn", "mixed"] = "auto"
    station_context: str | None = None
    operator: str | None = None
    debug: bool = False


class NLPResponse(BaseModel):
    session_id: str | None = None
    language: str
    intents: list[str]
    entities: dict
    context: dict
    state: str
    requires_clarification: bool
    answer: str
    results: list = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: float
    debug: dict = Field(default_factory=dict)


class ConversationManager:
    def __init__(self, session):
        self.session = session

    def load(self, identifier, now):
        conversation = (
            self.session.get(Conversation, identifier) if identifier else None
        )
        context = (
            self.session.scalar(select(Context).where(Context.session_id == identifier))
            if conversation
            else None
        )
        if (
            context
            and datetime.fromisoformat(
                context.values.get("expires_at", "1970-01-01T00:00:00+00:00")
            )
            > now
        ):
            return conversation, context, dict(context.values)
        conversation = Conversation(id=str(uuid4()), language="auto")
        self.session.add(conversation)
        self.session.flush()
        context = Context(session_id=conversation.id, values={})
        self.session.add(context)
        return conversation, context, {}

    def save(self, context, values, now):
        values["expires_at"] = (now + timedelta(minutes=15)).isoformat()
        context.values = dict(values)
        self.session.flush()


class RTCQueryOrchestrator:
    def __init__(self, session):
        self.engine = RTCEnquiryEngine(session)

    def execute(self, intents, slots, at):
        results = []
        for intent in intents[:3]:
            if intent not in text_support.SUPPORTED:
                results.append(
                    {
                        "intent": intent,
                        "status": "UNSUPPORTED",
                        "query": {},
                        "results": [],
                        "warnings": [],
                    }
                )
                continue
            query = EnquiryRequest(
                intent=intent,
                via=slots.get("via"),
                origin=slots.get("origin"),
                destination=slots.get("destination"),
                travel_date=slots["travel_date"],
                at=at,
                filters=slots.get("filters", {}),
                service_id=slots.get("service_id"),
                trip_id=slots.get("trip_id"),
                station=slots.get("origin"),
                passengers=slots.get("passengers", 1),
                service_number=slots.get("service_number"),
            )
            result = self.engine.enquire(query)
            encoded = result.model_dump(mode="json")
            for row in encoded["results"]:
                if row.get("service_id"):
                    service = self.engine.session.get(Service, row["service_id"])
                    category = (
                        self.engine.session.get(Category, service.category_id)
                        if service
                        else None
                    )
                    if category:
                        row["category_name"] = category.name
                if row.get("station_id"):
                    station = self.engine.session.get(Station, row["station_id"])
                    if station:
                        row["station_name"] = station.name
                if not row.get("dataset_source") and slots.get("service_id"):
                    service = self.engine.session.get(Service, slots["service_id"])
                    if service:
                        row["dataset_source"] = service.dataset_source
            if not encoded["results"]:
                sources = set(
                    self.engine.session.scalars(
                        select(Service.dataset_source)
                        .where(Service.active.is_(True))
                        .distinct()
                    )
                )
                if sources and sources <= {"DEMO", "SYNTHETIC"}:
                    encoded["dataset_source"] = "DEMO"
            results.append(encoded)
            candidates = [r for r in encoded["results"] if r.get("service_id")]
            if candidates:
                slots["candidates"] = candidates
            if (
                result.results
                and isinstance(result.results[0], dict)
                and (
                    len(result.results) == 1
                    or intent
                    in {
                        "NEXT_BUS",
                        "FIRST_BUS",
                        "LAST_BUS",
                        "CHEAPEST_BUS",
                        "FASTEST_BUS",
                    }
                )
            ):
                selected = result.results[0]
                if selected.get("service_id"):
                    slots["service_id"] = selected["service_id"]
                if selected.get("trip_id"):
                    slots["trip_id"] = selected["trip_id"]
        return results


class RTCResponseEngine:
    def __init__(self, content):
        self.content = content

    def render(self, results, language):
        if language == "en":
            return text_support.render(results)
        rows = next((r["results"] for r in results if r["results"]), [])
        if not rows:
            return self.content.render("NO_RESULTS", language)
        row = rows[0]
        if "departure" in row:
            status = (
                "ESTIMATED" if row.get("departure_kind") == "estimated" else "SCHEDULED"
            )
            answer = self.content.render(status, language, row)
            if row.get("fare") is not None:
                answer += " " + self.content.render("FARE", language, row)
            if row.get("dataset_source") == "DEMO":
                answer = self.content.render("DEMO_NOTICE", language) + " " + answer
            return answer.strip()
        return self.content.render("DETAILS", language)


class RTCDialogueManager:
    def missing(self, slots):
        if not slots.get("destination"):
            return "AWAITING_DESTINATION", ""
        if not slots.get("origin"):
            return "AWAITING_ORIGIN", ""
        return None


class RTCNLPEngine:
    def __init__(self, session):
        self.session = session
        self.normalizer = LanguageNormalizer()
        self.content = NLPContentRepository(session)
        self.classifier = IntentClassifier(self.content.rules())
        self.english_model = EnglishIntentModel(ROOT)
        self.extractor = RTCEntityExtractor(session)
        self.temporal = TemporalParser()
        self.conversations = ConversationManager(session)
        self.orchestrator = RTCQueryOrchestrator(session)

    def process(self, request: NLPRequest, now: datetime, persist=True):
        start = perf_counter()
        if now.tzinfo is None:
            raise ValueError("Aware current time required")
        self.classifier = IntentClassifier(self.content.rules())
        text = self.normalizer.normalize(request.text)
        language = (
            self.normalizer.language(text)
            if request.language == "auto"
            else request.language
        )
        conversation, context, loaded = (
            self.conversations.load(request.session_id, now)
            if persist
            else (None, None, {})
        )
        slots = deepcopy(loaded)
        previous = deepcopy(slots)
        state, answer, clarify = "ANSWERING", "", False
        results, intents, entities, timings = [], [], {}, {}
        prediction = {"status": "RULES"}
        try:
            tick = perf_counter()
            entities = self.extractor.extract(text)
            timings["entity_extraction_ms"] = (perf_counter() - tick) * 1000
            if request.station_context and not slots.get("origin"):
                resolved = self.orchestrator.engine.resolver.resolve(
                    request.station_context
                )
                if resolved["status"] != "KNOWN":
                    raise ValueError("Which boarding station do you mean?")
                slots["origin"] = resolved["candidates"][0]["id"]
            if request.operator:
                slots.setdefault("filters", {})["operator"] = request.operator
            if text in ("reset", "/reset", "new enquiry", "కొత్త ప్రశ్న"):
                slots = {}
                answer = self.content.render("HELP", language)
            else:
                station = (
                    self.session.get(Station, slots.get("origin"))
                    if slots.get("origin")
                    else None
                )
                local = now.astimezone(
                    ZoneInfo(station.timezone if station else "Asia/Kolkata")
                )
                old = (
                    slots.get("origin"),
                    slots.get("destination"),
                    slots.get("travel_date"),
                    deepcopy(slots.get("filters", {})),
                )
                extracted = entities.get("filters", {})
                clear = bool(
                    re.search(r"any (?:bus )?type|clear filters|any category", text)
                )
                if clear:
                    slots["filters"] = {
                        k: v
                        for k, v in slots.get("filters", {}).items()
                        if k == "operator"
                    }
                slots["filters"] = {**slots.get("filters", {}), **extracted}
                slots.update({k: v for k, v in entities.items() if k != "filters"})
                temporal = self.temporal.parse(text, local)
                date_change = bool(
                    re.search(
                        r"today|tomorrow|repu|రేపు|ellundi|ఎల్లుండి|\d{4}-\d{2}-\d{2}",
                        text,
                    )
                )
                if "travel_date" not in slots or date_change:
                    slots["travel_date"] = temporal["travel_date"]
                periods = {
                    "morning": (6, 12),
                    "afternoon": (12, 17),
                    "evening": (17, 21),
                    "night": (21, 24),
                }
                period = next(
                    (p for p in periods if p in text),
                    "morning" if temporal["morning"] else None,
                )
                if date_change or period:
                    slots.pop("time_window", None)
                    for key in ("after", "before"):
                        slots["filters"].pop(key, None)
                if period:
                    slots["time_window"] = period
                new = (
                    slots.get("origin"),
                    slots.get("destination"),
                    slots.get("travel_date"),
                    slots["filters"],
                )
                if old != new or period:
                    for key in (
                        "service_id",
                        "trip_id",
                        "service_number",
                        "candidates",
                    ):
                        if key not in entities:
                            slots.pop(key, None)
                if re.search(r"not that bus|not that one", text):
                    for key in ("service_id", "trip_id", "service_number"):
                        slots.pop(key, None)
                    raise ValueError(
                        "Which service would you like instead? Choose a result number or service number."
                    )
                selection_handled = False
                selection = re.fullmatch(
                    r"(?:the )?(first|second|third|fourth|fifth|\d+)(?: one| bus| service)?[.!?]*",
                    text,
                )
                if selection and (
                    slots.get("candidates") or text not in ("first bus", "first")
                ):
                    ranks = {
                        "first": 1,
                        "second": 2,
                        "third": 3,
                        "fourth": 4,
                        "fifth": 5,
                    }
                    n = ranks.get(
                        selection[1], int(selection[1]) if selection[1].isdigit() else 0
                    )
                    candidates = slots.get("candidates", [])
                    if not 1 <= n <= min(5, len(candidates)):
                        raise ValueError(
                            "Which listed service number would you like to select?"
                        )
                    selection_handled = True
                    chosen = candidates[n - 1]
                    slots["service_id"] = chosen["service_id"]
                    slots.pop("trip_id", None)
                    if chosen.get("trip_id"):
                        slots["trip_id"] = chosen["trip_id"]
                    answer = (
                        "Selected service " + chosen.get("service_number", str(n)) + "."
                    )
                tick = perf_counter()
                intents = text_support.classify_extra(
                    text, self.classifier.classify(text), self.session
                )
                if any(
                    i in intents
                    for i in (
                        "CHEAPEST_BUS",
                        "FASTEST_BUS",
                        "NEXT_BUS",
                        "FIRST_BUS",
                        "LAST_BUS",
                        "TICKET_FARE",
                    )
                ) and not re.search(
                    r"\band (?:is|are|does|do|which|what|when|how)\b", text
                ):
                    modifiers = {
                        "AC_BUS_AVAILABILITY",
                        "NON_AC_AVAILABILITY",
                        "SLEEPER_BUS_AVAILABILITY",
                        "SEATER_BUS_AVAILABILITY",
                    }
                    intents = [i for i in intents if i not in modifiers]
                if selection_handled:
                    intents = []
                if (
                    not intents
                    and not selection_handled
                    and language == "en"
                    and not re.search(r"weather|cricket|politic|joke|recipe", text)
                ):
                    try:
                        prediction = self.english_model.predict(text)
                        if prediction["status"] == "KNOWN":
                            codes = {
                                r["code"]: r.get("backend_code") or r["code"]
                                for r in text_support.registry(self.session)
                            }
                            intents = [
                                codes.get(i, i)
                                for i in prediction["intents"]
                                if i in codes or i in text_support.SUPPORTED
                            ]
                    except (ValueError, OSError, KeyError, ImportError):
                        prediction = {"status": "NOT_READY"}
                if slots["filters"].get("ac") is False:
                    intents = [
                        "NON_AC_AVAILABILITY" if i == "AC_BUS_AVAILABILITY" else i
                        for i in intents
                    ]
                if slots["filters"].get("sleeper") is False:
                    intents = [
                        "SEATER_BUS_AVAILABILITY"
                        if i == "SLEEPER_BUS_AVAILABILITY"
                        else i
                        for i in intents
                    ]
                updated = (
                    bool({k: v for k, v in entities.items() if k != "filters"})
                    or extracted
                    or date_change
                    or period
                    or clear
                )
                if not intents and updated:
                    intents = [
                        "NEXT_BUS" if clear else slots.get("last_intent", "NEXT_BUS")
                    ]
                if not intents and text in ("that bus", "this bus"):
                    if not slots.get("service_id"):
                        raise ValueError("Which service do you mean?")
                    answer = "Ask about the selected service's fare, stops or status."
                timings["intent_inference_ms"] = (perf_counter() - tick) * 1000
                if text in ("hello", "hi", "నమస్తే", "thanks", "thank you", "help"):
                    answer = self.content.render("HELP", language)
                    intents = []
                elif not intents and not answer:
                    state, clarify = "IDLE", True
                    answer = self.content.render("IDLE", language)
                elif intents:
                    absent = text_support.missing(intents, slots)
                    if absent:
                        slots["last_intent"] = intents[0]
                        state, clarify = absent, True
                        answer = self.content.render(state, language)
                        if not answer and state in (
                            "AWAITING_SERVICE",
                            "AWAITING_OPERATOR",
                            "AWAITING_VIA",
                        ):
                            answer = {
                                "AWAITING_SERVICE": "Which service do you mean? Choose a listed bus or give its service number.",
                                "AWAITING_OPERATOR": "Which RTC operator do you mean?",
                                "AWAITING_VIA": "Which intermediate station should the bus pass through?",
                            }[state]
                    else:
                        if slots.get("service_number") and not slots.get("service_id"):
                            matches = list(
                                self.session.scalars(
                                    select(Service).where(
                                        Service.number.ilike(slots["service_number"]),
                                        Service.active.is_(True),
                                    )
                                )
                            )
                            if len(matches) != 1:
                                raise ValueError(
                                    "Which service number do you mean? It must match one active service."
                                )
                            slots["service_id"] = matches[0].id
                        if slots.get("service_id") and not slots.get("trip_id"):
                            trips = list(
                                self.session.scalars(
                                    select(Trip).where(
                                        Trip.service_id == slots["service_id"],
                                        Trip.service_date
                                        == date.fromisoformat(slots["travel_date"]),
                                        Trip.active.is_(True),
                                    )
                                )
                            )
                            if len(trips) == 1:
                                slots["trip_id"] = trips[0].id
                        query_at = (
                            local
                            if slots["travel_date"] == local.date().isoformat()
                            else datetime.combine(
                                date.fromisoformat(slots["travel_date"]),
                                datetime.min.time(),
                                local.tzinfo,
                            )
                        )
                        if slots.get("time_window"):
                            lo, hi = periods[slots["time_window"]]
                            window = datetime.combine(
                                date.fromisoformat(slots["travel_date"]),
                                datetime.min.time(),
                                local.tzinfo,
                            )
                            query_at = max(query_at, window + timedelta(hours=lo))
                            slots["filters"]["before"] = (
                                window + timedelta(hours=hi)
                            ).isoformat()
                        bound = re.search(
                            r"\b(after|before)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
                            text,
                        )
                        if bound:
                            hour, minute = int(bound[2]), int(bound[3] or 0)
                            if (
                                not 0 <= hour <= 23
                                or minute > 59
                                or bound[4]
                                and not 1 <= hour <= 12
                            ):
                                raise ValueError("What valid time do you mean?")
                            if bound[4]:
                                hour = hour % 12 + (12 if bound[4] == "pm" else 0)
                            slots["filters"][bound[1]] = (
                                datetime.combine(
                                    date.fromisoformat(slots["travel_date"]),
                                    datetime.min.time(),
                                    local.tzinfo,
                                )
                                .replace(hour=hour, minute=minute)
                                .isoformat()
                            )
                        searches = {
                            "NEXT_BUS",
                            "FIRST_BUS",
                            "LAST_BUS",
                            "CHEAPEST_BUS",
                            "FASTEST_BUS",
                            "BUSES_BETWEEN",
                            "CONNECTING_BUSES",
                            "AC_BUS_AVAILABILITY",
                            "NON_AC_AVAILABILITY",
                            "SLEEPER_BUS_AVAILABILITY",
                            "SEATER_BUS_AVAILABILITY",
                        }
                        if searches.intersection(intents):
                            slots.pop("service_id", None)
                            slots.pop("trip_id", None)
                        tick = perf_counter()
                        results = self.orchestrator.execute(intents, slots, query_at)
                        timings["database_lookup_ms"] = (perf_counter() - tick) * 1000
                        if any(
                            r["status"]
                            in ("DISAMBIGUATION_REQUIRED", "UNKNOWN_STATION")
                            for r in results
                        ):
                            state, clarify = "AWAITING_STATION_CLARIFICATION", True
                            answer = self.content.render(state, language)
                        else:
                            answer = RTCResponseEngine(self.content).render(
                                results, language
                            )
                            if not any(r["results"] for r in results):
                                state = "NO_RESULTS"
                        slots["last_intent"] = intents[0]
        except ValueError as exc:
            if not re.search(r"not that bus|not that one", text):
                slots = deepcopy(previous)
            state, clarify, answer = "CLARIFICATION_REQUIRED", True, str(exc)
        if persist:
            self.conversations.save(context, slots, now)
        elapsed = (perf_counter() - start) * 1000
        debug = (
            {
                "input": request.text,
                "normalized_text": text,
                "predicted_intents": intents,
                "prediction": prediction,
                "rule_score": 1
                if intents and prediction["status"] == "RULES"
                else None,
                "extracted_entities": entities,
                "previous_context": previous,
                "applied_context": deepcopy(slots),
                "database_function": "RTCEnquiryEngine.enquire" if results else None,
                "queries": [r.get("query", {}) for r in results],
                "matching_service_ids": list(
                    dict.fromkeys(
                        row["service_id"]
                        for r in results
                        for row in r["results"]
                        if row.get("service_id")
                    )
                ),
                "sources": [
                    {
                        "source": row.get("dataset_source"),
                        "freshness": row.get("status"),
                        "recorded_at": row.get("recorded_at"),
                    }
                    for r in results
                    for row in r["results"]
                ],
                "response_template": [r["intent"] + ":" + r["status"] for r in results]
                or [state],
                "timings_ms": timings,
                "processing_ms": elapsed,
            }
            if request.debug
            else {}
        )
        return NLPResponse(
            session_id=conversation.id if conversation else None,
            language=language,
            intents=intents,
            entities=entities,
            context=slots,
            state=state,
            requires_clarification=clarify,
            answer=answer,
            results=results,
            warnings=[
                "Offline local inference; rule scores are not calibrated probabilities."
            ],
            duration_ms=elapsed,
            debug=debug,
        )
