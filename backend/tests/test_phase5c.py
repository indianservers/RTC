"""300 real FastAPI/SQLite conversations with explicit structural/fact assertions."""

from datetime import timedelta
from decimal import Decimal

import pytest
from app.catalog import Context
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_conversation_memory import NOW, turn
from test_conversation_memory import chat as _chat
from test_conversation_memory import text_db as _text_db

chat = _chat
text_db = _text_db


@pytest.mark.parametrize("variant", range(20))
@pytest.mark.parametrize(
    "family",
    [
        "fare",
        "platform",
        "attributes",
        "compare",
        "reference",
        "correction",
        "deadline",
        "summary",
        "scope",
        "reset",
        "composite",
        "unknown",
        "negation",
        "sessions",
        "expiry",
    ],
)
def test_300_multiturn_reasoning(chat, text_db, family, variant):
    day = (NOW + timedelta(days=variant)).date().isoformat()
    destination = "Nellore" if variant % 2 == 0 else "Tirupati"
    dest_id = "DEMO4" if destination == "Nellore" else "DEMO2"
    response = turn(chat, f"Next bus to {destination} on {day}?")
    assert response["intents"] == ["NEXT_BUS"]
    assert response["context"]["destination"] == dest_id
    assert response["query_plan"]["primary_intent"] == "NEXT_BUS"
    assert len(response["result_set"]) == 3
    sid = response["session_id"]
    first, second, third = response["result_set"]

    def ask(text, **extra):
        nonlocal response
        version = response["context"]["state_version"]
        response = turn(chat, text, response, **extra)
        assert response["session_id"] == sid
        assert response["context"]["state_version"] == version + 1
        return response

    if family == "fare":
        ask("Second one")
        ask("How much?")
        assert response["intents"] == ["TICKET_FARE"]
        query = response["results"][0]["query"]
        assert query["segments"][0]["service_id"] == second["service_id"]
        assert query["segments"][0]["destination"] == dest_id
        assert Decimal(response["results"][0]["results"][0]["amount"]) == Decimal(
            second["fare"]
        )
    elif family == "platform":
        ask("2")
        ask("Which platform?")
        assert response["results"][0]["query"]["service_id"] == second["service_id"]
        assert response["results"][0]["results"][0] == {
            "status": "unknown",
            "bay": None,
        }
        assert response["selected_journey"]["service_id"] == second["service_id"]
    elif family == "attributes":
        ask("Only AC")
        assert response["context"]["filters"]["ac"] is True
        ask("Only sleeper")
        assert response["context"]["filters"]["sleeper"] is True
        ask("1")
        ask("Does it have AC?")
        assert response["results"][0]["results"][0]["ac"] is True
        assert response["results"][0]["results"][0]["sleeper"] is True
    elif family == "compare":
        ask("Second one")
        ask("Compare with the first one")
        comparison = response["results"][0]
        assert response["dialogue_act"] == "COMPARISON"
        assert comparison["query"]["result_ids"] == [
            second["result_id"],
            first["result_id"],
        ]
        assert [Decimal(r["fare"]) for r in comparison["results"]] == [
            Decimal(second["fare"]),
            Decimal(first["fare"]),
        ]
        assert response["selected_journey"]["service_id"] == second["service_id"]
        ask("Which one is cheaper?")
        assert response["results"][0]["winners"] == [1]
        assert response["results"][0]["results"][2]["fare"] is None
    elif family == "reference":
        ask("1")
        ask("The next one")
        assert response["selected_journey"]["service_id"] == second["service_id"]
        ask("The one before it")
        assert response["selected_journey"]["service_id"] == first["service_id"]
        ask("The Express")
        assert response["selected_journey"]["service_id"] == first["service_id"]
        ask("The other one")
        assert response["requires_clarification"]
        assert response["selected_journey"]["service_id"] == first["service_id"]
    elif family == "correction":
        ask("2")
        ask("No, Tirumala")
        assert (
            response["context"]["destination"] == "DEMO3"
            and response["selected_journey"] is None
        )
        ask("Only AC")
        ask("Under 900")
        assert (
            response["context"]["filters"]["ac"] is True
            and Decimal(response["context"]["filters"]["max_fare"]) == 900
        )
        ask("Remove the fare limit")
        assert response["context"]["filters"].get("max_fare") is None
        assert response["context"]["filters"]["ac"] is True
    elif family == "deadline":
        ask(f"I need to reach {destination} before 7 AM tomorrow")
        assert response["context"]["filters"].get("arrival_before")
        assert not response["context"]["filters"].get("before")
        deadline = response["context"]["filters"]["arrival_before"]
        ask("Only AC")
        ask("Under 900")
        assert response["context"]["filters"]["arrival_before"] == deadline
        ask("Forget the earlier time")
        assert not response["context"]["filters"].get("arrival_before")
        assert response["context"]["filters"]["ac"] is True
    elif family == "summary":
        ask("Only AC")
        ask("Under 900")
        before = response["context"].copy()
        ask("Summarize my journey")
        assert response["dialogue_act"] == "SUMMARY" and not response["results"]
        assert response["context"]["filters"] == before["filters"]
        assert response["context"]["destination"] == dest_id
        assert destination in response["answer"] and "900" in response["answer"]
        assert response["selected_journey"] is None
    elif family == "scope":
        ask("2")
        chosen = response["context"]["selected_result_id"]
        ask(
            [
                "What's the weather?",
                "Who is the Prime Minister?",
                "Can you order food?",
                "Tell me a joke.",
            ][variant % 4]
        )
        assert (
            response["dialogue_act"] == "OUT_OF_SCOPE"
            and response["state"] == "OUT_OF_SCOPE"
        )
        assert (
            not response["results"]
            and response["context"]["selected_result_id"] == chosen
        )
        ask("Fare?")
        assert Decimal(response["results"][0]["results"][0]["amount"]) == Decimal(
            second["fare"]
        )
    elif family == "reset":
        ask("2")
        ask("Start over")
        assert response["dialogue_act"] == "RESET_CONVERSATION"
        assert (
            not response["context"].get("destination")
            and not response["selected_journey"]
            and not response["result_set"]
        )
        ask("How much?")
        assert response["requires_clarification"] and not response["results"]
    elif family == "composite":
        ask(f"Next bus to {destination}, fare and platform on {day}?")
        assert response["query_plan"]["primary_intent"] == "NEXT_BUS"
        assert set(response["query_plan"]["secondary_intents"]) == {
            "TICKET_FARE",
            "BUS_PLATFORM",
        }
        assert len(response["answer_sections"]) == 3
        timings = next(r for r in response["results"] if r["intent"] == "NEXT_BUS")[
            "results"
        ]
        fare = next(r for r in response["results"] if r["intent"] == "TICKET_FARE")
        platform = next(r for r in response["results"] if r["intent"] == "BUS_PLATFORM")
        assert [r["service_id"] for r in fare["results"]] == [
            r["service_id"] for r in timings
        ]
        assert [r["service_id"] for r in platform["results"]] == [
            r["service_id"] for r in timings
        ]
        assert [r["fare"] for r in fare["results"]] == [r["fare"] for r in timings]
    elif family == "unknown":
        ask("3")
        ask("Fare?")
        assert response["results"][0]["results"][0]["amount"] is None
        ask("Which platform?")
        assert response["results"][0]["results"][0]["bay"] is None
        ask("Is it available?")
        assert response["selected_journey"]["service_id"] == third["service_id"]
        assert response["results"][0]["query"]["service_id"] == third["service_id"]
    elif family == "negation":
        ask("Only AC")
        ask("Only AC and non AC")
        assert (
            response["requires_clarification"]
            and response["context"]["filters"]["ac"] is True
        )
        ask("Not AC, Express")
        assert response["context"]["filters"]["ac"] is False
        assert response["context"]["filters"]["category"] == "express"
        ask("Two passengers, not three")
        assert response["context"]["passengers"] == 2
    elif family == "sessions":
        ask("2")
        other = turn(chat, "Next bus to Hyderabad tomorrow?")
        assert other["session_id"] != sid and other["context"]["destination"] == "DEMO6"
        ask("Fare?")
        assert (
            response["context"]["destination"] == dest_id
            and response["selected_journey"]["service_id"] == second["service_id"]
        )
        assert Decimal(response["results"][0]["results"][0]["amount"]) == Decimal(
            second["fare"]
        )
    else:
        ask("2")
        with Session(text_db) as session, session.begin():
            context = session.scalar(select(Context).where(Context.session_id == sid))
            context.values = {
                **context.values,
                "expires_at": (NOW - timedelta(seconds=1)).isoformat(),
            }
        expired = chat.post("/api/v1/conversation/state", json={"session_id": sid})
        assert expired.status_code == 410
        fresh = chat.post(
            "/api/v1/conversation/message",
            json={"text": "How much?", "language": "en", "session_id": sid},
        ).json()
        assert fresh["session_id"] != sid and not fresh["context"].get("destination")
        assert fresh["requires_clarification"]


def test_named_time_and_premium_difference(chat):
    first = turn(chat, "Next bus to Nellore tomorrow?")
    chosen = turn(chat, "The 9 AM one", first)
    assert chosen["selected_journey"]["service_id"] == "nellore-luxury"
    first_chosen = turn(chat, "1", chosen)
    premium = turn(chat, "How much more is Super Luxury?", first_chosen)
    assert premium["results"][0]["query"]["result_ids"] == [
        first["result_set"][0]["result_id"],
        first["result_set"][1]["result_id"],
    ]
    assert [Decimal(r["fare"]) for r in premium["results"][0]["results"]] == [
        Decimal(101),
        Decimal(205),
    ]
    assert "104" in premium["answer"]


def test_bound_delay_and_seats_do_not_lose_selected_scope(chat):
    first = turn(chat, "Next bus to Hyderabad tomorrow?")
    selected = turn(chat, "2", first)
    result = turn(chat, "Is the Hyderabad bus late, and are seats available?", selected)
    assert set(result["intents"]) == {"BUS_DELAY", "SEAT_AVAILABILITY"}
    for tool in result["results"]:
        assert tool["query"]["service_id"] == selected["selected_journey"]["service_id"]
    assert result["context"]["destination"] == "DEMO6"


def test_comparison_eligibility_and_arrival_deadline(chat):
    first = turn(chat, "Next bus to Nellore tomorrow?")
    earlier = turn(chat, "Which arrives earlier?", first)
    assert earlier["results"][0]["winners"] == [1]
    deadline = turn(chat, "Which is better for reaching before 8 AM?", earlier)
    assert deadline["results"][0]["winners"] == []
    assert deadline["context"]["filters"] == first["context"]["filters"]
    ambiguity = turn(chat, "Compare the two", deadline)
    assert ambiguity["requires_clarification"]
    neither = turn(chat, "Neither", ambiguity)
    assert (
        neither["dialogue_act"] == "NEGATION"
        and not neither["result_set"]
        and not neither["selected_journey"]
    )
    assert neither["context"]["destination"] == "DEMO4"


def test_transfer_plan_retains_deadline_and_budget(chat):
    first = turn(chat, "I need to reach Tirumala before 10 PM tomorrow")
    filtered = turn(chat, "Only AC", first)
    budget = turn(chat, "Under 900", filtered)
    changed = turn(chat, "What if I change at Tirupati?", budget)
    assert changed["context"]["destination"] == "DEMO3"
    assert changed["context"]["transfer_station"] == "DEMO2"
    assert (
        changed["context"]["filters"]["arrival_before"]
        == budget["context"]["filters"]["arrival_before"]
    )
    assert changed["context"]["filters"]["ac"] is True
    assert Decimal(changed["context"]["filters"]["max_fare"]) == 900
    assert changed["context"]["journey_constraints"]["transfer_station"] == "DEMO2"


def test_earliest_arrival_and_intermediate_stop_share_primary_segments(chat):
    first = turn(chat, "Next bus to Nellore tomorrow?")
    result = turn(
        chat, "Which bus arrives earliest, and does it stop at Ongole?", first
    )
    assert set(result["intents"]) == {"FASTEST_BUS", "BUS_VIA_LOCATION"}
    assert result["context"]["destination"] == "DEMO4"
    assert result["context"]["via"] == "DEMO5"
    primary = result["results"][0]
    secondary = result["results"][1]
    assert primary["results"] and secondary["query"]["service_ids"] == [
        r["service_id"] for r in primary["results"]
    ]
    assert all(
        q["segments"][0]["destination"] == "DEMO4"
        for q in secondary["query"]["bound_queries"]
    )


def test_unknown_category_is_pending_across_destination_correction(chat):
    first = turn(chat, "Next bus to Nellore tomorrow?")
    selected = turn(chat, "2", first)
    unknown = turn(chat, "Only imaginary premium", selected)
    assert unknown["state"] == "AWAITING_CATEGORY" and unknown["requires_clarification"]
    assert unknown["context"]["unresolved_category"] == "imaginary premium"
    assert unknown["selected_journey"] is None and not unknown["result_set"]
    assert unknown["clarification_choices"] and not unknown["results"]
    corrected = turn(chat, "No, I meant Tirupati", unknown)
    assert corrected["context"]["destination"] == "DEMO2"
    assert corrected["context"]["unresolved_category"] == "imaginary premium"
    assert corrected["state"] == "AWAITING_CATEGORY" and not corrected["results"]
    summary = turn(chat, "Summarize my journey", corrected)
    assert summary["context"]["destination"] == "DEMO2" and summary["context"].get(
        "unresolved_category"
    )
    resolved = turn(chat, "Only Super Luxury", summary)
    assert resolved["context"]["filters"]["category"] == "luxury" and not resolved[
        "context"
    ].get("unresolved_category")


def test_negative_category_correction_retains_explicit_non_ac_constraint(chat):
    first = turn(chat, "Next bus to Nellore tomorrow?")
    filtered = turn(chat, "Only AC", first)
    selected = turn(chat, "1", filtered)
    ordinary = turn(chat, "Not AC, ordinary", selected)
    assert ordinary["context"]["filters"]["ac"] is False
    assert ordinary["context"]["unresolved_category"] == "ordinary"
    assert (
        not ordinary["context"]["filters"].get("category")
        and not ordinary["selected_journey"]
    )
