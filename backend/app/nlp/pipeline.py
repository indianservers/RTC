import hashlib
import json
import os
import re
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import BaseModel, Field, computed_field
from sqlalchemy import delete, select

from ..catalog import Context, Conversation, Message
from ..domain import Category, Service, Station
from ..engine import EnquiryRequest, RTCEnquiryEngine
from ..operations import Trip
from . import text_support
from .telugu import localize_dialogue, normalize_enquiry, render_results as render_telugu_results
from .components import IntentClassifier, LanguageNormalizer, TemporalParser
from .content import NLPContentRepository
from .english_model import EnglishIntentModel
from .entities import AmbiguousStation, RTCEntityExtractor, UnknownCategory
from .planner import ExecutionPlanner
from .references import (
    ReferentialResolver,
    StaleResult,
    conversational_reference,
    selected_enquiry,
    selected_rows,
    stable_results,
)
from .reliability import (
    ConversationRepairEngine,
    ErrorCategory,
    Reliability,
    assess,
    diagnose,
    stale_platform_evidence,
)
from .session_access import check_owner, public_context, token_hash
from .state import ContextOperation, ContextUpdateEngine, ConversationState

ROOT = Path(__file__).resolve().parents[3]


class NLPRequest(BaseModel):
    expected_state_version: int | None = Field(default=None, ge=0)
    client_message_id: str | None = Field(default=None, min_length=8, max_length=120)
    session_mode: Literal["kiosk", "personal"] | None = None
    context_action: ContextOperation | None = None
    session_id: str | None = None
    text: str = Field(min_length=1, max_length=2000)
    language: Literal["auto", "te", "en", "te-Latn", "mixed"] = "auto"
    station_context: str | None = None
    operator: str | None = None
    debug: bool = False
    owner_token: str | None = Field(
        default=None, min_length=32, max_length=256, repr=False
    )


class FollowUpSuggestion(BaseModel):
    id: str
    label: str
    text: str
    context_action: ContextOperation | None = None


class ConversationPlan(BaseModel):
    primary_intent: str | None = None
    secondary_intents: list[str] = Field(default_factory=list)
    shared_entities: dict = Field(default_factory=dict)
    dependencies: list[dict] = Field(default_factory=list)


class AnswerSection(BaseModel):
    intent: str
    title: str
    text: str
    status: str


class NLPResponse(BaseModel):
    feedback_policy: dict = Field(
        default_factory=lambda: {
            "enabled": True,
            "retain_text_enabled": os.getenv("RTC_FEEDBACK_RETAIN_TEXT", "0") == "1",
            "retention_days": min(
                365, max(1, int(os.getenv("RTC_FEEDBACK_RETENTION_DAYS", "30")))
            ),
        }
    )
    reliability: Reliability = Field(default_factory=Reliability)
    source_metadata: list[dict] = Field(default_factory=list)
    dialogue_act: str = "ENQUIRY"
    query_plan: ConversationPlan = Field(default_factory=ConversationPlan)
    answer_sections: list[AnswerSection] = Field(default_factory=list)
    clarification_choices: list[dict] = Field(default_factory=list)
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    follow_up_suggestions: list[FollowUpSuggestion] = Field(default_factory=list)
    data_source: list[str] = Field(default_factory=list)
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

    @computed_field
    def response_text(self) -> str:
        return self.answer

    @computed_field
    def detected_intents(self) -> list[str]:
        return self.intents

    @computed_field
    def detected_entities(self) -> dict:
        return self.entities

    @computed_field
    def current_context(self) -> dict:
        return self.context

    @computed_field
    def selected_journey(self) -> dict | None:
        return self.context.get("selected_itinerary") or self.context.get(
            "selected_result"
        )

    @computed_field
    def result_set(self) -> list[dict]:
        return self.context.get("candidates", [])

    @computed_field
    def pending_clarification(self) -> str | None:
        return self.context.get("pending_clarification")


class ConversationRestoreRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    owner_token: str | None = Field(
        default=None, min_length=32, max_length=256, repr=False
    )


class HistoryMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    sequence_number: int | None


class ConversationStateResponse(BaseModel):
    last_message_id: str | None = None
    data_source: list[str] = Field(default_factory=list)
    session_id: str
    current_context: dict
    selected_journey: dict | None
    result_set: list[dict]
    state_version: int
    history: list[HistoryMessage]


class ConversationManager:
    def __init__(self, session):
        self.session = session

    def expire(self, context):
        self.session.execute(
            delete(Message).where(Message.session_id == context.session_id)
        )
        context.values = {
            key: value
            for key, value in context.values.items()
            if key in {"_owner_hash", "expires_at", "revision"}
        }
        for key in (
            "origin_station_id",
            "destination_station_id",
            "travel_date",
            "passenger_count",
            "last_trip_id",
        ):
            setattr(context, key, None)

    def load(self, identifier, now, owner_token=None, create_identifier=None):
        conversation = (
            self.session.get(Conversation, identifier) if identifier else None
        )
        context = (
            self.session.scalar(
                select(Context)
                .where(Context.session_id == identifier)
                .with_for_update()
            )
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
        if context:
            self.expire(context)
        conversation = Conversation(
            id=create_identifier
            if not conversation and create_identifier
            else str(uuid4()),
            language="auto",
        )
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
        personal = (
            values.get("session_mode") == "personal"
            and os.getenv("RTC_KIOSK_ONLY") != "1"
        )
        ttl = (
            min(10080, max(15, int(os.getenv("RTC_PERSONAL_IDLE_MINUTES", "1440"))))
            if personal
            else 15
        )
        values["expires_at"] = (now + timedelta(minutes=ttl)).isoformat()
        values["state_version"] = values["revision"]
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
            if primary is not None and intent in {
                "TICKET_FARE",
                "GET_FARE",
                "ARRIVAL_TIME",
                "BUS_PLATFORM",
                "BUS_DELAY",
                "SEAT_AVAILABILITY",
                "BUS_VIA_LOCATION",
            }:
                scoped = []
                warnings = []
                queries = []
                for candidate in primary.get("results", [])[
                    : slots.get("result_limit", 5)
                ]:
                    temporary = {**slots, "selected_result": deepcopy(candidate)}
                    if candidate.get("journey_id"):
                        temporary["selected_itinerary"] = deepcopy(candidate)
                    else:
                        temporary.pop("selected_itinerary", None)
                    if intent in {
                        "TICKET_FARE",
                        "GET_FARE",
                        "ARRIVAL_TIME",
                    } and not candidate.get("journey_id"):
                        scoped.append(deepcopy(candidate))
                        continue
                    bound = selected_enquiry(self.engine, intent, temporary, at)
                    if bound is None:
                        leg = candidate.get("legs", [candidate])[0]
                        from ..operations import Trip

                        trip = self.engine.session.scalar(
                            select(Trip).where(
                                Trip.service_id == leg["service_id"],
                                Trip.service_date
                                == date.fromisoformat(str(leg["service_date"])),
                                Trip.active.is_(True),
                            )
                        )
                        bound = self.engine.enquire(
                            EnquiryRequest(
                                intent=intent,
                                service_id=leg["service_id"],
                                trip_id=trip.id if trip else None,
                                origin=leg.get("origin_id", leg.get("origin")),
                                destination=leg.get(
                                    "destination_id", leg.get("destination")
                                ),
                                travel_date=leg["service_date"],
                                at=at,
                                passengers=slots.get("passengers", 1),
                            )
                        ).model_dump(mode="json")
                    for row in bound["results"]:
                        scoped.append(
                            {
                                **row,
                                "related_result_id": candidate.get("result_id"),
                                "service_id": row.get("service_id")
                                or candidate.get("service_id"),
                                "dataset_source": row.get("dataset_source")
                                or candidate.get("dataset_source"),
                            }
                        )
                    warnings.extend(bound.get("warnings", []))
                    queries.append(bound.get("query", {}))
                results.append(
                    {
                        "intent": intent,
                        "status": "KNOWN" if scoped else "NO_RESULTS",
                        "query": {
                            "intent": intent,
                            "origin": slots.get("origin"),
                            "destination": slots.get("destination"),
                            "travel_date": slots["travel_date"],
                            "filters": EnquiryRequest(
                                intent=intent,
                                travel_date=slots["travel_date"],
                                filters=slots.get("filters", {}),
                            ).model_dump(mode="json")["filters"],
                            "bound_queries": queries,
                            "service_ids": [
                                r.get("service_id")
                                for r in primary.get("results", [])[
                                    : slots.get("result_limit", 5)
                                ]
                            ],
                        },
                        "results": scoped,
                        "warnings": warnings,
                        "executor": "ConversationQueryPlanner.bound_results",
                        "pagination": {},
                    }
                )
                continue
            selected = selected_enquiry(self.engine, intent, slots, at)
            if selected is not None:
                results.append(selected)
                continue
            if (
                intent == "NEXT_BUS"
                and slots.get("station_departures")
                and slots.get("origin")
                and not slots.get("destination")
            ):
                from ..domain import Stop

                services = self.engine.session.scalars(
                    select(Service)
                    .join(Stop, Stop.route_id == Service.route_id)
                    .where(
                        Stop.station_id == slots["origin"],
                        Stop.boarding.is_(True),
                        Stop.active.is_(True),
                        Service.active.is_(True),
                    )
                    .distinct()
                    .limit(501)
                )
                found = []
                for service in services:
                    stops = self.engine.enquiry.get_route_stops(
                        service.id, date.fromisoformat(slots["travel_date"])
                    )
                    if not stops or stops[-1].station_id == slots["origin"]:
                        continue
                    response = self.engine.enquire(
                        EnquiryRequest(
                            intent="NEXT_BUS",
                            origin=slots["origin"],
                            destination=stops[-1].station_id,
                            service_id=service.id,
                            travel_date=slots["travel_date"],
                            at=at,
                            filters=slots.get("filters", {}),
                        )
                    )
                    found.extend(response.model_dump(mode="json")["results"])
                found.sort(key=lambda row: (row["departure"], row["service_id"]))
                found = found[: slots.get("result_limit", 5)]
                slots["candidates"] = stable_results(found)
                slots["result_revision"] = int(slots.get("revision", 0)) + 1
                results.append(
                    {
                        "intent": intent,
                        "status": "KNOWN" if found else "NO_RESULTS",
                        "query": {
                            "intent": intent,
                            "origin": slots["origin"],
                            "travel_date": slots["travel_date"],
                        },
                        "results": found,
                        "warnings": [],
                        "executor": "RTCEnquiryEngine station departures",
                        "pagination": {"limit": slots.get("result_limit", 5)},
                    }
                )
                continue
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
                slots["journey_candidates"] = rows[: slots.get("result_limit", 5)]
                slots["candidates"] = rows[: slots.get("result_limit", 5)]
                slots["result_revision"] = int(slots.get("revision", 0)) + 1
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
                primary = encoded
                continue
            projected = planner.project(intent, primary, query, slots.get("service_id"))
            if projected is None:
                result = self.engine.enquire(
                    query.model_copy(update={"intent": "BUSES_BETWEEN"})
                    if intent == "FASTEST_BUS" and slots.get("arrival_ranking")
                    else query
                )
                if intent == "FASTEST_BUS" and slots.get("arrival_ranking"):
                    result.results.sort(key=lambda row: row["arrival"])
                encoded = result.model_dump(mode="json")
                encoded["intent"] = intent
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
                slots["candidates"] = stable_results(candidates)[
                    : slots.get("result_limit", 5)
                ]
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
        if language == "te":
            return render_telugu_results(results)
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
        text, repair_kind, repair_ms = ConversationRepairEngine().prepare(text)
        language = (
            self.normalizer.language(text)
            if request.language == "auto"
            else request.language
        )
        text = normalize_enquiry(text)
        identifier = request.session_id
        initial_identifier = None
        if request.client_message_id and not request.owner_token:
            raise HTTPException(
                422, "An owner capability is required for idempotent messages"
            )
        if not identifier and request.client_message_id:
            initial_identifier = str(
                UUID(
                    bytes=hashlib.sha256(
                        (
                            (request.owner_token or "") + request.client_message_id
                        ).encode()
                    ).digest()[:16],
                    version=4,
                )
            )
            identifier = initial_identifier
        conversation, context, loaded = (
            self.conversations.load(
                identifier, now, request.owner_token, initial_identifier
            )
            if persist
            else (None, None, {})
        )
        slots = deepcopy(loaded)
        text = re.sub(
            r"^(?:actually,?\s+|what about\s+)(?=(?:the )?(?:first|second|third|last)\b)",
            "",
            text,
        )
        if re.fullmatch(r"(?:the )?last (?:one|bus|option)[.!?]*", text):
            text = f"{min(5, len(slots.get('candidates', [])))} one"
        if re.fullmatch(r"next one[.!?]*", text) and slots.get("selected_result_id"):
            index = next(
                (
                    i
                    for i, r in enumerate(slots.get("candidates", []))
                    if r.get("result_id", r.get("journey_id"))
                    == slots["selected_result_id"]
                ),
                -1,
            )
            text = f"{index + 2} one"
        if re.fullmatch(r"previous option[.!?]*", text):
            text = "previous one"
        if re.fullmatch(r"same service[.!?]*", text):
            text = "that bus"
        if re.fullmatch(r"(?:any )?earlier[.!?]*", text) and slots.get(
            "selected_result"
        ):
            selected = slots["selected_result"]
            departure = selected.get("departure_at", selected.get("departure"))
            text = "before " + datetime.fromisoformat(departure).strftime("%I:%M %p")
        if re.fullmatch(r"how long[.!?]*", text):
            text = "journey duration"
        if re.fullmatch(r"(?:any )?cheaper[.!?]*", text):
            text = "cheapest bus"
        request_hash = hashlib.sha256(
            json.dumps(request.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest()
        if request.client_message_id and persist:
            receipt = slots.get("_receipts", {}).get(request.client_message_id)
            if receipt:
                if receipt["hash"] != request_hash:
                    raise HTTPException(
                        409, "Message ID was already used for different content"
                    )
                return NLPResponse.model_validate(receipt["response"])
            if request.client_message_id in slots.get("_processed_ids", []):
                raise HTTPException(
                    409,
                    "This message was processed; restore the current session before continuing",
                )
        if (
            request.expected_state_version is not None
            and request.expected_state_version != int(slots.get("revision", 0))
        ):
            raise HTTPException(
                409,
                "Conversation changed; restore the current context before sending this message again",
            )
        if request.session_mode:
            if (
                request.session_mode == "personal"
                and os.getenv("RTC_KIOSK_ONLY") == "1"
            ):
                raise HTTPException(
                    422, "This installation enforces shared-kiosk expiry"
                )
            slots["session_mode"] = request.session_mode
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
        if request.context_action:
            action = request.context_action
            allowed = set(ContextUpdateEngine.filter_slots) | {
                "origin",
                "destination",
                "travel_date",
                "transfer_station",
            }
            if (
                action.op not in {"RESET_CONTEXT", "SELECT_RESULT"}
                and action.slot not in allowed
            ):
                raise HTTPException(422, "Unsupported public context update")
            if (
                action.op
                in {"SET_SLOT", "REPLACE_SLOT", "CONFIRM_SLOT", "INHERIT_SLOT"}
                and action.value is not None
            ):
                if action.slot in {"origin", "destination", "transfer_station"}:
                    if not isinstance(action.value, str):
                        raise HTTPException(
                            422, "Choose a station name or local station ID"
                        )
                    resolved = self.orchestrator.engine.resolver.resolve(action.value)
                    if resolved.get("status") != "KNOWN":
                        raise HTTPException(422, "Choose one unambiguous station")
                    action = action.model_copy(
                        update={"value": resolved["candidates"][0]["id"]}
                    )
                if action.slot in {"ac", "sleeper", "accessible"} and not isinstance(
                    action.value, bool
                ):
                    raise HTTPException(422, "This preference requires true or false")
            owner_hash = slots.get("_owner_hash")
            slots = ContextUpdateEngine().apply(slots, action)
            try:
                ConversationState.model_validate(slots)
            except ValueError as exc:
                raise HTTPException(422, "Invalid context slot value") from exc
            if owner_hash:
                slots["_owner_hash"] = owner_hash
            operations.append(action.model_dump())
        slots.setdefault("slot_origins", deepcopy(slots.get("slot_sources", {})))
        slots["slot_sources"] = {
            key: "INHERITED" for key in slots.get("slot_sources", {})
        }
        state, answer, clarify = "ANSWERING", "", False
        results: list[dict] = []
        intents: list[str] = []
        entities, timings = {}, {}
        prediction = {"status": "RULES"}
        temporal = {}
        special: dict | None = None
        try:
            text = conversational_reference(text, slots, self.session)
            if text in {"start over", "start again"}:
                text = "reset"
            if text.strip(".!? ") == "neither":
                operation = ContextOperation(
                    op="REFINE_RESULTS", slot="candidates", value=[]
                )
                slots = ContextUpdateEngine().apply(slots, operation)
                operations.append(operation.model_dump())
                special = {
                    "answer": "Neither option is selected. Your route and preferences are retained; would you like a fresh search?",
                    "act": "NEGATION",
                    "results": [],
                    "intents": [],
                }
            else:
                special = ConversationRepairEngine().conflict(
                    text
                ) or text_support.special_dialogue(
                    text, slots, self.orchestrator.engine, now
                )
            if special:
                answer = special["answer"]
                results = special["results"]
                intents = special["intents"]
                state = special.get("state", "ANSWERING")
                clarify = special.get("clarify", False)
            else:
                tick = perf_counter()
                limit_match = re.search(
                    r"(?:show )?(?:the )?next (one|two|three|four|five|[1-5]) buses",
                    text,
                )
                if limit_match:
                    slots["result_limit"] = {
                        "one": 1,
                        "two": 2,
                        "three": 3,
                        "four": 4,
                        "five": 5,
                    }.get(
                        limit_match[1],
                        int(limit_match[1]) if limit_match[1].isdigit() else 3,
                    )
                    slots["station_departures"] = True
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
                        operation = ContextOperation(
                            op="SET_SLOT", slot=slot, value=value
                        )
                        slots = ContextUpdateEngine().apply(slots, operation)
                        slots["journey_mode"] = True
                        operations.append(operation.model_dump())
                if re.search(
                    r"don.t change buses|no transfers|direct only|show direct buses|any direct service",
                    text,
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
                if re.search(
                    r"forget (?:the )?(?:earlier )?time|remove (?:the )?time", text
                ):
                    for slot in ("after", "before", "arrival_after", "arrival_before"):
                        op = ContextOperation(op="CLEAR_SLOT", slot=slot)
                        slots = ContextUpdateEngine().apply(slots, op)
                        operations.append(op.model_dump())
                    for key in (
                        "time_window",
                        "requested_clock",
                        "temporal_resolution",
                    ):
                        slots.pop(key, None)
                    text = "next bus"
                if re.fullmatch(r"is it available[.!?]*", text):
                    if slots.get("selected_result") or slots.get("selected_itinerary"):
                        text = "is it cancelled?"
                    else:
                        raise ValueError(
                            "Which bus or route should I check for availability?"
                        )
                entities = self.extractor.extract(text)
                selected_attribute = bool(
                    (slots.get("selected_itinerary") or slots.get("selected_result"))
                    and re.fullmatch(
                        r"(?:ac|sleeper|is it ac|is it (?:a )?sleeper|does (?:it|that bus|this bus) have ac)[.!?]*",
                        text,
                    )
                )
                if entities.get("filters", {}).get("category"):
                    slots.pop("unresolved_category", None)
                    slots.pop("category_choices", None)
                if selected_attribute:
                    entities["filters"] = {}
                if re.search(r"chang(?:e|ing) at", text) and entities.get(
                    "destination"
                ):
                    entities["transfer_station"] = entities.pop("destination")
                    slots["journey_mode"] = True
                    slots["journey_max_transfers"] = max(
                        1, slots.get("journey_max_transfers", 2)
                    )
                    text = "connecting buses"

                same_service = bool(
                    re.search(r"same (?:one|bus|service) tomorrow", text)
                )
                if same_service:
                    if not slots.get("service_id") and slots.get("selected_itinerary"):
                        legs = slots["selected_itinerary"]["legs"]
                        if len(legs) != 1:
                            raise ValueError(
                                "Which leg of the selected journey should I check for tomorrow?"
                            )
                        slots["service_id"] = legs[0]["service_id"]
                        slots["journey_mode"] = False
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
                        slots.pop("unresolved_category", None)
                        slots.pop("category_choices", None)
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
                    temporal = self.temporal.parse(
                        text, local, slots.get("travel_date")
                    )
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
                            if k
                            in ("after", "before", "arrival_after", "arrival_before")
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
                        inherited_period = slots.get("time_window")
                        previous_bounds = {
                            key: value
                            for key, value in slots["filters"].items()
                            if key
                            in {"after", "before", "arrival_after", "arrival_before"}
                        }
                        if period:
                            slots.pop("time_window", None)
                        for key in (
                            "after",
                            "before",
                            "arrival_after",
                            "arrival_before",
                        ):
                            slots["filters"].pop(key, None)
                        if date_change and not period and not temporal.get("filters"):
                            if inherited_period:
                                slots["time_window"] = inherited_period
                            elif old[2]:
                                delta = date.fromisoformat(
                                    str(slots["travel_date"])
                                ) - date.fromisoformat(str(old[2]))
                                slots["filters"].update(
                                    {
                                        key: (
                                            datetime.fromisoformat(str(value)) + delta
                                        ).isoformat()
                                        for key, value in previous_bounds.items()
                                    }
                                )
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
                            "selected_result",
                            "selected_result_id",
                            "selected_journey_id",
                            "selected_trip_id",
                            "selected_segment",
                            "selected_itinerary",
                            "selected_leg",
                            "selection_status",
                            "service_id",
                            "trip_id",
                            "service_number",
                            "candidates",
                        ):
                            if key not in entities:
                                slots.pop(key, None)
                    if re.search(r"not that bus|not that one", text):
                        for key in (
                            "service_id",
                            "trip_id",
                            "service_number",
                            "selected_result",
                            "selected_result_id",
                            "selected_journey_id",
                            "selected_trip_id",
                            "selected_segment",
                            "selected_itinerary",
                            "selected_leg",
                            "selection_status",
                        ):
                            slots.pop(key, None)
                        raise ValueError(
                            "Which service would you like instead? Choose a result number or service number."
                        )
                    if re.fullmatch(
                        r"(?:the )?(?:cheaper one|cheapest one|fastest one|previous one|this one)[.!?]*",
                        text,
                    ):
                        if re.search(r"cheaper one|cheapest one|fastest one", text):
                            # Compare current database facts within the displayed list.
                            # Never silently substitute a different departure for a reference.
                            fresh_candidates = []
                            for candidate in slots.get("candidates", []):
                                temporary = {
                                    "selected_result": deepcopy(candidate),
                                    "travel_date": slots.get("travel_date"),
                                }
                                if candidate.get("journey_id"):
                                    temporary["selected_itinerary"] = deepcopy(
                                        candidate
                                    )
                                try:
                                    selected_rows(
                                        self.orchestrator.engine, temporary, now
                                    )
                                except StaleResult:
                                    continue
                                updated = temporary["selected_result"]
                                if candidate.get("journey_id"):
                                    updated.update(
                                        fare=updated.get("total_fare"),
                                        departure=updated["departure_at"],
                                        arrival=updated["arrival_at"],
                                    )
                                fresh_candidates.append({**candidate, **updated})
                            if not fresh_candidates:
                                raise StaleResult(
                                    "Those departures are no longer available. Please search for updated options."
                                )
                            comparison = {**slots, "candidates": fresh_candidates}
                            fresh_index = ReferentialResolver().resolve(
                                text, comparison
                            )
                            chosen_id = fresh_candidates[fresh_index]["result_id"]
                            index = next(
                                i
                                for i, candidate in enumerate(slots["candidates"])
                                if candidate["result_id"] == chosen_id
                            )
                            slots["candidates"][index] = fresh_candidates[fresh_index]
                        else:
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
                            selection[1],
                            int(selection[1]) if selection[1].isdigit() else 0,
                        )
                        candidates = slots.get("candidates", [])
                        if not 1 <= n <= min(5, len(candidates)):
                            raise ValueError(
                                "Please search for buses first so I can identify that option."
                                if not candidates
                                else "Which listed service number would you like to select?"
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
                                    origin=chosen.get("origin_id")
                                    or slots.get("origin"),
                                    destination=chosen.get("destination_id")
                                    or slots.get("destination"),
                                    at=max(now, departure - timedelta(seconds=1)),
                                    travel_date=date.fromisoformat(
                                        chosen["service_date"]
                                    ),
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
                            selected_departure_time = (
                                datetime.fromisoformat(chosen["departure_at"])
                                .strftime("%I:%M %p")
                                .lstrip("0")
                            )
                            destination = self.session.get(
                                Station, chosen["destination"]
                            )
                            answer = f"You've selected the {selected_departure_time} journey to {destination.name if destination else 'your destination'}. What would you like to know about it?"
                        else:
                            slots["service_id"] = chosen["service_id"]
                        slots.pop("trip_id", None)
                        if chosen.get("trip_id"):
                            slots["trip_id"] = chosen["trip_id"]
                        if not chosen.get("journey_id"):
                            answer = (
                                "You've selected service "
                                + chosen.get("service_number", str(n))
                                + "."
                            )
                    timings["context_update_ms"] = (
                        perf_counter() - context_tick
                    ) * 1000
                    tick = perf_counter()
                    intents = text_support.classify_extra(
                        text, self.classifier.classify(text), self.session
                    )
                    if limit_match:
                        intents = ["NEXT_BUS"]
                    if selected_attribute:
                        intents = ["BUS_AMENITIES"]
                    if re.search(r"arrives (?:first|earliest)", text):
                        slots["arrival_ranking"] = True
                    elif "FASTEST_BUS" in intents:
                        slots["arrival_ranking"] = False
                    if re.search(
                        r"don.t change buses|no transfers|direct only|show direct buses|any direct service",
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
                    if prediction["status"] in (
                        "OUT_OF_SCOPE",
                        "CLARIFICATION_REQUIRED",
                    ):
                        raise ValueError(
                            "I can help with RTC bus enquiries; that request appears outside this scope."
                            if prediction["status"] == "OUT_OF_SCOPE"
                            else "Please clarify which bus information you need."
                        )
                    clock_match = re.search(
                        r"\b(?:at|around)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text
                    )
                    if "BUS_AT_TIME" in intents and slots.get("requested_clock"):
                        previous_clock = datetime.fromisoformat(
                            slots["requested_clock"]
                        )
                        clock_day = date.fromisoformat(slots["travel_date"])
                        slots["requested_clock"] = previous_clock.replace(
                            year=clock_day.year,
                            month=clock_day.month,
                            day=clock_day.day,
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
                        active = slots.get("last_intent", "NEXT_BUS")
                        if active in {
                            "BUS_PLATFORM",
                            "SEAT_AVAILABILITY",
                            "BUS_DELAY",
                            "BUS_LIVE_STATUS",
                            "BUS_CANCELLATION",
                            "ROUTE_STOPS",
                            "BUS_AMENITIES",
                            "ARRIVAL_TIME",
                            "JOURNEY_DURATION",
                            "BUS_VIA_LOCATION",
                        } and not (
                            slots.get("selected_result")
                            or slots.get("selected_itinerary")
                        ):
                            active = (
                                "CONNECTING_BUSES"
                                if slots.get("journey_mode")
                                else "NEXT_BUS"
                            )
                        intents = ["NEXT_BUS" if clear else active]
                    if not intents and text in ("that bus", "this bus"):
                        if not (
                            slots.get("service_id")
                            or slots.get("selected_itinerary")
                            or slots.get("selected_result")
                        ):
                            raise ValueError("Which service do you mean?")
                        answer = (
                            "Ask about the selected service's fare, stops or status."
                        )
                    timings["intent_inference_ms"] = (perf_counter() - tick) * 1000
                    if text == "keep this conversation context":
                        answer = "Privacy setting updated. Your current enquiry is unchanged."
                        intents = []
                    elif text in ("hello", "hi", "నమస్తే", "thanks", "thank you", "help"):
                        answer = self.content.render("HELP", language)
                        intents = []
                    elif not intents and not answer:
                        state, clarify = "IDLE", True
                        answer = self.content.render("IDLE", language)
                    elif intents:
                        absent = (
                            "AWAITING_CATEGORY"
                            if slots.get("unresolved_category")
                            else text_support.missing(intents, slots)
                        )
                        if absent == "AWAITING_TIME":
                            raise ValueError(
                                "What departure time should I search around? For example, at 8 PM."
                            )
                        if absent:
                            slots["last_intent"] = intents[0]
                            state, clarify = absent, True
                            answer = self.content.render(state, language)
                            if absent == "AWAITING_CATEGORY":
                                answer = (
                                    "Your requested category '"
                                    + slots["unresolved_category"]
                                    + "' is not recorded. Choose a listed category or say 'Any bus type'."
                                )
                            if intents[0] in {"TICKET_FARE", "GET_FARE"} and absent in {
                                "AWAITING_DESTINATION",
                                "AWAITING_SERVICE",
                            }:
                                answer = "Which destination or bus would you like the fare for?"
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
                            if slots.get("service_number") and not slots.get(
                                "service_id"
                            ):
                                matches = list(
                                    self.session.scalars(
                                        select(Service).where(
                                            Service.number.ilike(
                                                slots["service_number"]
                                            ),
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
                                        datetime.fromisoformat(
                                            slots["filters"]["after"]
                                        ),
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
                                for field in (
                                    "selected_result",
                                    "selected_result_id",
                                    "selected_journey_id",
                                    "selected_trip_id",
                                    "selected_segment",
                                    "selected_itinerary",
                                    "selected_leg",
                                    "selection_status",
                                ):
                                    slots.pop(field, None)
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
                            results = self.orchestrator.execute(
                                intents, slots, query_at
                            )
                            timings["database_lookup_ms"] = (
                                perf_counter() - tick
                            ) * 1000
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
                                    if language == "en" and set(intents) & searches:
                                        description = text_support.conversation_summary(
                                            slots, self.session
                                        ).split(". No service")[0]
                                        answer = (
                                            "I couldn't find matching scheduled services in the current database. "
                                            + description.rstrip(".")
                                            + ". You can change the date or remove an optional restriction."
                                        )
                            slots["last_intent"] = intents[0]
        except UnknownCategory as exc:
            slots = deepcopy(previous)
            for key in (
                "selected_result",
                "selected_result_id",
                "selected_trip_id",
                "selected_journey_id",
                "selected_segment",
                "selected_itinerary",
                "selected_leg",
                "service_id",
                "trip_id",
                "selection_status",
                "candidates",
                "journey_candidates",
            ):
                slots.pop(key, None)
            slots.setdefault("filters", {}).pop("category", None)
            slots["filters"].update(exc.filters)
            slots["unresolved_category"] = exc.requested
            slots["category_choices"] = exc.choices
            operations = []
            state, clarify, answer = "AWAITING_CATEGORY", True, str(exc)
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
                "selected_result",
                "selected_result_id",
                "selected_journey_id",
                "selected_trip_id",
                "selected_segment",
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
        for key in ("origin", "destination"):
            station = self.session.get(Station, slots[key]) if slots.get(key) else None
            if station:
                slots[key + "_name"] = station.name
            else:
                slots.pop(key + "_name", None)
        chosen = slots.get("selected_itinerary") or slots.get("selected_result")
        if chosen:
            service_ids = [leg["service_id"] for leg in chosen.get("legs", [])] or [
                chosen["service_id"]
            ]
            services = [
                self.session.get(Service, identifier) for identifier in service_ids
            ]
            slots["selection_summary"] = {
                "service_numbers": [s.number for s in services if s],
                "categories": [
                    self.session.get(Category, s.category_id).name
                    for s in services
                    if s
                ],
                "leg_count": len(service_ids),
                "departure": chosen.get("departure_at", chosen.get("departure")),
            }
        else:
            slots.pop("selection_summary", None)
        if request.station_context:
            current = self.orchestrator.engine.resolver.resolve(request.station_context)
            if current.get("status") == "KNOWN":
                slots["current_station_id"] = current["candidates"][0]["id"]
        for row in slots.get("candidates", []):
            row["result_list_version"] = slots.get("result_revision", 0)
        reliability = assess(state, clarify, intents, results, prediction, answer)
        stale_evidence = stale_platform_evidence(self.orchestrator.engine, results, now)
        if stale_evidence:
            reliability.error_category = ErrorCategory.STALE_OPERATIONAL_DATA
            reliability.failure_group = "DATA_ERROR"
            reliability.diagnosis = stale_evidence
            answer += " " + stale_evidence[0]["message"]
        reliability.repair = repair_kind
        reliability.repair_detection_ms = repair_ms
        if state == "NO_RESULTS" and set(intents) & (
            ExecutionPlanner.journey_intents
            | {
                "AC_BUS_AVAILABILITY",
                "NON_AC_AVAILABILITY",
                "SLEEPER_BUS_AVAILABILITY",
                "SEATER_BUS_AVAILABILITY",
                "CONNECTING_BUSES",
                "ALTERNATIVE_ROUTES",
            }
        ):
            reliability.diagnosis, reliability.diagnostic_ms = diagnose(
                self.orchestrator.engine, slots, now
            )
            if reliability.diagnosis:
                answer = (
                    " ".join(d["message"] for d in reliability.diagnosis)
                    + " Your restrictions are unchanged."
                )
        if state == "IDLE" and clarify and not intents:
            answer = "Are you asking about bus timings, a fare, a platform or a route?"
        if repair_kind and not clarify:
            answer = "Okay, I've applied your correction. " + answer
        if language == "te":
            answer = localize_dialogue(answer, state, clarify, results)
        slots["last_question"] = request.text
        slots["last_answer"] = answer
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
        ordered = ExecutionPlanner().plan(intents)
        sections = (
            [
                AnswerSection(
                    intent=r["intent"],
                    title=r["intent"].replace("_", " ").title(),
                    text=r.get("answer_text") or text_support.render_result(r),
                    status=r["status"],
                )
                for r in results
            ]
            if language == "en"
            else []
        )
        response = NLPResponse(
            reliability=reliability,
            source_metadata=[
                {
                    "intent": r["intent"],
                    "source": row.get("dataset_source", row.get("sources")),
                    "freshness": row.get("status")
                    or row.get("arrival_kind")
                    or row.get("departure_kind")
                    or ("scheduled" if row.get("departure") else "unknown"),
                    "recorded_at": row.get("recorded_at"),
                    "expires_at": row.get("expires_at"),
                }
                for r in results
                for row in r["results"]
            ],
            dialogue_act=special.get("act", "ENQUIRY")
            if special
            else "RESET_CONVERSATION"
            if text == "reset"
            else "CORRECTION"
            if re.search(
                r"^(?:no|actually|i meant)|forget|remove.*limit",
                request.text.casefold(),
            )
            else "ENQUIRY",
            query_plan=ConversationPlan(
                primary_intent=ordered[0] if ordered else None,
                secondary_intents=ordered[1:],
                shared_entities={
                    k: slots[k]
                    for k in (
                        "origin",
                        "destination",
                        "travel_date",
                        "filters",
                        "passengers",
                    )
                    if k in slots
                },
                dependencies=[
                    {
                        "intent": r["intent"],
                        "executor": r.get("executor", "RTCEnquiryEngine.enquire"),
                        "query": r.get("query", {}),
                    }
                    for r in results
                ],
            ),
            answer_sections=sections,
            clarification_choices=(
                [
                    {"id": c["id"], "label": c["name"], "text": "Only " + c["name"]}
                    for c in slots.get("category_choices", [])
                ]
            )
            if clarify and slots.get("category_choices")
            else [
                {
                    "id": r.get("result_id"),
                    "label": "Option " + str(i + 1),
                    "text": str(i + 1),
                }
                for i, r in enumerate(slots.get("candidates", []))
            ]
            if clarify
            else [],
            message_id=request.client_message_id or str(uuid4()),
            follow_up_suggestions=text_support.suggestions(slots, results),
            data_source=text_support.sources(results, slots),
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
            ]
            + (
                [
                    "The previous session expired or was unavailable. A new private conversation has started; please supply the journey details again."
                ]
                if request.session_id
                and conversation
                and request.session_id != conversation.id
                else []
            ),
            duration_ms=elapsed,
            debug=debug,
            context_changes=operations,
        )
        if special and special.get("choices"):
            response.clarification_choices = special["choices"]
        if repair_kind == "SELECTION_REPAIR" and clarify:
            response.follow_up_suggestions = [
                FollowUpSuggestion(
                    id="fresh_options", label="Show other departures", text="Next bus"
                )
            ]
        if reliability.diagnosis:
            for d in reliability.diagnosis:
                if d["code"] == "FARE_LIMIT":
                    response.follow_up_suggestions.append(
                        FollowUpSuggestion(
                            id="remove_fare",
                            label="Remove fare limit",
                            text="Remove the fare limit",
                        )
                    )
                if d["code"] == "TIME_WINDOW":
                    response.follow_up_suggestions.append(
                        FollowUpSuggestion(
                            id="remove_time",
                            label="Forget earlier time",
                            text="Forget the earlier time",
                        )
                    )
        if persist:
            reset = (
                text in {"reset", "/reset", "new enquiry"}
                or request.context_action
                and request.context_action.op == "RESET_CONTEXT"
            )
            if reset:
                self.session.execute(
                    delete(Message).where(Message.session_id == conversation.id)
                )
            else:
                for index, (role, body) in enumerate(
                    (("user", request.text), ("assistant", answer))
                ):
                    self.session.add(
                        Message(
                            session_id=conversation.id,
                            role=role,
                            text=body,
                            sequence_number=slots["revision"] * 2 + index,
                        )
                    )
            if request.client_message_id:
                receipts = dict(slots.get("_receipts", {}))
                receipts[request.client_message_id] = {
                    "hash": request_hash,
                    "response": response.model_dump(mode="json"),
                }
                slots["_receipts"] = dict(list(receipts.items())[-3:])
                slots["_processed_ids"] = (
                    slots.get("_processed_ids", []) + [request.client_message_id]
                )[-100:]
                context.values = dict(slots)
            ids = {
                r.get("service_id")
                for r in slots.get("candidates", [])
                if r.get("service_id")
            }
            if slots.get("service_id"):
                ids.add(slots["service_id"])
            operators = {
                s.operator_id for sid in ids if (s := self.session.get(Service, sid))
            }
            if not operators and slots.get("filters", {}).get("operator"):
                from ..domain import Operator

                value = slots["filters"]["operator"]
                op = self.session.scalar(
                    select(Operator).where(
                        (Operator.id == value) | (Operator.code == value)
                    )
                )
                if op:
                    operators.add(op.id)
            operator_id = next(iter(operators)) if len(operators) == 1 else None
            if not reset:
                messages = dict(slots.get("_feedback_messages", {}))
                descriptor = self.english_model.descriptor()
                messages[response.message_id] = {
                    "sequence": slots["revision"] * 2 + 1,
                    "operator_id": operator_id,
                    "predicted_intents": intents,
                    "extracted_entities": entities,
                    "context": {
                        k: slots[k]
                        for k in (
                            "origin",
                            "destination",
                            "travel_date",
                            "filters",
                            "passengers",
                            "selected_result_id",
                        )
                        if k in slots
                    },
                    "source": response.data_source,
                    "model_version": prediction.get("version")
                    or "DETERMINISTIC_RULES:"
                    + hashlib.sha256(
                        json.dumps(self.classifier.rules, sort_keys=True).encode()
                    ).hexdigest()[:12],
                    "dataset_version": descriptor.get("dataset_version")
                    if descriptor
                    else None,
                    "reliability": reliability.model_dump(mode="json"),
                    "structured_results": [
                        {
                            k: v
                            for k, v in row.items()
                            if k
                            in {
                                "service_id",
                                "trip_id",
                                "fare",
                                "amount",
                                "bay",
                                "status",
                                "departure",
                                "arrival",
                                "dataset_source",
                            }
                        }
                        for result in results
                        for row in result["results"]
                    ][:15],
                }
                slots["_feedback_messages"] = dict(list(messages.items())[-40:])
            from .metrics import capture

            capture(self.session, operator_id, response, repair_kind)
            slots["_last_message_id"] = response.message_id
            context.values = dict(slots)
            self.session.flush()
        return response
