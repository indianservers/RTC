"""Bounded tool dependency planning; reuse facts, never invent calculations."""

from copy import deepcopy


class ConversationQueryPlanner:
    journey_intents = frozenset(
        {
            "NEXT_BUS",
            "FIRST_BUS",
            "LAST_BUS",
            "CHEAPEST_BUS",
            "FASTEST_BUS",
            "BUSES_BETWEEN",
            "FARE_COMPARISON",
        }
    )
    projections = frozenset({"TICKET_FARE", "GET_FARE", "ARRIVAL_TIME"})

    def plan(self, intents):
        unique = list(dict.fromkeys(intents))[:3]
        return sorted(
            unique,
            key=lambda i: (
                0 if i in self.journey_intents else 1 if i in self.projections else 2
            ),
        )

    def project(self, intent, primary, query, service_id=None):
        if (
            intent not in self.projections
            or primary is None
            or not primary.get("results")
        ):
            return None
        rows = [
            r
            for r in primary["results"]
            if not service_id or r.get("service_id") == service_id
        ]
        if not rows or any("departure" not in r or "arrival" not in r for r in rows):
            return None
        return {
            "intent": intent,
            "status": "KNOWN",
            "query": query.model_dump(mode="json"),
            "matched_stations": deepcopy(primary.get("matched_stations", {})),
            "results": deepcopy(rows),
            "warnings": ["Reused structured database results for the same journey."],
            "pagination": {},
            "executor": "ExecutionPlanner.project",
        }


# Compatibility for existing imports; one planner implementation.
ExecutionPlanner = ConversationQueryPlanner
