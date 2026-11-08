from .route_search import RouteSearch

"""Central typed entry point. Reuses the existing enquiry repository."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from .catalog import Amenity, Vehicle, VehicleType
from .domain import Category, Service
from .enquiry import Enquiry, JourneyQuery
from .links import ServiceVehicle
from .resolver import StationResolver


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ac: bool | None = None
    sleeper: bool | None = None
    electric: bool | None = None
    accessible: bool | None = None
    reservation: bool | None = None
    category: str | None = None
    exclude_categories: list[str] = Field(default_factory=list)
    operator: str | None = None
    amenity: str | None = None
    min_fare: Decimal | None = Field(default=None, ge=0)
    max_fare: Decimal | None = Field(default=None, ge=0)
    max_duration_minutes: int | None = Field(default=None, gt=0)
    after: AwareDatetime | None = None
    before: AwareDatetime | None = None
    arrival_after: AwareDatetime | None = None
    arrival_before: AwareDatetime | None = None

    @model_validator(mode="after")
    def consistent(self):
        if (
            self.min_fare is not None
            and self.max_fare is not None
            and self.min_fare > self.max_fare
        ):
            raise ValueError("Invalid fare window")
        if self.after and self.before and self.after >= self.before:
            raise ValueError("Invalid time window")
        if (
            self.arrival_after
            and self.arrival_before
            and self.arrival_after >= self.arrival_before
        ):
            raise ValueError("Invalid arrival time window")
        return self


class EnquiryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: str
    origin: str | None = None
    destination: str | None = None
    station: str | None = None
    service_id: str | None = None
    trip_id: str | None = None
    service_number: str | None = None
    via: str | None = None
    travel_date: date
    at: AwareDatetime | None = None
    filters: SearchFilters = Field(default_factory=SearchFilters)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    max_transfers: int = Field(default=2, ge=0, le=2)
    minimum_transfer: int = Field(default=15, ge=1, le=180)
    operating_day_start_minutes: int = Field(default=0, ge=0, lt=1440)
    passengers: int = Field(default=1, ge=1, le=100)


class EnquiryResponse(BaseModel):
    intent: str
    status: str
    query: dict
    matched_stations: dict = Field(default_factory=dict)
    results: list = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    pagination: dict = Field(default_factory=dict)


class RTCEnquiryEngine:
    def __init__(self, session):
        self.session = session
        self.enquiry = Enquiry(session)
        self.resolver = StationResolver(session)
        self.vehicle_cache = None
        self.vehicle_type_cache = None

    def enquire(self, request: EnquiryRequest | None = None, **values):
        request = request or EnquiryRequest.model_validate(values)
        from .nlp.taxonomy import IntentRegistry

        definition = IntentRegistry(self.session).get(request.intent)
        if definition:
            if definition.capability == "UNSUPPORTED" or not definition.backend_code:
                return EnquiryResponse(
                    intent=definition.code,
                    status="UNSUPPORTED",
                    query=request.model_dump(mode="json"),
                    warnings=[
                        "Intent recognized; no integrated local enquiry handler is available."
                    ],
                )
            request = request.model_copy(update={"intent": definition.backend_code})
        try:
            result = self._execute(request)
            if definition:
                result = result.model_copy(update={"intent": definition.code})
            return result
        except ValueError as exc:
            return EnquiryResponse(
                intent=request.intent,
                status="INVALID_QUERY",
                query=request.model_dump(mode="json"),
                warnings=[str(exc)],
            )

    def _execute(self, r):
        matched = {}
        for name in ("origin", "destination", "station"):
            value = getattr(r, name)
            if value:
                resolved = self.resolver.resolve(value)
                matched[name] = resolved
                if resolved["status"] not in ("KNOWN", "CITY"):
                    return EnquiryResponse(
                        intent=r.intent,
                        status=resolved["status"],
                        query=r.model_dump(mode="json"),
                        matched_stations=matched,
                    )
        intent = r.intent.upper()
        e = self.enquiry
        at = r.at or datetime.combine(
            r.travel_date,
            time.min,
            ZoneInfo(
                next(iter(matched.values()))["candidates"][0]["timezone"]
                if matched
                else "Asia/Kolkata"
            ),
        )
        if intent in (
            "STATION_FACILITIES",
            "LOST_PROPERTY_CONTACT",
            "STATION_HELPDESK",
        ):
            station = r.station or r.origin
            if not station:
                raise ValueError("Station required")
            if intent == "STATION_FACILITIES":
                rows = e.get_station_facilities(station)
            else:
                from .schema1a import ContactPoint

                ids = [
                    s["id"]
                    for s in matched.get("station", matched.get("origin"))["candidates"]
                ]
                rows = list(
                    self.session.scalars(
                        select(ContactPoint).where(
                            ContactPoint.station_id.in_(ids),
                            ContactPoint.active.is_(True),
                            ContactPoint.contact_type
                            == (
                                "LOST_PROPERTY"
                                if intent == "LOST_PROPERTY_CONTACT"
                                else "HELPDESK"
                            ),
                        )
                    )
                )
        elif intent == "SERVICE_NUMBER_LOOKUP":
            rows = list(
                self.session.scalars(
                    select(Service)
                    .where(Service.number == r.service_number, Service.active.is_(True))
                    .order_by(Service.id)
                    .limit(100)
                )
            )
        elif intent in (
            "ROUTE_STOPS",
            "BOARDING_POINT",
            "ALIGHTING_POINT",
            "INTERMEDIATE_STOP",
        ):
            if not r.service_id:
                raise ValueError("Service ID required")
            rows = e.get_route_stops(r.service_id)
            if intent == "BOARDING_POINT":
                rows = [s for s in rows if s.boarding]
            if intent == "ALIGHTING_POINT":
                rows = [s for s in rows if s.alighting]
            if intent == "INTERMEDIATE_STOP":
                rows = rows[1:-1]
        elif intent == "SEAT_AVAILABILITY":
            rows = [e.get_seat_availability(r.trip_id or "", at, r.passengers)]
        elif intent == "BUS_PLATFORM":
            rows = [
                e.get_platform_assignment(
                    r.trip_id or "", r.station or r.origin or "", at
                )
            ]
        elif intent in ("BUS_LIVE_STATUS", "BUS_CANCELLATION"):
            rows = [e.get_service_status(r.service_id or "", r.travel_date)]
        elif intent in ("BUS_DELAY", "SERVICE_DISRUPTION"):
            from .status import OperationalStatusEngine

            status_engine = OperationalStatusEngine(self.session)
            rows = (
                [status_engine.status(r.trip_id or "", at)]
                if intent == "BUS_DELAY"
                else status_engine.disruptions(r.service_id or "", at)
            )
        elif intent == "CONCESSION_ELIGIBILITY":
            rows = e.get_concessions(r.filters.operator or "", r.travel_date)
        else:
            if "origin" not in matched or "destination" not in matched:
                raise ValueError("Origin and destination required")
            rows = []
            for origin in matched["origin"]["candidates"]:
                for destination in matched["destination"]["candidates"]:
                    if origin["id"] == destination["id"]:
                        raise ValueError("Origin equals destination")
                    category = r.filters.category
                    if category:
                        candidates = list(
                            self.session.scalars(
                                select(Category)
                                .where(
                                    Category.active.is_(True),
                                    (Category.id == category)
                                    | (Category.code == category)
                                    | (Category.name == category),
                                )
                                .limit(2)
                            )
                        )
                        if len(candidates) != 1:
                            raise ValueError("Unknown or ambiguous category")
                        category = candidates[0].id
                    q = JourneyQuery(
                        origin=origin["id"],
                        destination=destination["id"],
                        at=at,
                        category=category,
                        operator=r.filters.operator,
                        amenity=r.filters.amenity,
                        limit=100,
                    )
                    if intent in ("FIRST_BUS", "LAST_BUS"):
                        start = datetime.combine(
                            r.travel_date, time.min, ZoneInfo(origin["timezone"])
                        ) + timedelta(minutes=r.operating_day_start_minutes)
                        found = e._rows(q.model_copy(update={"at": start}))
                    elif intent in ("CONNECTING_BUSES", "ALTERNATIVE_ROUTES"):
                        found = RouteSearch(e).connections(
                            q, r.max_transfers, r.minimum_transfer
                        )
                    elif intent == "BUS_VIA_LOCATION":
                        found = e.get_services_via_stop(q, r.via or "")
                    else:
                        found = e._rows(q)
                    rows.extend(found)
            if r.service_id:
                rows = [x for x in rows if x.get("service_id") == r.service_id]
            rows = self._filter(rows, r, intent)
            if intent == "FIRST_BUS":
                rows = rows[:1]
            elif intent == "LAST_BUS":
                rows = rows[-1:]
            elif intent in ("CHEAPEST_BUS", "FARE_COMPARISON"):
                rows = sorted(
                    [x for x in rows if x.get("fare") is not None],
                    key=lambda x: Decimal(x["fare"]),
                )
            elif intent == "FASTEST_BUS":
                rows.sort(key=lambda x: x["arrival"] - x["departure"])
            elif intent not in {
                "NEXT_BUS",
                "BUSES_BETWEEN",
                "DEPARTURES_AFTER",
                "DEPARTURES_BEFORE",
                "ARRIVAL_TIME",
                "JOURNEY_DURATION",
                "BUSES_OPERATING_TODAY",
                "AVAILABLE_BUS_TYPES",
                "AC_BUS_AVAILABILITY",
                "NON_AC_AVAILABILITY",
                "SLEEPER_BUS_AVAILABILITY",
                "SEATER_BUS_AVAILABILITY",
                "ELECTRIC_BUS_AVAILABILITY",
                "DIRECT_BUS_AVAILABILITY",
                "BUS_AMENITIES",
                "SERVICE_CATEGORY_COMPARISON",
                "RESERVATION_SUPPORTED",
                "TICKET_FARE",
                "CONNECTING_BUSES",
                "ALTERNATIVE_ROUTES",
                "BUS_VIA_LOCATION",
            }:
                raise ValueError("Unsupported intent")
        count = len(rows)
        return EnquiryResponse(
            intent=intent,
            status="KNOWN" if rows else "UNKNOWN",
            query=r.model_dump(mode="json"),
            matched_stations=matched,
            results=jsonable_encoder(rows[r.offset : r.offset + r.limit]),
            pagination={"offset": r.offset, "limit": r.limit, "total": count},
        )

    def _filter(self, rows, r, intent):
        f = r.filters
        result = []
        for row in rows:
            if "legs" in row:
                result.append(row)
                continue
            service = self.session.get(Service, row["service_id"])
            if service.category_id in f.exclude_categories:
                continue
            vehicle = (
                self.vehicle_cache.get(service.id)
                if self.vehicle_cache is not None
                else self.session.scalar(
                    select(Vehicle)
                    .join(ServiceVehicle, ServiceVehicle.vehicle_id == Vehicle.id)
                    .where(
                        ServiceVehicle.service_id == service.id,
                        ServiceVehicle.active.is_(True),
                    )
                )
            )
            kind = (
                (
                    self.vehicle_type_cache.get(vehicle.type_id)
                    if self.vehicle_type_cache is not None
                    else self.session.get(VehicleType, vehicle.type_id)
                )
                if vehicle
                else None
            )
            desired = {
                "ac": True
                if intent == "AC_BUS_AVAILABILITY"
                else False
                if intent == "NON_AC_AVAILABILITY"
                else f.ac,
                "sleeper": True
                if intent == "SLEEPER_BUS_AVAILABILITY"
                else False
                if intent == "SEATER_BUS_AVAILABILITY"
                else f.sleeper,
                "wheelchair": f.accessible,
            }
            if any(
                want is not None and (kind is None or getattr(kind, name) != want)
                for name, want in desired.items()
            ):
                continue
            electric = True if intent == "ELECTRIC_BUS_AVAILABILITY" else f.electric
            if electric is not None and (
                kind is None
                or kind.fuel is None
                or (kind.fuel.upper() == "ELECTRIC") != electric
            ):
                continue
            if (
                f.reservation is not None
                and service.reservation_supported != f.reservation
            ):
                continue
            if f.arrival_after and (
                row.get("arrival") is None or row["arrival"] < f.arrival_after
            ):
                continue
            if f.arrival_before and (
                row.get("arrival") is None or row["arrival"] >= f.arrival_before
            ):
                continue
            if f.after and row["departure"] < f.after:
                continue
            if f.before and row["departure"] >= f.before:
                continue
            if f.min_fare is not None and (
                row["fare"] is None or Decimal(row["fare"]) < f.min_fare
            ):
                continue
            if f.max_fare is not None and (
                row["fare"] is None or Decimal(row["fare"]) > f.max_fare
            ):
                continue
            if (
                f.max_duration_minutes
                and (row["arrival"] - row["departure"]).total_seconds()
                > f.max_duration_minutes * 60
            ):
                continue
            row = dict(row)
            row["fare_details"] = {
                "total": row["fare"],
                "currency": "INR",
                "fare_status": "KNOWN" if row["fare"] is not None else "UNKNOWN",
                "source": row["dataset_source"],
            }
            if intent == "BUS_AMENITIES":
                row["amenities"] = (
                    jsonable_encoder(
                        list(
                            self.session.scalars(
                                select(Amenity).where(
                                    Amenity.vehicle_id == vehicle.id,
                                    Amenity.active.is_(True),
                                )
                            )
                        )
                    )
                    if vehicle
                    else []
                )
            result.append(row)
        return sorted(result, key=lambda x: x.get("departure", x.get("arrival")))
