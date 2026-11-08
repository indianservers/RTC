"""Typed local journey planning facade over the existing timetable repository."""

from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
from itertools import pairwise
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from .domain import Category, Operator, Service
from .engine import EnquiryRequest, RTCEnquiryEngine, SearchFilters
from .enquiry import JourneyQuery
from .fares import FareEngine
from .route_search import RouteSearch
from .status import OperationalStatusEngine

Ranking = Literal[
    "EARLIEST_ARRIVAL",
    "EARLIEST_DEPARTURE",
    "LOWEST_FARE",
    "SHORTEST_DURATION",
    "FEWEST_TRANSFERS",
    "MINIMUM_WAIT",
    "PREFERRED_BUS_CATEGORY",
]


class JourneyConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: str = Field(min_length=1, max_length=250)
    destination: str = Field(min_length=1, max_length=250)
    earliest_departure: AwareDatetime
    transfer_station: str | None = Field(default=None, min_length=1, max_length=250)
    latest_departure: AwareDatetime | None = None
    arrival_deadline: AwareDatetime | None = None
    horizon_hours: int = Field(default=48, ge=1, le=48)
    max_transfers: int = Field(default=2, ge=0, le=2)
    minimum_transfer_minutes: int = Field(default=15, ge=1, le=180)
    maximum_wait_minutes: int = Field(default=180, ge=1, le=1440)
    maximum_total_wait_minutes: int = Field(default=360, ge=1, le=2880)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    passengers: int = Field(default=1, ge=1, le=100)
    require_verified_seats: bool = False
    ranking: Ranking = "EARLIEST_ARRIVAL"
    preferred_category: str | None = Field(default=None, max_length=100)
    max_expansions: int = Field(default=5000, ge=1, le=20000)
    max_services_per_segment: int = Field(default=1000, ge=1, le=10000)
    avoid_verified_disruptions: bool = True
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1000)
    pareto_only: bool = False

    @model_validator(mode="after")
    def consistent(self):
        if self.origin == self.destination:
            raise ValueError("Origin equals destination")
        if self.latest_departure and self.latest_departure < self.earliest_departure:
            raise ValueError("Departure window is reversed")
        if self.arrival_deadline and self.arrival_deadline <= self.earliest_departure:
            raise ValueError("Arrival deadline precedes departure")
        if self.minimum_transfer_minutes > self.maximum_wait_minutes:
            raise ValueError("Minimum transfer exceeds maximum waiting time")
        return self


class JourneyLeg(BaseModel):
    service_id: str
    trip_id: str | None
    service_date: date
    origin: str
    destination: str
    boarding_stop_id: str
    alighting_stop_id: str
    boarding_at: AwareDatetime
    alighting_at: AwareDatetime
    category: str
    operator_id: str
    fare: Decimal | None
    fare_breakdown: dict
    source: str
    operational_status: dict
    departure_kind: str
    arrival_kind: str
    platform: dict
    warnings: list[str] = Field(default_factory=list)


class Transfer(BaseModel):
    station_id: str
    arrival_at: AwareDatetime
    departure_at: AwareDatetime
    wait_minutes: float
    minimum_minutes: int


class Itinerary(BaseModel):
    journey_id: str
    origin: str
    destination: str
    departure_at: AwareDatetime
    arrival_at: AwareDatetime
    transfer_count: int
    total_duration_minutes: float
    total_wait_minutes: float
    fare_status: Literal["KNOWN", "PARTIAL", "UNKNOWN"]
    total_fare: Decimal | None
    known_subtotal: Decimal
    currency: Literal["INR"] = "INR"
    sources: list[str]
    legs: list[JourneyLeg]
    transfers: list[Transfer]

    @model_validator(mode="after")
    def invariant(self):
        if not self.legs or len(self.legs) != self.transfer_count + 1:
            raise ValueError("Invalid leg count")
        if (
            self.origin != self.legs[0].origin
            or self.destination != self.legs[-1].destination
        ):
            raise ValueError("Invalid endpoints")
        if (
            self.departure_at != self.legs[0].boarding_at
            or self.arrival_at != self.legs[-1].alighting_at
        ):
            raise ValueError("Invalid itinerary timestamps")
        if any(x.alighting_at < x.boarding_at for x in self.legs):
            raise ValueError("Negative leg duration")
        if len(self.transfers) != self.transfer_count:
            raise ValueError("Invalid transfer count")
        for a, b, t in zip(self.legs, self.legs[1:], self.transfers):
            wait = (b.boarding_at - a.alighting_at).total_seconds() / 60
            if (
                a.destination != b.origin
                or t.station_id != a.destination
                or wait < t.minimum_minutes
                or t.wait_minutes != wait
            ):
                raise ValueError("Invalid transfer")
        if self.total_duration_minutes != (
            self.arrival_at - self.departure_at
        ).total_seconds() / 60 or self.total_wait_minutes != sum(
            t.wait_minutes for t in self.transfers
        ):
            raise ValueError("Invalid duration totals")
        known = sum((x.fare for x in self.legs if x.fare is not None), Decimal(0))
        status = (
            "KNOWN"
            if all(x.fare is not None for x in self.legs)
            else "PARTIAL"
            if any(x.fare is not None for x in self.legs)
            else "UNKNOWN"
        )
        if (
            self.known_subtotal != known
            or self.fare_status != status
            or self.total_fare != (known if status == "KNOWN" else None)
        ):
            raise ValueError("Invalid fare total")
        return self


class JourneyResults(BaseModel):
    applied_filters: JourneyConstraints
    itineraries: list[Itinerary]
    warnings: list[str]
    search_horizon_end: AwareDatetime
    search_stats: dict
    pagination: dict
    recommendations: dict[str, str | None] = Field(default_factory=dict)
    comparisons: list[str] = Field(default_factory=list)


class RecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    search: JourneyConstraints
    missed_service_id: str
    missed_service_date: date
    explicitly_missed: bool = False


class JourneyPlanner:
    def __init__(self, session: Session):
        self.session = session
        self.engine = RTCEnquiryEngine(session)
        self.enquiry = self.engine.enquiry
        self._services: dict[str, Service | None] = {}
        self._categories: dict[str, Category | None] = {}
        self._disruptions: dict[str, list] = {}

    def _itinerary(self, path, c):
        legs = []
        for row in path:
            service = self._services[row["service_id"]]
            if service.category_id not in self._categories:
                self._categories[service.category_id] = self.session.get(
                    Category, service.category_id
                )
            category = self._categories[service.category_id]
            fare = FareEngine.format_quote(row["fare"], row["fare_source"])
            status = (
                OperationalStatusEngine(self.session).status(
                    row["trip_id"], c.earliest_departure
                )
                if row["trip_id"]
                else {"status": "SCHEDULED_ONLY", "gps_status": "UNKNOWN"}
            )
            platform = (
                self.enquiry.get_platform_assignment(
                    row["trip_id"], row["origin_id"], c.earliest_departure
                )
                if row["trip_id"]
                else {"status": "unknown", "bay": None}
            )
            alerts = self._disruptions.get(service.id, [])
            legs.append(
                JourneyLeg(
                    service_id=service.id,
                    trip_id=row["trip_id"],
                    service_date=row["service_date"],
                    origin=row["origin_id"],
                    destination=row["destination_id"],
                    boarding_stop_id=row["boarding_stop_id"],
                    alighting_stop_id=row["alighting_stop_id"],
                    boarding_at=row["departure"],
                    alighting_at=row["arrival"],
                    category=category.name,
                    operator_id=service.operator_id,
                    fare=Decimal(fare["total"]) if fare["total"] is not None else None,
                    fare_breakdown=fare,
                    source=row["dataset_source"],
                    operational_status=status,
                    departure_kind=row["departure_kind"],
                    arrival_kind=row["arrival_kind"],
                    platform=platform,
                    warnings=[a.description for a in alerts],
                )
            )
        transfers = [
            Transfer(
                station_id=a.destination,
                arrival_at=a.alighting_at,
                departure_at=b.boarding_at,
                wait_minutes=(b.boarding_at - a.alighting_at).total_seconds() / 60,
                minimum_minutes=c.minimum_transfer_minutes,
            )
            for a, b in pairwise(legs)
        ]
        known = sum((leg.fare for leg in legs if leg.fare is not None), Decimal(0))
        fare_status = (
            "KNOWN"
            if all(x.fare is not None for x in legs)
            else "PARTIAL"
            if any(x.fare is not None for x in legs)
            else "UNKNOWN"
        )
        key = "|".join(
            f"{r.service_id}:{r.service_date}:{r.boarding_stop_id}:{r.alighting_stop_id}"
            for r in legs
        )
        return Itinerary(
            journey_id=sha256(key.encode()).hexdigest()[:24],
            origin=legs[0].origin,
            destination=legs[-1].destination,
            departure_at=legs[0].boarding_at,
            arrival_at=legs[-1].alighting_at,
            transfer_count=len(legs) - 1,
            total_duration_minutes=(
                legs[-1].alighting_at - legs[0].boarding_at
            ).total_seconds()
            / 60,
            total_wait_minutes=sum(t.wait_minutes for t in transfers),
            fare_status=fare_status,
            total_fare=known if fare_status == "KNOWN" else None,
            known_subtotal=known,
            sources=sorted({x.source for x in legs}),
            legs=legs,
            transfers=transfers,
        )

    @staticmethod
    def rank(items, mode: Ranking, preferred_category=None):
        if mode == "LOWEST_FARE":
            items = [i for i in items if i.total_fare is not None]

        def score(i):
            return {
                "EARLIEST_ARRIVAL": i.arrival_at.timestamp(),
                "EARLIEST_DEPARTURE": i.departure_at.timestamp(),
                "LOWEST_FARE": i.total_fare,
                "SHORTEST_DURATION": i.total_duration_minutes,
                "FEWEST_TRANSFERS": i.transfer_count,
                "MINIMUM_WAIT": i.total_wait_minutes,
                "PREFERRED_BUS_CATEGORY": sum(
                    x.category.casefold() != (preferred_category or "").casefold()
                    for x in i.legs
                ),
            }[mode]

        return sorted(
            items, key=lambda i: (score(i), i.arrival_at, i.departure_at, i.journey_id)
        )

    def search(self, c: JourneyConstraints, excluded=()):
        q = JourneyQuery(
            origin=c.origin,
            destination=c.destination,
            at=c.earliest_departure,
            days=(c.horizon_hours + 23) // 24,
            category=None,
            operator=c.filters.operator,
            amenity=c.filters.amenity,
        )
        # Journey-wide price/time bounds are evaluated on complete itineraries.
        leg_filters = c.filters.model_copy(
            update={
                "min_fare": None,
                "max_fare": None,
                "after": None,
                "before": None,
                "arrival_after": None,
                "arrival_before": None,
                "max_duration_minutes": None,
            }
        )
        if leg_filters.category:
            from sqlalchemy import select

            matches = list(
                self.session.scalars(
                    select(Category).where(
                        Category.active.is_(True),
                        (Category.id == leg_filters.category)
                        | (Category.name == leg_filters.category)
                        | (Category.code == leg_filters.category),
                    )
                )
            )
            if len(matches) != 1:
                raise ValueError("Unknown or ambiguous category")
            leg_filters = leg_filters.model_copy(update={"category": matches[0].id})
        r = EnquiryRequest(
            intent="BUSES_BETWEEN",
            travel_date=c.earliest_departure.date(),
            filters=leg_filters,
        )
        operator_id = None
        if c.filters.operator:
            from sqlalchemy import select

            operator = self.session.scalar(
                select(Operator).where(
                    Operator.active.is_(True),
                    (Operator.id == c.filters.operator)
                    | (Operator.code == c.filters.operator),
                )
            )
            if operator is None:
                raise ValueError("Unknown operator")
            operator_id = operator.id

        eligibility = {}
        self.engine.vehicle_cache = {}
        self.engine.vehicle_type_cache = {}
        self._services.clear()
        self.enquiry.repository.schedule_services.clear()
        self._categories.clear()
        self._disruptions.clear()

        def prepare_metadata():
            if len(self.enquiry.repository.schedule_services) == len(self._services):
                return
            from sqlalchemy import select

            from .catalog import Vehicle, VehicleType
            from .links import ServiceVehicle
            from .records import Disruption

            pending = {
                sid: svc
                for sid, svc in self.enquiry.repository.schedule_services.items()
                if sid not in self._services
            }
            if not pending:
                return
            self._services.update(pending)
            for sid in pending:
                self._disruptions[sid] = []
            vehicles = self.session.execute(
                select(ServiceVehicle.service_id, Vehicle)
                .join(Vehicle, Vehicle.id == ServiceVehicle.vehicle_id)
                .where(
                    ServiceVehicle.service_id.in_(pending),
                    ServiceVehicle.active.is_(True),
                )
                .order_by(ServiceVehicle.service_id, Vehicle.id)
            ).all()
            type_ids = set()
            for sid, vehicle in vehicles:
                self.engine.vehicle_cache.setdefault(sid, vehicle)
                type_ids.add(vehicle.type_id)
            if type_ids:
                self.engine.vehicle_type_cache.update(
                    {
                        v.id: v
                        for v in self.session.scalars(
                            select(VehicleType).where(VehicleType.id.in_(type_ids))
                        )
                    }
                )
            alerts = self.session.scalars(
                select(Disruption).where(
                    Disruption.service_id.in_(pending),
                    Disruption.active.is_(True),
                    Disruption.verified.is_(True),
                    Disruption.effective_at <= c.earliest_departure,
                    Disruption.expires_at > c.earliest_departure,
                )
            )
            for alert in alerts:
                self._disruptions[alert.service_id].append(alert)

        def allowed(row):
            prepare_metadata()
            if c.avoid_verified_disruptions and self._disruptions.get(
                row["service_id"]
            ):
                return False
            if row["service_id"] not in self._services:
                self._services[row["service_id"]] = self.session.get(
                    Service, row["service_id"]
                )
            service = self._services[row["service_id"]]
            if leg_filters.category and service.category_id != leg_filters.category:
                return False
            if operator_id and service.operator_id != operator_id:
                return False
            if service.id not in eligibility:
                eligibility[service.id] = bool(
                    self.engine._filter([row], r, "BUSES_BETWEEN")
                )
            if not eligibility[service.id]:
                return False
            if c.require_verified_seats:
                from .availability import seat_availability

                snapshot = seat_availability(
                    self.session,
                    row["trip_id"] or "",
                    c.earliest_departure,
                    c.passengers,
                    row["origin_id"],
                    row["destination_id"],
                )
                if snapshot.get("status") != "available":
                    return False
            return True

        graph = RouteSearch(self.enquiry)
        paths = graph.timed_paths(
            q,
            max_transfers=c.max_transfers,
            minimum_transfer=c.minimum_transfer_minutes,
            maximum_wait=c.maximum_wait_minutes,
            maximum_total_wait=c.maximum_total_wait_minutes,
            horizon_hours=c.horizon_hours,
            max_expansions=c.max_expansions,
            max_services_per_segment=c.max_services_per_segment,
            leg_filter=allowed,
            latest_departure=c.latest_departure,
            arrival_deadline=c.arrival_deadline,
            excluded_services=excluded,
        )
        items = [self._itinerary(path, c) for path in paths]
        f = c.filters
        items = [
            i
            for i in items
            if (
                f.max_fare is None
                or (i.total_fare is not None and i.total_fare <= f.max_fare)
            )
            and (
                f.min_fare is None
                or (i.total_fare is not None and i.total_fare >= f.min_fare)
            )
            and (not f.after or i.departure_at >= f.after)
            and (not f.before or i.departure_at < f.before)
            and (not f.arrival_after or i.arrival_at >= f.arrival_after)
            and (not f.arrival_before or i.arrival_at < f.arrival_before)
            and (
                not f.max_duration_minutes
                or i.total_duration_minutes <= f.max_duration_minutes
            )
        ]
        if c.transfer_station:
            resolved = self.engine.resolver.resolve(c.transfer_station)
            if resolved["status"] != "KNOWN":
                raise ValueError("Choose a unique transfer station code.")
            transfer_id = resolved["candidates"][0]["id"]
            items = [
                i
                for i in items
                if any(t.station_id == transfer_id for t in i.transfers)
            ]
        if c.pareto_only:
            if len(items) > 2000:
                raise ValueError(
                    "Pareto candidate resource limit exceeded; narrow the search"
                )

            def dominates(a, b):
                if a.total_fare is None or b.total_fare is None:
                    return False
                aa = (
                    a.arrival_at,
                    a.total_fare,
                    a.transfer_count,
                    a.total_wait_minutes,
                )
                bb = (
                    b.arrival_at,
                    b.total_fare,
                    b.transfer_count,
                    b.total_wait_minutes,
                )
                return all(x <= y for x, y in zip(aa, bb)) and any(
                    x < y for x, y in zip(aa, bb)
                )

            items = [
                b
                for b in items
                if not any(dominates(a, b) for a in items if a is not b)
            ]
        items = self.rank(items, c.ranking, c.preferred_category)
        warnings = [
            "Scheduled or estimated journeys do not confirm GPS, seats or guaranteed connections.",
            "Transfers require the same physical station; inter-stand travel is unsupported.",
            "Concessions and through-ticket discounts are not evaluated.",
            "Active verified service disruption records are conservatively excluded when avoid_verified_disruptions is enabled.",
        ]
        if graph.stats["truncated"]:
            warnings.append(
                "Search resource limit reached; results are partial and optimality is not guaranteed."
            )
        if not items:
            warnings.append(
                "No eligible itinerary found within the horizon and resource bounds. Consider explicitly relaxing category, fare, time or transfer constraints."
            )
        comparisons = []
        if len(items) > 1:
            a, b = items[:2]
            if a.arrival_at != b.arrival_at:
                earlier = a if a.arrival_at < b.arrival_at else b
                comparisons.append(
                    f"Journey {earlier.journey_id} arrives earlier and requires {earlier.transfer_count} transfer(s)."
                )
            if (
                a.total_fare is not None
                and b.total_fare is not None
                and a.total_fare != b.total_fare
            ):
                cheaper = a if a.total_fare < b.total_fare else b
                comparisons.append(
                    f"Journey {cheaper.journey_id} costs INR {abs(a.total_fare - b.total_fare)} less."
                )
        return JourneyResults(
            applied_filters=c,
            comparisons=comparisons,
            itineraries=items[c.offset : c.offset + c.limit],
            warnings=warnings,
            search_horizon_end=c.earliest_departure + timedelta(hours=c.horizon_hours),
            search_stats=graph.stats,
            pagination={
                "offset": c.offset,
                "limit": c.limit,
                "eligible_count": len(items),
                "truncated": graph.stats["truncated"],
            },
        )

    def find_direct_journeys(self, c):
        return self.search(c.model_copy(update={"max_transfers": 0}))

    def find_connecting_journeys(self, c):
        return self.search(c)

    def find_alternatives_after_missed_bus(self, request: RecoveryRequest):
        if not request.explicitly_missed:
            raise ValueError(
                "Explicit missed-bus confirmation required; a scheduled time alone is insufficient"
            )
        service = self.enquiry.get_service_details(request.missed_service_id)
        # Validate the missed service segment/date against its local timetable.
        station = self.enquiry.repository.resolve_station(request.search.origin)
        from datetime import datetime, time
        from zoneinfo import ZoneInfo

        start = datetime.combine(
            request.missed_service_date, time.min, ZoneInfo(station.timezone)
        )
        stops = self.enquiry.get_route_stops(service.id)
        boarding = [a for a in stops if a.station_id == station.id and a.boarding]
        alighting = [
            b
            for b in stops
            if b.alighting and any(a.sequence < b.sequence for a in boarding)
        ]
        if not alighting:
            raise ValueError("Missed service has no valid onward boarding segment")
        rows = self.enquiry._rows(
            JourneyQuery(
                origin=station.id,
                destination=alighting[-1].station_id,
                at=start,
                days=3,
            )
        )
        missed = [
            r
            for r in rows
            if r["service_id"] == service.id
            and r["service_date"] == request.missed_service_date
        ]
        if not missed:
            raise ValueError("Missed service does not serve the requested segment/date")
        after = max(
            request.search.earliest_departure,
            missed[0]["departure"] + timedelta(microseconds=1),
        )
        c = request.search.model_copy(update={"earliest_departure": after})
        c = JourneyConstraints.model_validate(c.model_dump())
        c = c.model_copy(update={"limit": 100, "offset": 0})
        result = self.search(c)
        result.itineraries = [
            i
            for i in result.itineraries
            if not any(
                l.service_id == service.id
                and l.service_date == request.missed_service_date
                for l in i.legs
            )
        ]
        result.pagination["eligible_count"] = len(result.itineraries)
        direct = [i for i in result.itineraries if i.transfer_count == 0]
        connecting = [i for i in result.itineraries if i.transfer_count > 0]

        def best(items, ranking):
            ranked = self.rank(items, ranking, c.preferred_category)
            return ranked[0].journey_id if ranked else None

        result.recommendations = {
            "next_direct": best(direct, "EARLIEST_DEPARTURE"),
            "fastest_connection": best(connecting, "EARLIEST_ARRIVAL"),
            "lowest_known_fare": best(result.itineraries, "LOWEST_FARE"),
            "next_compatible": best(result.itineraries, "EARLIEST_DEPARTURE"),
        }
        return result

    def replan_journey(self, c):
        # Always query authoritative records afresh; never accept caller-supplied legs.
        return self.search(c)
