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
from .entities import AmbiguousStation, RTCEntityExtractor
from .planner import ExecutionPlanner
from .references import ReferentialResolver, StaleResult, stable_results
from .session_access import check_owner, public_context, token_hash
from .state import ContextOperation, ContextUpdateEngine, ConversationState

ROOT = Path(__file__).resolve().parents[3]


class NLPRequest(BaseModel):
    session_id: str | None = None
    text: str = Field(min_length=1, max_length=2000)
    language: Literal["auto", "te", "en", "te-Latn", "mixed"] = "auto"
    station_context: str | None = None
    operator: str | None = None
    debug: bool = False
    owner_token: str | None = Field(
        default=None, min_length=32, max_length=256, repr=False
    )


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
    context_changes: list[dict] = Field(default_factory=list)


class ConversationManager:
    def __init__(self, session):
        self.session = session

    def load(self, identifier, now, owner_token=None):
        conversation = (
            self.session.get(Conversation, identifier) if identifier else None
        )
        context = (
            self.session.scalar(select(Context).where(Context.session_id == identifier))
            if conversation
            else None
        )
        if context:
            check_owner(context.values, owner_token)
        if (
            context
            and datetime.fromisoformat(
                context.values.get("expires_at", "1970-01-01T00:00:00+00:00")
            )
            > now
        ):
            values = dict(context.values)
            if owner_token:
                values.setdefault("_owner_hash", token_hash(owner_token))
            return conversation, context, values
        conversation = Conversation(id=str(uuid4()), language="auto")
        self.session.add(conversation)
        self.session.flush()
        context = Context(session_id=conversation.id, values={})
        self.session.add(context)
        return (
            conversation,
            context,
            ({"_owner_hash": token_hash(owner_token)} if owner_token else {}),
        )

    def save(self, context, values, now):
        values["session_id"] = context.session_id
        values["revision"] = int(context.values.get("revision", 0)) + 1
        values["last_activity_at"] = now.isoformat()
        ConversationState.model_validate(values)
        values["expires_at"] = (now + timedelta(minutes=15)).isoformat()
        context.values = dict(values)
        self.session.flush()


class RTCQueryOrchestrator:
    def __init__(self, session):
        self.engine = RTCEnquiryEngine(session)

    def execute(self, intents, slots, at):
        results = []
        planner = ExecutionPlanner()
        primary = None
        for intent in planner.plan(intents):
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
            journey_mode = intent in {"CONNECTING_BUSES", "ALTERNATIVE_ROUTES"} or (
                slots.get("journey_mode") and intent in planner.journey_intents
            )
            if journey_mode:
                from ..journey import JourneyConstraints, JourneyPlanner

                ranking = {
                    "CHEAPEST_BUS": "LOWEST_FARE",
                    "FARE_COMPARISON": "LOWEST_FARE",
                    "FASTEST_BUS": "EARLIEST_ARRIVAL",
                }.get(intent, slots.get("journey_ranking", "EARLIEST_ARRIVAL"))
                constraints = JourneyConstraints(
                    origin=query.origin,
                    destination=query.destination,
                    earliest_departure=at,
                    filters=query.filters,
                    passengers=query.passengers,
                    max_transfers=slots.get("journey_max_transfers", 2),
                    transfer_station=slots.get("transfer_station"),
                    maximum_wait_minutes=slots.get("journey_max_wait", 180),
                    ranking=ranking,
                )
                journeys = JourneyPlanner(self.engine.session).search(constraints)
                rows = []
                for itinerary in journeys.itineraries:
                    row = itinerary.model_dump(mode="json")
                    row.update(
                        departure=row["departure_at"],
                        arrival=row["arrival_at"],
                        fare=row["total_fare"],
                        result_id=row["journey_id"],
                        dataset_source="DEMO"
                        if set(row["sources"]) <= {"DEMO", "SYNTHETIC"}
                        else "LOCAL",
                    )
                    rows.append(row)
                slots["journey_mode"] = True
                slots["journey_constraints"] = constraints.model_dump(mode="json")
                slots["journey_ranking"] = ranking
                slots["journey_candidates"] = rows
                slots["candidates"] = rows
                slots.pop("selected_itinerary", None)
                encoded = {
                    "intent": intent,
                    "status": "KNOWN" if rows else "NO_RESULTS",
                    "query": query.model_dump(mode="json"),
                    "results": rows,
                    "warnings": journeys.warnings,
                    "executor": "JourneyPlanner.search",
                    "pagination": journeys.pagination,
                }
                results.append(encoded)
                continue
            projected = planner.project(intent, primary, query, slots.get("service_id"))
            if projected is None:
                result = self.engine.enquire(query)
                encoded = result.model_dump(mode="json")
            else:
                from ..engine import EnquiryResponse

                result = EnquiryResponse.model_validate(projected)
                encoded = projected
            if intent in planner.journey_intents:
                primary = encoded
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
            if intent in planner.journey_intents or (
                candidates and not slots.get("candidates")
            ):
                slots["candidates"] = stable_results(candidates)
                slots["result_revision"] = int(slots.get("revision", 0)) + 1
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
                    if (
                        slots.get("service_id") != selected["service_id"]
                        or slots.get("selection_status") != "USER_CONFIRMED"
                    ):
                        slots["selection_status"] = "SYSTEM_QUERY_DEFAULT"
                    slots["service_id"] = selected["service_id"]
                    service = self.engine.session.get(Service, selected["service_id"])
                    slots["selected_route_id"] = service.route_id if service else None
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
            self.conversations.load(request.session_id, now, request.owner_token)
            if persist
            else (None, None, {})
        )
        slots = deepcopy(loaded)
        pending = slots.get("station_clarification")
        if pending:
            choice = next(
                (
                    c
                    for c in pending["choices"]
                    if text.casefold() in {c["code"].casefold(), c["id"].casefold()}
                ),
                None,
            )
            if choice:
                text = pending["query"].replace(
                    pending["term"], choice["code"].casefold()
                )
                slots.pop("station_clarification", None)
        operations = []
        previous = deepcopy(slots)
        slots.setdefault("slot_origins", deepcopy(slots.get("slot_sources", {})))
        slots["slot_sources"] = {
            key: "INHERITED" for key in slots.get("slot_sources", {})
        }
        state, answer, clarify = "ANSWERING", "", False
        results, intents, entities, timings = [], [], {}, {}
        prediction = {"status": "RULES"}
        temporal = {}
        try:
            tick = perf_counter()
            if re.search(r"only ac until|only .* until", text):
                raise ValueError(
                    "Leg-specific category constraints are not supported yet. Please specify a requirement for the whole journey."
                )
            for pattern, slot, mapping in (
                (
                    r"(?:maximum|max) (one|two|zero|[0-2]) transfers?",
                    "journey_max_transfers",
                    {"one": 1, "two": 2, "zero": 0},
                ),
                (
                    r"(?:maximum|max) (?:waiting|wait)(?: time)? (\d+) minutes?",
                    "journey_max_wait",
                    {},
                ),
            ):
                match = re.search(pattern, text)
                if match:
                    value = mapping.get(
                        match[1], int(match[1]) if match[1].isdigit() else 0
                    )
                    operation = ContextOperation(op="SET_SLOT", slot=slot, value=value)
                    slots = ContextUpdateEngine().apply(slots, operation)
                    slots["journey_mode"] = True
                    operations.append(operation.model_dump())
            if re.search(
                r"don.t change buses|no transfers|direct only|show direct buses", text
            ):
                slots.pop("transfer_station", None)
                operation = ContextOperation(
                    op="SET_SLOT", slot="journey_max_transfers", value=0
                )
                slots = ContextUpdateEngine().apply(slots, operation)
                slots["journey_mode"] = True
                operations.append(operation.model_dump())
            if re.search(r"fewest transfers|fewer transfers", text):
                slots["journey_mode"] = True
                slots["journey_ranking"] = "FEWEST_TRANSFERS"
                text = "connecting buses"
            entities = self.extractor.extract(text)
            if re.search(r"chang(?:e|ing) at", text) and entities.get("destination"):
                entities["transfer_station"] = entities.pop("destination")
                slots["journey_mode"] = True
                slots["journey_max_transfers"] = max(
                    1, slots.get("journey_max_transfers", 2)
                )
                text = "connecting buses"

            same_service = bool(re.search(r"same (?:one|bus|service) tomorrow", text))
            if same_service:
                if not slots.get("service_id"):
                    raise ValueError(
                        "Which recurring service should I check for tomorrow?"
                    )
                entities["service_id"] = slots["service_id"]
            timings["entity_extraction_ms"] = (perf_counter() - tick) * 1000
            context_tick = perf_counter()
            if re.search(
                r"forget (?:the )?(?:price|fare) limit|remove (?:the )?(?:price|fare) limit",
                text,
            ):
                operation = ContextOperation(op="CLEAR_SLOT", slot="max_fare")
                slots = ContextUpdateEngine().apply(slots, operation)
                operations.append(operation.model_dump())
                text = "clear price limit"
            if request.station_context and not slots.get("origin"):
                resolved = self.orchestrator.engine.resolver.resolve(
                    request.station_context
                )
                if resolved["status"] != "KNOWN":
                    raise ValueError("Which boarding station do you mean?")
                slots["origin"] = resolved["candidates"][0]["id"]
                slots.setdefault("slot_sources", {})["origin"] = "SYSTEM_DEFAULT"
                slots.setdefault("slot_origins", {})["origin"] = "SYSTEM_DEFAULT"
                slots["current_station"] = slots["origin"]
            if request.operator or request.operator == "":
                operation = ContextOperation(
                    op="SET_SLOT" if request.operator else "CLEAR_SLOT",
                    slot="operator",
                    value=request.operator,
                )
                slots = ContextUpdateEngine().apply(slots, operation)
                operations.append(operation.model_dump())
            if text in ("reset", "/reset", "new enquiry", "కొత్త ప్రశ్న"):
                slots = (
                    {"_owner_hash": slots["_owner_hash"]}
                    if "_owner_hash" in slots
                    else {}
                )
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
                slots.setdefault("filters", {})
                if re.search(r"cheaper category", text):
                    slots["filters"].pop("category", None)
                clear = bool(
                    re.search(r"any (?:bus )?type|clear filters|any category", text)
                )
                if clear:
                    slots["filters"] = {
                        k: v
                        for k, v in slots.get("filters", {}).items()
                        if k in {"operator", "accessible"}
                    }
                for key, value in {
                    **extracted,
                    **{k: v for k, v in entities.items() if k != "filters"},
                }.items():
                    target = (
                        slots.get("filters", {})
                        if key in ContextUpdateEngine.filter_slots
                        else slots
                    )
                    operation = ContextOperation(
                        op="REPLACE_SLOT" if key in target else "SET_SLOT",
                        slot=key,
                        value=value,
                    )
                    slots = ContextUpdateEngine().apply(slots, operation)
                    operations.append(operation.model_dump())
                temporal = self.temporal.parse(text, local, slots.get("travel_date"))
                date_change = temporal.get("explicit_relative", False) or bool(
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
                if "same time tomorrow" in text:
                    previous_bounds = {
                        k: datetime.fromisoformat(v)
                        for k, v in slots.get("filters", {}).items()
                        if k in ("after", "before", "arrival_after", "arrival_before")
                        and v
                    }
                    if previous_bounds:
                        anchor = min(v.date() for v in previous_bounds.values())
                        delta = date.fromisoformat(temporal["travel_date"]) - anchor
                        temporal["filters"] = {
                            k: (v + delta).isoformat()
                            for k, v in previous_bounds.items()
                        }
                if date_change or period:
                    slots.pop("time_window", None)
                    for key in ("after", "before", "arrival_after", "arrival_before"):
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
                if re.fullmatch(
                    r"(?:the )?(?:cheaper one|cheapest one|fastest one|previous one|this one)[.!?]*",
                    text,
                ):
                    index = ReferentialResolver().resolve(text, slots)
                    text = f"the {index + 1} one"
                refined = False
                if re.fullmatch(
                    r"remove (?:the )?first (?:option|bus)|any other[?!.]*", text
                ):
                    rows = slots.get("candidates", [])
                    if not rows:
                        raise ValueError(
                            "Request a current list before refining options."
                        )
                    remaining = (
                        rows[1:]
                        if text.startswith("remove")
                        else [
                            r
                            for r in rows
                            if r.get("service_id") != slots.get("service_id")
                        ]
                    )
                    operation = ContextOperation(
                        op="REFINE_RESULTS", slot="candidates", value=remaining
                    )
                    slots = ContextUpdateEngine().apply(slots, operation)
                    operations.append(operation.model_dump())
                    if not any(
                        r.get("service_id") == slots.get("service_id")
                        for r in remaining
                    ):
                        slots.pop("service_id", None)
                        slots.pop("trip_id", None)
                        slots.pop("selection_status", None)
                    answer = self.content.render(
                        "RESULTS_UPDATED", language, {"count": len(remaining)}
                    )
                    refined = True
                selection_handled = refined
                selection = re.fullmatch(
                    r"(?:select )?(?:the )?(first|second|third|fourth|fifth|\d+)(?: one| bus| service| option)?[.!?]*",
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
                    if chosen.get("journey_id"):
                        from ..journey import JourneyConstraints, JourneyPlanner

                        constraints = JourneyConstraints.model_validate(
                            slots["journey_constraints"]
                        )
                        constraints = JourneyConstraints.model_validate(
                            {
                                **constraints.model_dump(),
                                "earliest_departure": max(
                                    constraints.earliest_departure, now
                                ),
                                "limit": 100,
                                "offset": 0,
                            }
                        )
                        fresh = JourneyPlanner(self.session).search(constraints)
                        selected = next(
                            (
                                i
                                for i in fresh.itineraries
                                if i.journey_id == chosen["journey_id"]
                            ),
                            None,
                        )
                        if selected is None:
                            raise StaleResult(
                                "That itinerary is no longer eligible. Please request updated journey options."
                            )
                        chosen = selected.model_dump(mode="json")
                        chosen.update(
                            departure=chosen["departure_at"],
                            arrival=chosen["arrival_at"],
                            fare=chosen["total_fare"],
                            result_id=chosen["journey_id"],
                        )
                        candidates[n - 1] = chosen
                    if not chosen.get("journey_id"):
                        departure = datetime.fromisoformat(chosen["departure"])
                        refresh = self.orchestrator.engine.enquire(
                            EnquiryRequest(
                                intent="NEXT_BUS",
                                origin=slots["origin"],
                                destination=slots["destination"],
                                at=max(now, departure - timedelta(seconds=1)),
                                travel_date=date.fromisoformat(chosen["service_date"]),
                                service_id=chosen["service_id"],
                                filters=slots.get("filters", {}),
                                limit=100,
                            )
                        )
                        current = next(
                            (
                                r
                                for r in refresh.results
                                if r.get("service_id") == chosen["service_id"]
                                and r.get("departure") == chosen["departure"]
                            ),
                            None,
                        )
                        if current is None:
                            raise StaleResult(
                                "This listed departure changed, departed or is no longer eligible. Request a fresh bus list."
                            )
                        # Keep stable reference metadata while refreshing all database facts.
                        chosen = {
                            **chosen,
                            **refresh.model_dump(mode="json")["results"][
                                refresh.results.index(current)
                            ],
                        }
                        candidates[n - 1] = chosen
                    operation = ContextOperation(op="SELECT_RESULT", value=n - 1)
                    slots = ContextUpdateEngine().apply(slots, operation)
                    operations.append(operation.model_dump())
                    if chosen.get("journey_id"):
                        slots["selected_itinerary"] = chosen
                        slots["selected_leg"] = None
                        answer = f"Selected journey option {n}."
                    else:
                        slots["service_id"] = chosen["service_id"]
                    slots.pop("trip_id", None)
                    if chosen.get("trip_id"):
                        slots["trip_id"] = chosen["trip_id"]
                    if not chosen.get("journey_id"):
                        answer = (
                            "Selected service "
                            + chosen.get("service_number", str(n))
                            + "."
                        )
                timings["context_update_ms"] = (perf_counter() - context_tick) * 1000
                tick = perf_counter()
                intents = text_support.classify_extra(
                    text, self.classifier.classify(text), self.session
                )
                if re.search(
                    r"don.t change buses|no transfers|direct only|show direct buses",
                    text,
                ):
                    intents = ["CONNECTING_BUSES"]
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
                if same_service:
                    intents = ["NEXT_BUS"]
                if selection_handled:
                    intents = []
                if (
                    not intents
                    and not selection_handled
                    and language == "en"
                    and not (
                        slots.get("last_intent")
                        and len(text.split()) <= 5
                        and (
                            any(k != "filters" for k in entities)
                            or extracted
                            or date_change
                            or period
                            or clear
                        )
                    )
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
                if prediction["status"] in ("OUT_OF_SCOPE", "CLARIFICATION_REQUIRED"):
                    raise ValueError(
                        "I can help with RTC bus enquiries; that request appears outside this scope."
                        if prediction["status"] == "OUT_OF_SCOPE"
                        else "Please clarify which bus information you need."
                    )
                clock_match = re.search(
                    r"\b(?:at|around)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text
                )
                if "BUS_AT_TIME" in intents and slots.get("requested_clock"):
                    previous_clock = datetime.fromisoformat(slots["requested_clock"])
                    clock_day = date.fromisoformat(slots["travel_date"])
                    slots["requested_clock"] = previous_clock.replace(
                        year=clock_day.year, month=clock_day.month, day=clock_day.day
                    ).isoformat()
                if "BUS_AT_TIME" in intents and clock_match:
                    hour, minute = int(clock_match[1]), int(clock_match[2] or 0)
                    if (
                        minute > 59
                        or hour > 23
                        or clock_match[3]
                        and not 1 <= hour <= 12
                    ):
                        raise ValueError("Which valid departure time do you mean?")
                    if clock_match[3]:
                        hour = hour % 12 + (12 if clock_match[3] == "pm" else 0)
                    slots["requested_clock"] = (
                        datetime.combine(
                            date.fromisoformat(slots["travel_date"]),
                            datetime.min.time(),
                            local.tzinfo,
                        )
                        .replace(hour=hour, minute=minute)
                        .isoformat()
                    )
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
                    or temporal.get("filters")
                    or clear
                    or operations
                )
                if not intents and updated and not selection_handled:
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
                    if absent == "AWAITING_TIME":
                        raise ValueError(
                            "What departure time should I search around? For example, at 8 PM."
                        )
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
                        if temporal.get("filters"):
                            slots["filters"].update(temporal["filters"])
                            slots["temporal_resolution"] = {
                                **temporal,
                                "original_text": request.text,
                            }
                            if slots["filters"].get("after"):
                                query_at = max(
                                    query_at,
                                    datetime.fromisoformat(slots["filters"]["after"]),
                                )
                        searches = {
                            "NEXT_BUS",
                            "FIRST_BUS",
                            "LAST_BUS",
                            "CHEAPEST_BUS",
                            "FASTEST_BUS",
                            "FARE_COMPARISON",
                            "BUSES_BETWEEN",
                            "CONNECTING_BUSES",
                            "AC_BUS_AVAILABILITY",
                            "NON_AC_AVAILABILITY",
                            "SLEEPER_BUS_AVAILABILITY",
                            "SEATER_BUS_AVAILABILITY",
                        }
                        if searches.intersection(intents) and not same_service:
                            slots.pop("service_id", None)
                            slots.pop("trip_id", None)
                        tick = perf_counter()
                        if "BUS_AT_TIME" in intents:
                            clock_day = date.fromisoformat(slots["travel_date"])
                            query_at = datetime.fromisoformat(
                                slots["requested_clock"]
                            ).replace(
                                year=clock_day.year,
                                month=clock_day.month,
                                day=clock_day.day,
                            )
                            slots["requested_clock"] = query_at.isoformat()
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
        except AmbiguousStation as exc:
            slots = deepcopy(previous)
            slots["station_clarification"] = {
                "query": text,
                "term": exc.term,
                "choices": exc.choices,
            }
            operations = []
            state, clarify, answer = "AWAITING_STATION_CLARIFICATION", True, str(exc)
        except StaleResult as exc:
            slots = deepcopy(previous)
            for field in (
                "service_id",
                "trip_id",
                "selection_status",
                "candidates",
                "journey_candidates",
                "selected_itinerary",
                "selected_leg",
            ):
                slots.pop(field, None)
            operations = []
            state, clarify, answer = "CLARIFICATION_REQUIRED", True, str(exc)
        except ValueError as exc:
            if not re.search(r"not that bus|not that one", text):
                slots = deepcopy(previous)
                operations = []
            state, clarify, answer = (
                (
                    "OUT_OF_SCOPE"
                    if prediction["status"] == "OUT_OF_SCOPE"
                    else "CLARIFICATION_REQUIRED"
                ),
                True,
                str(exc),
            )
        existing_changes = {op.get("slot") for op in operations}
        for name in (
            "travel_date",
            "time_window",
            "after",
            "before",
            "arrival_after",
            "arrival_before",
        ):
            current = (
                slots.get("filters", {})
                if name in ContextUpdateEngine.filter_slots
                else slots
            )
            old = (
                previous.get("filters", {})
                if name in ContextUpdateEngine.filter_slots
                else previous
            )
            if current.get(name) != old.get(name) and name not in existing_changes:
                source: Literal[
                    "EXPLICIT", "INHERITED", "SYSTEM_DEFAULT", "CANDIDATE"
                ] = "EXPLICIT"
                if (
                    name == "travel_date"
                    and not temporal.get("explicit_relative")
                    and not re.search(r"\d{4}-\d{2}-\d{2}", text)
                ):
                    source = (
                        "INHERITED" if previous.get("travel_date") else "SYSTEM_DEFAULT"
                    )
                slots.setdefault("slot_sources", {})[name] = source
                slots.setdefault("slot_origins", {})[name] = (
                    source
                    if source != "INHERITED"
                    else previous.get("slot_origins", {}).get(name, "SYSTEM_DEFAULT")
                )
                operations.append(
                    ContextOperation(
                        op="CLEAR_SLOT"
                        if name not in current
                        else "REPLACE_SLOT"
                        if name in old
                        else "SET_SLOT",
                        slot=name,
                        value=current.get(name),
                        source=source,
                    ).model_dump()
                )
        slots["confirmed_slots"] = [
            k
            for k in slots.get("confirmed_slots", [])
            if k in slots and slots[k] is not None
        ]
        slots["last_intents"] = intents
        slots["pending_clarification"] = state if clarify else None
        slots["last_system_question"] = answer if clarify else None
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
                "previous_context": public_context(previous),
                "applied_context": public_context(deepcopy(slots)),
                "database_function": "; ".join(
                    dict.fromkeys(
                        r.get("executor", "RTCEnquiryEngine.enquire") for r in results
                    )
                )
                if results
                else None,
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
            context=public_context(slots),
            state=state,
            requires_clarification=clarify,
            answer=answer,
            results=results,
            warnings=[
                "Offline local inference; rule scores are not calibrated probabilities."
            ],
            duration_ms=elapsed,
            debug=debug,
            context_changes=operations,
        )
