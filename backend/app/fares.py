from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from .domain import Fare, Service
from .operations import Trip
from .records import FareOverride, FareRule, FareTable


@event.listens_for(Session, "after_flush")
def clear_rule_cache(session, context):
    if any(
        isinstance(row, (FareRule, FareTable))
        for row in session.new | session.dirty | session.deleted
    ):
        session.info.pop("fare_rule_index", None)


class FareEngine:
    def __init__(self, session):
        self.session = session

    def quote(self, service_id, origin_id, destination_id, day):
        service = self.session.get(Service, service_id)
        if not service:
            raise ValueError("Unknown service")
        trip = self.session.scalar(
            select(Trip).where(Trip.service_id == service_id, Trip.service_date == day)
        )
        override = (
            self.session.scalar(
                select(FareOverride).where(
                    FareOverride.trip_id == trip.id,
                    FareOverride.origin_id == origin_id,
                    FareOverride.destination_id == destination_id,
                    FareOverride.active.is_(True),
                )
            )
            if trip
            else None
        )
        stage = self.session.scalar(
            select(Fare)
            .where(
                Fare.service_id == service_id,
                Fare.origin_id == origin_id,
                Fare.destination_id == destination_id,
                Fare.valid_from <= day,
                Fare.valid_to >= day,
                Fare.active.is_(True),
            )
            .order_by(Fare.valid_from.desc())
        )
        amount = override.amount if override else stage.amount if stage else None
        source = (
            override.dataset_source
            if override
            else stage.dataset_source
            if stage
            else None
        )
        from .domain import Stop

        stops = list(
            self.session.scalars(
                select(Stop).where(
                    Stop.route_id == service.route_id, Stop.active.is_(True)
                )
            )
        )
        a = next((s for s in stops if s.station_id == origin_id), None)
        b = next((s for s in stops if s.station_id == destination_id), None)
        distance = (
            b.distance_km - a.distance_km
            if a and b and a.sequence < b.sequence
            else None
        )
        return self.calculate(service, day, amount, source, distance, bool(override))

    def rules(self):
        if "fare_rule_index" not in self.session.info:
            index = {}
            for rule, table in self.session.execute(
                select(FareRule, FareTable)
                .join(FareTable, FareTable.id == FareRule.table_id)
                .where(FareRule.active.is_(True), FareTable.active.is_(True))
            ):
                index.setdefault((table.operator_id, table.category_id), []).append(
                    rule
                )
            self.session.info["fare_rule_index"] = index
        return self.session.info["fare_rule_index"]

    def calculate(self, service, day, amount, source, distance, trip_override=False):
        if trip_override:
            result = self.format_quote(amount, source)
            result["basis"] = "EXACT_TRIP_OVERRIDE"
            return result
        rules = [
            r
            for r in self.rules().get((service.operator_id, service.category_id), [])
            if (r.valid_from is None or r.valid_from <= day)
            and (r.valid_to is None or r.valid_to >= day)
        ]
        if len(rules) > 1:
            result = self.format_quote(None, None)
            result["missing_component"] = "conflicting active fare rules"
            return result
        if not rules:
            return self.format_quote(amount, source)
        rule = rules[0]
        base = (
            Decimal(amount)
            if amount is not None
            else max(rule.minimum, rule.per_km * distance)
            if distance is not None
            else None
        )
        if base is None:
            return self.format_quote(None, None)
        base = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        surcharge = (
            Decimal(rule.flat_surcharge or 0)
            + base * Decimal(rule.percent_surcharge or 0) / 100
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        result = self.format_quote(base + surcharge, source or rule.dataset_source)
        result.update(
            base_fare=str(base),
            surcharge=str(surcharge),
            rule_id=rule.id,
            basis="SEGMENT_PLUS_RULE_SURCHARGE"
            if amount is not None
            else "DISTANCE_RULE",
            rule_source=rule.dataset_source,
        )
        return result

    @staticmethod
    def format_quote(amount, source):
        """Format a DB-resolved segment tariff; shared by batched timetable reads."""
        if amount is None:
            return {
                "base_fare": None,
                "surcharge": None,
                "discount": None,
                "total": None,
                "currency": "INR",
                "fare_status": "UNKNOWN",
                "missing_component": "valid segment tariff",
            }
        amount = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "base_fare": str(amount),
            "surcharge": None,
            "discount": None,
            "total": str(amount),
            "currency": "INR",
            "fare_status": "KNOWN",
            "source": source,
            "concession_eligibility": "NOT_EVALUATED",
        }
