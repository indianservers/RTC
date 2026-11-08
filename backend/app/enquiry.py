from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .availability import seat_availability, utc
from .catalog import Concession, Eligibility, Facility
from .domain import Category, Operator, Repository, Service, Stop
from .operations import PlatformAssignment, StationBay, Trip


class JourneyQuery(BaseModel):
    origin: str
    destination: str
    at: AwareDatetime
    days: int = Field(default=1, ge=1, le=7)
    category: str | None = None
    operator: str | None = None
    amenity: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class Enquiry:
    def __init__(self, session: Session):
        self.session = session
        self.repository = Repository(session)

    def _rows(self, q: JourneyQuery):
        rows = self.repository.journeys(
            q.origin, q.destination, q.at, q.days, q.category, q.amenity
        )
        if q.operator:
            op = self.session.scalar(
                select(Operator).where(
                    (Operator.id == q.operator) | (Operator.code == q.operator)
                )
            )
            if not op:
                raise ValueError("Unknown operator")
            ids = set(
                self.session.scalars(
                    select(Service.id).where(Service.operator_id == op.id)
                )
            )
            rows = [r for r in rows if r["service_id"] in ids]
        return rows

    def _page(self, rows, q):
        return rows[q.offset : q.offset + q.limit]

    def get_next_buses(self, q: JourneyQuery):
        return self._page(self._rows(q), q)

    def _day(self, q: JourneyQuery, day: date):
        station = self.repository.resolve_station(q.origin)
        at = datetime.combine(day, time.min, ZoneInfo(station.timezone))
        return self._rows(q.model_copy(update={"at": at, "days": 1}))

    def get_first_bus(self, q: JourneyQuery, day: date):
        rows = self._day(q, day)
        return rows[:1]

    def get_last_bus(self, q: JourneyQuery, day: date):
        rows = self._day(q, day)
        return rows[-1:]

    def get_bus_fare(self, q: JourneyQuery):
        return self._page(
            [
                {
                    "service_id": r["service_id"],
                    "service_date": r["service_date"],
                    "amount": r["fare"],
                    "currency": "INR",
                    "known": r["fare"] is not None,
                    "dataset_source": r["dataset_source"],
                }
                for r in self._rows(q)
            ],
            q,
        )

    def get_available_bus_types(self, q: JourneyQuery):
        ids = {r["service_id"] for r in self._rows(q)}
        return self._page(
            list(
                self.session.scalars(
                    select(Category)
                    .join(Service, Service.category_id == Category.id)
                    .where(Service.id.in_(ids))
                    .distinct()
                    .order_by(Category.name)
                )
            ),
            q,
        )

    def get_service_details(self, service_id: str):
        row = self.session.get(Service, service_id)
        if row is None or not row.active:
            raise ValueError("Unknown service")
        return row

    def get_route_stops(self, service_id: str):
        service = self.get_service_details(service_id)
        return list(
            self.session.scalars(
                select(Stop)
                .where(Stop.route_id == service.route_id, Stop.active.is_(True))
                .order_by(Stop.sequence)
            )
        )

    def get_journey_duration(self, q: JourneyQuery):
        return [
            {
                "service_id": r["service_id"],
                "minutes": int((r["arrival"] - r["departure"]).total_seconds() / 60),
            }
            for r in self.get_next_buses(q)
        ]

    def get_arrival_time(self, q: JourneyQuery):
        return [
            {
                "service_id": r["service_id"],
                "arrival": r["arrival"],
                "kind": r["arrival_kind"],
                "dataset_source": r["dataset_source"],
            }
            for r in self.get_next_buses(q)
        ]

    def get_platform_assignment(self, trip_id: str, station: str, at: datetime):
        station_id = self.repository.resolve_station(station).id
        rows = self.session.scalars(
            select(PlatformAssignment)
            .join(StationBay, StationBay.id == PlatformAssignment.bay_id)
            .where(
                PlatformAssignment.trip_id == trip_id,
                StationBay.station_id == station_id,
                PlatformAssignment.verified.is_(True),
                PlatformAssignment.active.is_(True),
            )
            .order_by(PlatformAssignment.effective_at.desc())
        )
        for row in rows:
            if utc(row.effective_at) <= utc(at) < utc(row.expires_at):
                bay = self.session.get(StationBay, row.bay_id)
                return {
                    "status": "known",
                    "bay": bay.code if bay else None,
                    "source_id": row.source_id,
                    "effective_at": utc(row.effective_at),
                    "dataset_source": row.dataset_source,
                }
        return {"status": "unknown", "bay": None}

    def get_seat_availability(self, trip_id: str, at: datetime, requested: int = 1):
        return seat_availability(self.session, trip_id, at, requested)

    def get_service_status(self, service_id: str, day: date):
        self.get_service_details(service_id)
        trip = self.session.scalar(
            select(Trip).where(
                Trip.service_id == service_id,
                Trip.service_date == day,
                Trip.active.is_(True),
            )
        )
        return {
            "status": trip.status if trip else "scheduled_only",
            "trip_id": trip.id if trip else None,
            "dataset_source": trip.dataset_source if trip else None,
        }

    def get_cheapest_services(self, q: JourneyQuery):
        return self._page(
            sorted(
                [r for r in self._rows(q) if r["fare"] is not None],
                key=lambda r: Decimal(r["fare"]),
            ),
            q,
        )

    def get_fastest_services(self, q: JourneyQuery):
        return self._page(
            sorted(self._rows(q), key=lambda r: r["arrival"] - r["departure"]), q
        )

    def get_direct_services(self, q: JourneyQuery):
        return self.get_next_buses(q)

    def get_connecting_services(self, q: JourneyQuery, minimum_transfer: int = 15):
        if not 1 <= minimum_transfer <= 180:
            raise ValueError("Transfer window must be 1–180 minutes")
        origin = self.repository.resolve_station(q.origin).id
        destination = self.repository.resolve_station(q.destination).id
        # One transfer, bounded candidate stations and legs.
        candidates = list(
            self.session.scalars(
                select(Stop.station_id)
                .where(Stop.active.is_(True))
                .distinct()
                .order_by(Stop.station_id)
                .limit(100)
            )
        )
        results = []
        for station in candidates:
            if station in (origin, destination):
                continue
            first = self._rows(q.model_copy(update={"destination": station}))[:100]
            for leg in first:
                after = leg["arrival"] + timedelta(minutes=minimum_transfer)
                second = self._rows(
                    q.model_copy(update={"origin": station, "at": after, "days": 1})
                )[:100]
                for onward in second:
                    if onward["service_id"] == leg["service_id"] or onward[
                        "arrival"
                    ] > q.at + timedelta(days=q.days):
                        continue
                    results.append(
                        {
                            "transfer_station_id": station,
                            "legs": [leg, onward],
                            "arrival": onward["arrival"],
                        }
                    )
                if len(results) >= 500:
                    break
            if len(results) >= 500:
                break
        return self._page(sorted(results, key=lambda r: r["arrival"]), q)

    def get_services_via_stop(self, q: JourneyQuery, via: str):
        via_id = self.repository.resolve_station(via).id
        origin = self.repository.resolve_station(q.origin).id
        destination = self.repository.resolve_station(q.destination).id
        results = []
        for row in self._rows(q):
            stops = self.get_route_stops(row["service_id"])
            if any(
                a.station_id == origin
                and b.station_id == via_id
                and c.station_id == destination
                and a.sequence < b.sequence < c.sequence
                for a in stops
                for b in stops
                for c in stops
            ):
                results.append(row)
        return self._page(results, q)

    def get_operator_services(self, operator: str, limit: int = 20, offset: int = 0):
        op = self.session.scalar(
            select(Operator).where(
                (Operator.id == operator) | (Operator.code == operator)
            )
        )
        if not op:
            raise ValueError("Unknown operator")
        return list(
            self.session.scalars(
                select(Service)
                .where(Service.operator_id == op.id, Service.active.is_(True))
                .order_by(Service.number)
                .offset(offset)
                .limit(min(limit, 100))
            )
        )

    def get_concessions(self, operator: str, day: date):
        op = self.session.scalar(
            select(Operator).where(
                (Operator.id == operator) | (Operator.code == operator)
            )
        )
        if not op:
            raise ValueError("Unknown operator")
        rows = self.session.scalars(
            select(Concession).where(
                Concession.operator_id == op.id,
                Concession.active.is_(True),
                Concession.valid_from <= day,
                Concession.valid_to >= day,
            )
        )
        return [
            {
                "name": r.name,
                "percent": str(r.percent),
                "eligibility_confirmed": False,
                "criteria": list(
                    self.session.scalars(
                        select(Eligibility.criterion).where(
                            Eligibility.concession_id == r.id
                        )
                    )
                ),
                "dataset_source": r.dataset_source,
            }
            for r in rows
        ]

    def get_station_facilities(self, station: str):
        station_id = self.repository.resolve_station(station).id
        return list(
            self.session.scalars(
                select(Facility)
                .where(Facility.station_id == station_id, Facility.active.is_(True))
                .order_by(Facility.name)
            )
        )
