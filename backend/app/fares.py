from sqlalchemy import select

from .domain import Fare, Service
from .operations import Trip
from .records import FareOverride


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
        return self.format_quote(amount, source)

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
