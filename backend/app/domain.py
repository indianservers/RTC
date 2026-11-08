import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    create_engine,
    event,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Entity:
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    dataset_source: Mapped[str] = mapped_column(default="DEMO")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Operator(Entity, Base):
    short_name: Mapped[str | None]
    headquarters_city_id: Mapped[str | None] = mapped_column(ForeignKey("cities.id"))
    website: Mapped[str | None]
    default_timezone: Mapped[str | None]
    __tablename__ = "transport_operators"
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]


class Station(Entity, Base):
    city_id: Mapped[str | None] = mapped_column(ForeignKey("cities.id"))
    name_native: Mapped[str | None]
    station_type: Mapped[str | None]
    address: Mapped[str | None]
    __tablename__ = "bus_stations"
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    timezone: Mapped[str] = mapped_column(default="Asia/Kolkata")


class Alias(Entity, Base):
    normalized_alias: Mapped[str | None] = mapped_column(index=True)
    language_code: Mapped[str | None]
    __tablename__ = "station_aliases"
    station_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"), index=True)
    name: Mapped[str] = mapped_column(unique=True)


class Category(Entity, Base):
    code: Mapped[str | None]
    name_native: Mapped[str | None]
    description: Mapped[str | None]
    service_tier: Mapped[str | None]
    fare_class_code: Mapped[str | None]
    __tablename__ = "bus_service_categories"
    operator_id: Mapped[str] = mapped_column(ForeignKey("transport_operators.id"))
    name: Mapped[str]
    __table_args__ = (UniqueConstraint("operator_id", "name"),)


class Route(Entity, Base):
    direction: Mapped[str | None]
    operator_id: Mapped[str | None] = mapped_column(
        ForeignKey("transport_operators.id")
    )
    origin_station_id: Mapped[str | None] = mapped_column(ForeignKey("bus_stations.id"))
    destination_station_id: Mapped[str | None] = mapped_column(
        ForeignKey("bus_stations.id")
    )
    route_name: Mapped[str | None]
    __tablename__ = "routes"
    code: Mapped[str] = mapped_column(unique=True)


class Stop(Entity, Base):
    arrival_offset_minutes: Mapped[int | None]
    departure_offset_minutes: Mapped[int | None]
    __tablename__ = "route_stops"
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"), index=True)
    station_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"), index=True)
    sequence: Mapped[int]
    offset_minutes: Mapped[int]
    distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    boarding: Mapped[bool] = mapped_column(default=True)
    alighting: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (
        UniqueConstraint("route_id", "sequence"),
        CheckConstraint("sequence >= 0 AND offset_minutes >= 0 AND distance_km >= 0"),
    )


class Service(Entity, Base):
    depot_id: Mapped[str | None] = mapped_column(ForeignKey("depots.id"))
    service_type: Mapped[str] = mapped_column(default="REGULAR")
    route_variant_id: Mapped[str | None] = mapped_column(
        ForeignKey("route_variants.id")
    )
    reservation_supported: Mapped[bool | None]
    __tablename__ = "services"
    operator_id: Mapped[str] = mapped_column(
        ForeignKey("transport_operators.id"), index=True
    )
    category_id: Mapped[str] = mapped_column(
        ForeignKey("bus_service_categories.id"), index=True
    )
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"), index=True)
    number: Mapped[str]
    departure_minutes: Mapped[int]
    weekdays: Mapped[str] = mapped_column(default="0123456")
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date] = mapped_column(Date)
    __table_args__ = (
        UniqueConstraint("operator_id", "number"),
        CheckConstraint(
            "departure_minutes >= 0 AND departure_minutes < 1440 AND valid_to >= valid_from"
        ),
    )


class ExceptionDay(Entity, Base):
    exception_type: Mapped[str | None]
    reason: Mapped[str | None]
    details: Mapped[dict | None] = mapped_column(JSON)
    __tablename__ = "service_calendar_exceptions"
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    service_date: Mapped[date] = mapped_column(Date)
    operates: Mapped[bool]
    __table_args__ = (UniqueConstraint("service_id", "service_date"),)


class Fare(Entity, Base):
    __tablename__ = "fare_stages"
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    origin_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"))
    destination_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date] = mapped_column(Date)
    __table_args__ = (CheckConstraint("amount >= 0 AND valid_to >= valid_from"),)


def database(url=None):
    target = url or os.getenv("DATABASE_URL", "sqlite:///rtc.db")
    from sqlalchemy.engine import make_url

    parsed = make_url(target)
    options = {"pool_pre_ping": True}
    if parsed.get_backend_name() == "postgresql":
        options.update(
            pool_size=int(os.getenv("RTC_DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("RTC_DB_MAX_OVERFLOW", "10")),
            pool_timeout=10,
            pool_recycle=900,
            connect_args={
                "connect_timeout": 5,
                "options": str(parsed.query.get("options", ""))
                + " -c statement_timeout="
                + os.getenv("RTC_DB_STATEMENT_TIMEOUT_MS", "15000"),
            },
        )
    elif parsed.get_backend_name() == "sqlite":
        options["connect_args"] = {"timeout": 15, "check_same_thread": False}
    engine = create_engine(target, **options)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def fk(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=15000")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")

    return engine


class Repository:
    def __init__(self, session: Session):
        self.session = session
        self.schedule_services: dict[str, Service] = {}

    def resolve_station(self, value):
        station = self.session.scalar(
            select(Station).where(
                (Station.id == value)
                | (Station.code == value)
                | (Station.name == value)
            )
        )
        if station is None:
            alias = self.session.scalar(select(Alias).where(Alias.name == value))
            station = self.session.get(Station, alias.station_id) if alias else None
        if not station or not station.active:
            raise ValueError("Unknown or inactive station")
        return station

    def journeys(
        self,
        origin,
        destination,
        at: datetime,
        days=1,
        category=None,
        amenity=None,
        service_limit=None,
    ):
        from .availability import utc
        from .catalog import Calendar
        from .links import ServiceVehicle
        from .operations import Trip
        from .records import FareOverride, ServiceStopTime, TripStopTime

        if at.tzinfo is None:
            raise ValueError("Timezone-aware timestamp required")
        start, end = self.resolve_station(origin), self.resolve_station(destination)
        zone = ZoneInfo(start.timezone)
        local = at.astimezone(zone)
        results = []
        origins = select(Stop.route_id).where(
            Stop.station_id == start.id, Stop.active.is_(True), Stop.boarding.is_(True)
        )
        destinations = select(Stop.route_id).where(
            Stop.station_id == end.id, Stop.active.is_(True), Stop.alighting.is_(True)
        )
        query = (
            select(Service)
            .join(Category, Category.id == Service.category_id)
            .join(Operator, Operator.id == Service.operator_id)
            .join(Route, Route.id == Service.route_id)
            .where(
                Service.active.is_(True),
                Category.active.is_(True),
                Operator.active.is_(True),
                Route.active.is_(True),
                Service.route_id.in_(origins),
                Service.route_id.in_(destinations),
            )
        )
        if category:
            query = query.where(Service.category_id == category)
        if amenity:
            from .catalog import Amenity

            query = (
                query.join(ServiceVehicle, ServiceVehicle.service_id == Service.id)
                .join(Amenity, Amenity.vehicle_id == ServiceVehicle.vehicle_id)
                .where(
                    Amenity.name == amenity,
                    Amenity.available.is_(True),
                    Amenity.active.is_(True),
                )
            )
        if service_limit is not None:
            query = query.order_by(Service.id).limit(service_limit + 1)
        services = list(self.session.scalars(query))
        if service_limit is not None and len(services) > service_limit:
            raise ValueError("Service resource limit exceeded; narrow the search")
        batch = None
        if service_limit is not None:
            from .timetable import TimetableBatch

            batch = TimetableBatch(self.session, services, local, days)
            self.schedule_services.update({s.id: s for s in services})
        for service in services:
            schedule_offsets = (
                batch.stop_times.get(service.id, {})
                if batch
                else {
                    r.stop_id: (r.arrival_offset, r.departure_offset)
                    for r in self.session.scalars(
                        select(ServiceStopTime).where(
                            ServiceStopTime.service_id == service.id,
                            ServiceStopTime.active.is_(True),
                        )
                    )
                }
            )
            stops = (
                batch.stops.get(service.route_id, [])
                if batch
                else list(
                    self.session.scalars(
                        select(Stop)
                        .where(Stop.route_id == service.route_id, Stop.active.is_(True))
                        .order_by(Stop.sequence)
                    )
                )
            )
            schedule_offsets = {
                stop.id: schedule_offsets.get(
                    stop.id,
                    (
                        stop.arrival_offset_minutes
                        if stop.arrival_offset_minutes is not None
                        else stop.offset_minutes,
                        stop.departure_offset_minutes
                        if stop.departure_offset_minutes is not None
                        else stop.offset_minutes,
                    ),
                )
                for stop in stops
            }
            for a in stops:
                for b in stops:
                    if (
                        a.station_id != start.id
                        or b.station_id != end.id
                        or a.sequence >= b.sequence
                        or not a.boarding
                        or not b.alighting
                    ):
                        continue
                    lookback = (
                        max(
                            max(
                                schedule_offsets.get(
                                    s.id, (s.offset_minutes, s.offset_minutes)
                                )
                            )
                            for s in stops
                        )
                        // 1440
                        + 1
                    )
                    for delta in range(-lookback, days + 1):
                        day = local.date() + timedelta(days=delta)
                        override = (
                            batch.exceptions.get((service.id, day))
                            if batch
                            else self.session.scalar(
                                select(ExceptionDay).where(
                                    ExceptionDay.service_id == service.id,
                                    ExceptionDay.service_date == day,
                                    ExceptionDay.active.is_(True),
                                )
                            )
                        )
                        details = (override.details or {}) if override else {}
                        if (
                            a.id in details.get("cancelled_stop_ids", [])
                            or b.id in details.get("cancelled_stop_ids", [])
                            or a.id in details.get("boarding_restricted_stop_ids", [])
                        ):
                            continue
                        variant_id = (
                            details.get("variant_id") or service.route_variant_id
                        )
                        if variant_id:
                            from .catalog import Variant
                            from .links import VariantStop

                            variant = self.session.get(Variant, variant_id)
                            members = set(
                                self.session.scalars(
                                    select(VariantStop.stop_id).where(
                                        VariantStop.variant_id == variant_id,
                                        VariantStop.active.is_(True),
                                    )
                                )
                            )
                            if (
                                not variant
                                or not variant.active
                                or variant.route_id != service.route_id
                                or a.id not in members
                                or b.id not in members
                            ):
                                continue
                        calendar = (
                            batch.calendar(service.id, day)
                            if batch
                            else self.session.scalar(
                                select(Calendar)
                                .where(
                                    Calendar.service_id == service.id,
                                    Calendar.active.is_(True),
                                    Calendar.valid_from <= day,
                                    Calendar.valid_to >= day,
                                )
                                .order_by(Calendar.valid_from.desc())
                            )
                        )
                        weekdays = calendar.weekdays if calendar else service.weekdays
                        runs = (
                            override.operates
                            if override
                            else str(day.weekday()) in weekdays
                        )
                        if (
                            not runs
                            or not service.valid_from <= day <= service.valid_to
                        ):
                            continue
                        base = datetime.combine(
                            day, datetime.min.time(), zone
                        ) + timedelta(
                            minutes=details.get(
                                "departure_minutes",
                                calendar.departure_minutes
                                if calendar
                                else service.departure_minutes,
                            )
                        )
                        departure = base + timedelta(
                            minutes=schedule_offsets.get(
                                a.id, (a.offset_minutes, a.offset_minutes)
                            )[1]
                        )
                        trip = (
                            batch.trips.get((service.id, day))
                            if batch
                            else self.session.scalar(
                                select(Trip).where(
                                    Trip.service_id == service.id,
                                    Trip.service_date == day,
                                    Trip.active.is_(True),
                                )
                            )
                        )
                        if trip and trip.planned_departure_at:
                            shift = (
                                utc(trip.planned_departure_at).astimezone(zone) - base
                            )
                            base += shift
                            departure += shift
                        if trip and trip.status == "cancelled":
                            continue
                        scheduled_departure = departure
                        departure_kind = "scheduled"
                        if trip:
                            observation = (
                                batch.observations.get((trip.id, a.id))
                                if batch
                                else self.session.scalar(
                                    select(TripStopTime)
                                    .where(
                                        TripStopTime.trip_id == trip.id,
                                        TripStopTime.stop_id == a.id,
                                        TripStopTime.active.is_(True),
                                        TripStopTime.verified.is_(True),
                                    )
                                    .order_by(TripStopTime.effective_at.desc())
                                )
                            )
                            if observation and utc(observation.effective_at) <= utc(
                                at
                            ) < utc(observation.expires_at):
                                if observation.actual_departure is not None:
                                    continue
                                if observation.estimated_departure is not None:
                                    departure = utc(
                                        observation.estimated_departure
                                    ).astimezone(zone)
                                    departure_kind = "estimated"
                        if not local <= departure < local + timedelta(days=days):
                            continue
                        fare = (
                            batch.fare(service.id, start.id, end.id, day)
                            if batch
                            else self.session.scalar(
                                select(Fare)
                                .where(
                                    Fare.active.is_(True),
                                    Fare.service_id == service.id,
                                    Fare.origin_id == start.id,
                                    Fare.destination_id == end.id,
                                    Fare.valid_from <= day,
                                    Fare.valid_to >= day,
                                )
                                .order_by(Fare.valid_from.desc())
                            )
                        )
                        fare_override = (
                            (
                                batch.overrides.get((trip.id, start.id, end.id))
                                if batch
                                else self.session.scalar(
                                    select(FareOverride).where(
                                        FareOverride.trip_id == trip.id,
                                        FareOverride.origin_id == start.id,
                                        FareOverride.destination_id == end.id,
                                        FareOverride.active.is_(True),
                                    )
                                )
                            )
                            if trip
                            else None
                        )
                        amount = (
                            fare_override.amount
                            if fare_override
                            else (fare.amount if fare else None)
                        )
                        from .fares import FareEngine

                        quoted = FareEngine(self.session).calculate(
                            service,
                            day,
                            amount,
                            fare_override.dataset_source
                            if fare_override
                            else fare.dataset_source
                            if fare
                            else None,
                            b.distance_km - a.distance_km,
                            bool(fare_override),
                        )
                        amount = quoted["total"]
                        arrival = (
                            base
                            + timedelta(
                                minutes=schedule_offsets.get(
                                    b.id, (b.offset_minutes, b.offset_minutes)
                                )[0]
                            )
                            + (departure - scheduled_departure)
                        )
                        arrival_kind = (
                            "estimated"
                            if departure_kind == "estimated"
                            else "scheduled"
                        )
                        if trip:
                            arrival_observation = (
                                batch.observations.get((trip.id, b.id))
                                if batch
                                else self.session.scalar(
                                    select(TripStopTime)
                                    .where(
                                        TripStopTime.trip_id == trip.id,
                                        TripStopTime.stop_id == b.id,
                                        TripStopTime.active.is_(True),
                                        TripStopTime.verified.is_(True),
                                    )
                                    .order_by(TripStopTime.effective_at.desc())
                                )
                            )
                            if arrival_observation and utc(
                                arrival_observation.effective_at
                            ) <= utc(at) < utc(arrival_observation.expires_at):
                                observed_arrival = (
                                    arrival_observation.actual_arrival
                                    or arrival_observation.estimated_arrival
                                )
                                if observed_arrival is not None:
                                    arrival = utc(observed_arrival).astimezone(zone)
                                    arrival_kind = (
                                        "actual"
                                        if arrival_observation.actual_arrival
                                        else "estimated"
                                    )
                        if arrival < departure:
                            continue
                        results.append(
                            {
                                "service_id": service.id,
                                "trip_id": trip.id if trip else None,
                                "origin_id": a.station_id,
                                "destination_id": b.station_id,
                                "boarding_stop_id": a.id,
                                "alighting_stop_id": b.id,
                                "service_number": service.number,
                                "service_date": day,
                                "departure": departure,
                                "arrival": arrival,
                                "arrival_kind": arrival_kind,
                                "departure_kind": departure_kind,
                                "scheduled_departure": scheduled_departure,
                                "fare": str(amount) if amount is not None else None,
                                "fare_source": quoted.get("source"),
                                "fare_breakdown": quoted,
                                "seat_availability": "unknown",
                                "dataset_source": service.dataset_source,
                            }
                        )
        return sorted(results, key=lambda row: row["departure"])
