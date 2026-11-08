from datetime import date
from decimal import Decimal

"""Typed compatibility state and explicit context dependency operations."""

from copy import deepcopy
from typing import ClassVar, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class JourneyPreferences(BaseModel):
    model_config = ConfigDict(extra="allow")
    ac: bool | None = None
    sleeper: bool | None = None
    category: str | None = None
    operator: str | None = None
    max_fare: Decimal | None = Field(default=None, ge=0)
    after: AwareDatetime | None = None
    before: AwareDatetime | None = None
    arrival_before: AwareDatetime | None = None
    arrival_after: AwareDatetime | None = None
    exclude_categories: list[str] = Field(default_factory=list)


class ConversationState(BaseModel):
    model_config = ConfigDict(extra="allow")
    session_id: str | None = None
    current_station: str | None = None
    origin: str | None = None
    destination: str | None = None
    travel_date: date | None = None
    filters: JourneyPreferences = Field(default_factory=JourneyPreferences)
    candidates: list[dict] = Field(default_factory=list)
    journey_candidates: list[dict] = Field(default_factory=list)
    selected_itinerary: dict | None = None
    selected_result: dict | None = None
    selected_result_id: str | None = None
    selected_journey_id: str | None = None
    selected_trip_id: str | None = None
    selected_segment: dict | None = None
    selected_leg: int | None = None
    journey_constraints: dict = Field(default_factory=dict)
    journey_ranking: str | None = None
    journey_mode: bool = False
    service_id: str | None = None
    trip_id: str | None = None
    selected_route_id: str | None = None
    selection_status: Literal["SYSTEM_QUERY_DEFAULT", "USER_CONFIRMED"] | None = None
    slot_origins: dict[str, str] = Field(default_factory=dict)
    last_intent: str | None = None
    last_intents: list[str] = Field(default_factory=list)
    pending_clarification: str | None = None
    last_system_question: str | None = None
    revision: int = Field(default=0, ge=0)
    last_activity_at: str | None = None
    slot_sources: dict[str, str] = Field(default_factory=dict)
    confirmed_slots: list[str] = Field(default_factory=list)
    result_revision: int | None = None


class ContextOperation(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def compatible_operations(cls, value):
        if isinstance(value, dict):
            value = dict(value)
            value["op"] = {
                "SET": "SET_SLOT",
                "REPLACE": "REPLACE_SLOT",
                "CLEAR": "CLEAR_SLOT",
                "INHERIT": "INHERIT_SLOT",
                "CONFIRM": "CONFIRM_SLOT",
                "REJECT": "REJECT_SLOT",
                "RESET": "RESET_CONTEXT",
            }.get(value.get("op"), value.get("op"))
            if value["op"] == "INHERIT_SLOT":
                value.setdefault("source", "INHERITED")
        return value

    op: Literal[
        "SET_SLOT",
        "REPLACE_SLOT",
        "CLEAR_SLOT",
        "CONFIRM_SLOT",
        "REJECT_SLOT",
        "RESET_CONTEXT",
        "SELECT_RESULT",
        "INHERIT_SLOT",
        "REFINE_RESULTS",
        "SWITCH_INTENT",
    ]
    slot: str | None = None
    value: object = None
    source: Literal["EXPLICIT", "INHERITED", "SYSTEM_DEFAULT", "CANDIDATE"] = "EXPLICIT"


class ContextUpdateEngine:
    dependencies: ClassVar[dict[str, set[str]]] = {
        "origin": {
            "service_id",
            "trip_id",
            "selected_route_id",
            "fare",
            "platform",
            "candidates",
        },
        "destination": {
            "service_id",
            "trip_id",
            "selected_route_id",
            "fare",
            "platform",
            "candidates",
        },
        "transfer_station": {"service_id", "trip_id", "candidates"},
        "passengers": {"service_id", "trip_id", "candidates", "fare", "platform"},
        "travel_date": {"service_id", "trip_id", "fare", "platform", "candidates"},
        "category": {"service_id", "trip_id", "fare", "platform", "candidates"},
        "ac": {"service_id", "trip_id", "fare", "platform", "candidates"},
        "sleeper": {"service_id", "trip_id", "fare", "platform", "candidates"},
    }
    filter_slots: ClassVar[set[str]] = {
        "ac",
        "sleeper",
        "category",
        "operator",
        "max_fare",
        "min_fare",
        "after",
        "before",
        "arrival_after",
        "arrival_before",
        "exclude_categories",
        "accessible",
    }

    def apply(self, state, operation: ContextOperation):
        values = deepcopy(state)
        if operation.op == "RESET_CONTEXT":
            return {}
        if operation.op == "SELECT_RESULT":
            index = operation.value
            if (
                not isinstance(index, int)
                or isinstance(index, bool)
                or not 0 <= index < len(values.get("candidates", []))
            ):
                raise ValueError("Select a currently listed service number.")
            chosen = values["candidates"][index]
            previous_id = values.get("selected_result_id")
            chosen_id = chosen.get("result_id") or chosen.get("journey_id")
            if previous_id and previous_id != chosen_id:
                values["selected_result_history"] = (
                    values.get("selected_result_history", []) + [previous_id]
                )[-10:]
            for slot, key in (
                ("origin", "origin_id"),
                ("destination", "destination_id"),
            ):
                resolved = chosen.get(key, chosen.get(slot))
                if resolved:
                    values[slot] = resolved
                    values.setdefault("slot_sources", {})[slot] = "CONFIRMED_SELECTION"
            if not values.get("travel_date") and chosen.get("service_date"):
                values["travel_date"] = str(chosen["service_date"])
            values["selection_status"] = "USER_CONFIRMED"
            values["selected_result"] = deepcopy(chosen)
            values["selected_result_id"] = chosen.get(
                "result_id", chosen.get("journey_id")
            )
            values["selected_journey_id"] = chosen.get("journey_id")
            values["selected_trip_id"] = chosen.get("trip_id")
            legs = chosen.get("legs", [])
            values["selected_segment"] = {
                "origin_id": chosen.get(
                    "origin_id", chosen.get("origin", values.get("origin"))
                ),
                "destination_id": chosen.get(
                    "destination_id",
                    chosen.get("destination", values.get("destination")),
                ),
                "boarding_stop_id": chosen.get(
                    "boarding_stop_id",
                    legs[0].get("boarding_stop_id") if legs else None,
                ),
                "alighting_stop_id": chosen.get(
                    "alighting_stop_id",
                    legs[-1].get("alighting_stop_id") if legs else None,
                ),
                "service_date": chosen.get("service_date", values.get("travel_date")),
            }
            if chosen.get("journey_id"):
                values["selected_itinerary"] = chosen
                values["selected_leg"] = None
                values.pop("service_id", None)
                values.pop("trip_id", None)
                return values
            values.pop("selected_itinerary", None)
            values.pop("selected_leg", None)
            previous = values.get("service_id")
            if previous and previous != chosen["service_id"]:
                values["selected_service_history"] = (
                    values.get("selected_service_history", []) + [previous]
                )[-10:]
            values["selection_status"] = "USER_CONFIRMED"
            values["service_id"] = chosen["service_id"]
            values["trip_id"] = chosen.get("trip_id")
            values["confirmed_slots"] = list(
                set(values.get("confirmed_slots", [])) | {"service_id"}
            )
            return values
        if operation.op == "REFINE_RESULTS":
            rows = operation.value
            if not isinstance(rows, list):
                raise ValueError("Result refinement requires a current result list")
            values["candidates"] = rows
            values["result_revision"] = values.get("revision", 0) + 1
            retained = {r.get("result_id") or r.get("journey_id") for r in rows}
            if values.get("selected_result_id") not in retained:
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
                ):
                    values.pop(key, None)
            return values
        if operation.op == "SWITCH_INTENT":
            values["last_intent"] = operation.value
            return values
        if not operation.slot:
            raise ValueError("Context operation requires a slot")
        if operation.source == "CANDIDATE" and operation.op not in (
            "CONFIRM_SLOT",
            "REJECT_SLOT",
        ):
            values.setdefault("inferred_candidates", {})[operation.slot] = (
                operation.value
            )
            return values
        target = (
            values.setdefault("filters", {})
            if operation.slot in self.filter_slots
            else values
        )
        previous = target.get(operation.slot)
        if operation.op in ("CLEAR_SLOT", "REJECT_SLOT"):
            target.pop(operation.slot, None)
        elif operation.op == "CONFIRM_SLOT":
            candidates = values.get("inferred_candidates", {})
            target[operation.slot] = candidates.pop(
                operation.slot,
                operation.value
                if operation.value is not None
                else target.get(operation.slot),
            )
            values["confirmed_slots"] = list(
                set(values.get("confirmed_slots", [])) | {operation.slot}
            )
        else:
            target[operation.slot] = (
                target.get(operation.slot)
                if operation.op == "INHERIT_SLOT" and operation.value is None
                else operation.value
            )
        values.setdefault("slot_sources", {})[operation.slot] = operation.source
        if operation.source != "INHERITED" or operation.slot not in values.get(
            "slot_origins", {}
        ):
            values.setdefault("slot_origins", {})[operation.slot] = operation.source
        if previous != target.get(operation.slot):
            if (
                operation.slot in self.dependencies
                or operation.slot in self.filter_slots
            ):
                for field in (
                    "selected_result",
                    "selected_result_id",
                    "selected_journey_id",
                    "selected_trip_id",
                    "selected_segment",
                    "selection_status",
                    "journey_candidates",
                    "selected_itinerary",
                    "selected_leg",
                    "journey_constraints",
                ):
                    values.pop(field, None)
                if values.get("journey_mode"):
                    values.pop("candidates", None)
            for field in self.dependencies.get(operation.slot, set()):
                values.pop(field, None)
                values["confirmed_slots"] = [
                    s for s in values.get("confirmed_slots", []) if s != field
                ]
        return values
