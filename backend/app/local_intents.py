"""Additional enquiries using existing local tables; no inferred policy or live facts."""

import itertools
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from .availability import utc
from .catalog import Layout, Vehicle
from .domain import Category, Operator, Service, Station, Stop
from .enquiry import JourneyQuery
from .links import ServiceVehicle
from .operations import PlatformAssignment, StationBay, Trip
from .records import Inventory, ReservationChannel, RouteDistance, TripStopTime
from .schema1a import ContactPoint

LOCAL_INTENTS = frozenset(
    [
        "BUS_AT_TIME",
        "SERVICE_FREQUENCY",
        "SPECIAL_DAY_SCHEDULE",
        "ACCESSIBLE_BUS_AVAILABILITY",
        "BUS_CAPACITY",
        "ROUTE_DISTANCE",
        "DESTINATION_REACHABILITY",
        "BOOKING_OPTIONS",
        "ESTIMATED_ARRIVAL",
        "BUS_DEPARTED_STATUS",
        "BUS_ARRIVED_STATUS",
        "PLATFORM_CHANGE",
        "OPERATOR_CONTACT",
        "STATION_NAVIGATION",
        "COMPLAINT_GUIDANCE",
    ]
)
TRIP_LOCAL = {
    "BUS_CAPACITY",
    "ESTIMATED_ARRIVAL",
    "BUS_DEPARTED_STATUS",
    "BUS_ARRIVED_STATUS",
    "PLATFORM_CHANGE",
}
OPERATOR_LOCAL = {"BOOKING_OPTIONS", "OPERATOR_CONTACT"}
STATION_LOCAL = {"STATION_NAVIGATION", "COMPLAINT_GUIDANCE"}


def enrich_definition(spec):
    if spec["code"] in LOCAL_INTENTS:
        return dict(
            spec,
            capability="PARTIAL",
            backend_code=spec["code"],
            limitation="Local records only; unknown data is never inferred. No policy, authorization or external live integration.",
        )
    return spec


class LocalEnquiries:
    def __init__(self, engine):
        self.engine, self.session = engine, engine.session

    def execute(self, r, matched, at):
        from .engine import EnquiryResponse

        rows, warnings = self.rows(r, matched, at)
        return EnquiryResponse(
            intent=r.intent,
            status="KNOWN" if rows else "UNKNOWN",
            query=r.model_dump(mode="json"),
            matched_stations=matched,
            results=jsonable_encoder(rows[r.offset : r.offset + r.limit]),
            warnings=warnings,
            pagination={"total": len(rows), "limit": r.limit, "offset": r.offset},
        )

    def station(self, value):
        result = self.engine.resolver.resolve(value or "")
        if result["status"] != "KNOWN":
            raise ValueError("Choose one station using its station code")
        return result["candidates"][0]["id"]

    def trip(self, r):
        row = (
            self.session.get(Trip, r.trip_id)
            if r.trip_id
            else self.session.scalar(
                select(Trip).where(
                    Trip.service_id == (r.service_id or ""),
                    Trip.service_date == r.travel_date,
                    Trip.active.is_(True),
                )
            )
        )
        if row and (
            not row.active
            or row.service_date != r.travel_date
            or r.service_id
            and row.service_id != r.service_id
        ):
            raise ValueError("Trip does not match selected service/date")
        if row:
            service = self.session.get(Service, row.service_id)
            if not service or not service.active:
                raise ValueError("The selected service is inactive or unknown")
        return row

    def operator(self, r):
        value = r.filters.operator
        if not value and r.service_id:
            service = self.session.get(Service, r.service_id)
            value = service.operator_id if service and service.active else None
        row = (
            self.session.scalar(
                select(Operator).where(
                    (Operator.id == value) | (Operator.code == value),
                    Operator.active.is_(True),
                )
            )
            if value
            else None
        )
        if not row:
            raise ValueError("Which RTC operator do you mean?")
        return row

    def journey_query(self, r, at):
        category = r.filters.category
        if category:
            matches = list(
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
            if len(matches) != 1:
                raise ValueError("Unknown or ambiguous category")
            category = matches[0].id
        return JourneyQuery(
            origin=r.origin,
            destination=r.destination,
            at=at,
            operator=r.filters.operator,
            category=category,
            amenity=r.filters.amenity,
            limit=100,
        )

    def rows(self, r, matched, at):
        intent = r.intent
        if intent in OPERATOR_LOCAL:
            op = self.operator(r)
            if intent == "BOOKING_OPTIONS":
                return [
                    {
                        "name": c.name,
                        "instructions": c.instructions,
                        "dataset_source": c.dataset_source,
                        "operator_id": op.id,
                    }
                    for c in self.session.scalars(
                        select(ReservationChannel)
                        .where(
                            ReservationChannel.operator_id == op.id,
                            ReservationChannel.active.is_(True),
                        )
                        .order_by(ReservationChannel.id)
                    )
                ], []
            return (
                [
                    {
                        "operator": op.name,
                        "website": op.website,
                        "dataset_source": op.dataset_source,
                    }
                ]
                if op.website
                else []
            ), [
                "Only the recorded operator website is available; no phone or contact availability is inferred."
            ]
        if intent in STATION_LOCAL:
            sid = self.station(r.station or r.origin)
            if intent == "COMPLAINT_GUIDANCE":
                return [
                    {
                        "label": c.label,
                        "contact_value": c.contact_value,
                        "opening_hours": c.opening_hours,
                        "last_verified_at": c.last_verified_at,
                        "dataset_source": c.dataset_source,
                    }
                    for c in self.session.scalars(
                        select(ContactPoint)
                        .where(
                            ContactPoint.station_id == sid,
                            ContactPoint.contact_type == "COMPLAINT",
                            ContactPoint.active.is_(True),
                        )
                        .order_by(ContactPoint.id)
                    )
                ], [
                    "Recorded complaint contacts only; opening hours and freshness are not live-verified."
                ]
            station = self.session.get(Station, sid)
            rows = (
                [
                    {
                        "station_name": station.name,
                        "address": station.address,
                        "dataset_source": station.dataset_source,
                    }
                ]
                if station.address
                else []
            )
            rows += [
                {
                    "bay": b.code,
                    "name": b.bay_name,
                    "zone": b.floor_or_zone,
                    "dataset_source": b.dataset_source,
                }
                for b in self.session.scalars(
                    select(StationBay)
                    .where(
                        StationBay.station_id == sid,
                        StationBay.active.is_(True),
                        StationBay.floor_or_zone.is_not(None),
                    )
                    .order_by(StationBay.code)
                )
            ]
            return rows, [
                "Recorded addresses and bay zones only; no indoor route is inferred."
            ]
        if intent in TRIP_LOCAL:
            trip = self.trip(r)
            if intent == "BUS_CAPACITY":
                if trip:
                    inventory = self.session.scalar(
                        select(Inventory).where(
                            Inventory.trip_id == trip.id, Inventory.active.is_(True)
                        )
                    )
                    if inventory and inventory.capacity is not None:
                        return [
                            {
                                "capacity": inventory.capacity,
                                "source": "trip_inventory",
                                "dataset_source": inventory.dataset_source,
                            }
                        ], ["Capacity is not seat availability."]
                vehicle = (
                    self.session.get(Vehicle, trip.vehicle_id)
                    if trip and trip.vehicle_id
                    else self.session.scalar(
                        select(Vehicle)
                        .join(ServiceVehicle, ServiceVehicle.vehicle_id == Vehicle.id)
                        .where(
                            ServiceVehicle.service_id == r.service_id,
                            ServiceVehicle.active.is_(True),
                            Vehicle.active.is_(True),
                        )
                    )
                )
                layout = (
                    self.session.get(Layout, vehicle.layout_id)
                    if vehicle and vehicle.active
                    else None
                )
                return (
                    [
                        {
                            "seating_capacity": layout.seating_capacity,
                            "berth_capacity": layout.berth_capacity,
                            "source": "assigned_vehicle_layout",
                            "dataset_source": layout.dataset_source,
                        }
                    ]
                    if layout and layout.active
                    else []
                ), ["Capacity is not seat availability."]
            if not trip:
                return [], [
                    "No dated trip record; scheduled times do not establish operational facts."
                ]
            if intent == "PLATFORM_CHANGE":
                sid = self.station(r.station or r.origin)
                records = list(
                    self.session.scalars(
                        select(PlatformAssignment)
                        .join(StationBay, StationBay.id == PlatformAssignment.bay_id)
                        .where(
                            PlatformAssignment.trip_id == trip.id,
                            StationBay.station_id == sid,
                            StationBay.active.is_(True),
                            PlatformAssignment.active.is_(True),
                            PlatformAssignment.verified.is_(True),
                            PlatformAssignment.effective_at <= at,
                            PlatformAssignment.recorded_at <= at,
                        )
                        .order_by(
                            PlatformAssignment.effective_at.desc(),
                            PlatformAssignment.id.desc(),
                        )
                    )
                )
                if len(records) < 2 or utc(records[0].expires_at) <= utc(at):
                    return [], [
                        "A current assignment and earlier assignment are both required to establish a change."
                    ]
                current = records[0]
                previous = next(
                    (
                        x
                        for x in records[1:]
                        if utc(x.effective_at) < utc(current.effective_at)
                    ),
                    None,
                )
                if not previous:
                    return [], [
                        "Assignment history has no distinct earlier effective time."
                    ]
                return [
                    {
                        "changed": current.bay_id != previous.bay_id,
                        "previous_bay": self.session.get(
                            StationBay, previous.bay_id
                        ).code,
                        "current_bay": self.session.get(
                            StationBay, current.bay_id
                        ).code,
                        "effective_at": current.effective_at,
                        "previous_source": previous.dataset_source,
                        "dataset_source": current.dataset_source,
                        "source_id": current.source_id,
                        "expires_at": current.expires_at,
                    }
                ], []
            sid = self.station(r.station or r.origin or r.destination)
            service = self.session.get(Service, trip.service_id)
            stops = list(
                self.session.scalars(
                    select(Stop).where(
                        Stop.route_id == service.route_id,
                        Stop.station_id == sid,
                        Stop.active.is_(True),
                    )
                )
            )
            if len(stops) != 1:
                raise ValueError("Select a unique station stop on the service route")
            obs = self.session.scalar(
                select(TripStopTime)
                .where(
                    TripStopTime.trip_id == trip.id,
                    TripStopTime.stop_id == stops[0].id,
                    TripStopTime.active.is_(True),
                    TripStopTime.verified.is_(True),
                    TripStopTime.effective_at <= at,
                    TripStopTime.recorded_at <= at,
                    TripStopTime.expires_at > at,
                )
                .order_by(TripStopTime.effective_at.desc(), TripStopTime.id.desc())
            )
            field = {
                "ESTIMATED_ARRIVAL": "estimated_arrival",
                "BUS_DEPARTED_STATUS": "actual_departure",
                "BUS_ARRIVED_STATUS": "actual_arrival",
            }[intent]
            value = getattr(obs, field) if obs else None
            if not value or intent != "ESTIMATED_ARRIVAL" and utc(value) > utc(at):
                return [], [
                    "No fresh verified stop observation supports this answer; absence is not a negative status."
                ]
            if intent == "ESTIMATED_ARRIVAL" and utc(value) < utc(at):
                return [], ["The recorded arrival estimate is in the past."]
            value = utc(value).astimezone(
                ZoneInfo(self.session.get(Station, sid).timezone)
            )
            return [
                dict(
                    station_id=sid,
                    **{field: value},
                    source_id=obs.source_id,
                    dataset_source=obs.dataset_source,
                    effective_at=obs.effective_at,
                    expires_at=obs.expires_at,
                )
            ], []
        if intent == "ROUTE_DISTANCE":
            if not r.service_id:
                raise ValueError("Select a service to identify its route")
            service = self.engine.enquiry.get_service_details(r.service_id)
            origin, dest = self.station(r.origin), self.station(r.destination)
            stops = list(
                self.session.scalars(
                    select(Stop)
                    .where(Stop.route_id == service.route_id, Stop.active.is_(True))
                    .order_by(Stop.sequence)
                )
            )
            starts, ends = (
                [s for s in stops if s.station_id == origin],
                [s for s in stops if s.station_id == dest],
            )
            if (
                len(starts) != 1
                or len(ends) != 1
                or starts[0].sequence >= ends[0].sequence
            ):
                raise ValueError("Select a forward segment with unique route stops")
            a, b = starts[0], ends[0]
            if service.route_variant_id:
                from .catalog import Variant
                from .links import VariantStop

                variant = self.session.get(Variant, service.route_variant_id)
                members = set(
                    self.session.scalars(
                        select(VariantStop.stop_id).where(
                            VariantStop.variant_id == service.route_variant_id,
                            VariantStop.active.is_(True),
                        )
                    )
                )
                if (
                    not variant
                    or not variant.active
                    or a.id not in members
                    or b.id not in members
                ):
                    raise ValueError(
                        "The selected segment is not in the active service route variant"
                    )
            distances = list(
                self.session.scalars(
                    select(RouteDistance).where(
                        RouteDistance.origin_stop_id == a.id,
                        RouteDistance.destination_stop_id == b.id,
                        RouteDistance.active.is_(True),
                    )
                )
            )
            if len(distances) > 1:
                return [], ["Conflicting segment distance records require review."]
            if distances:
                amount, source = distances[0].distance_km, distances[0].dataset_source
            else:
                amount, source = (
                    Decimal(b.distance_km) - Decimal(a.distance_km),
                    "DEMO"
                    if any(x.dataset_source in ("DEMO", "SYNTHETIC") for x in (a, b))
                    else service.dataset_source,
                )
            if amount < 0:
                return [], ["Recorded cumulative distances are inconsistent."]
            return [
                {
                    "distance_km": str(amount),
                    "dataset_source": source,
                    "service_id": service.id,
                }
            ], []
        if not r.origin or not r.destination:
            raise ValueError("Origin and destination required")
        if intent == "BUS_AT_TIME":
            if r.at is None:
                raise ValueError("Specify the departure time to search around")
            start = at - timedelta(minutes=15)
            end = at + timedelta(minutes=15)
            q = self.journey_query(r, start)
            rows = self.engine.enquiry._rows(q)
            rows = [x for x in rows if start <= x["departure"] < end]
            return self.engine._filter(rows, r, intent), [
                "Departure proximity window: 15 minutes before (inclusive) to 15 minutes after (exclusive) the specified time."
            ]
        if intent == "DESTINATION_REACHABILITY":
            from .journey import JourneyConstraints, JourneyPlanner

            planned = JourneyPlanner(self.session).search(
                JourneyConstraints(
                    origin=r.origin,
                    destination=r.destination,
                    earliest_departure=at,
                    horizon_hours=24,
                    max_transfers=r.max_transfers,
                    minimum_transfer_minutes=r.minimum_transfer,
                    filters=r.filters,
                    passengers=r.passengers,
                    limit=100,
                )
            )
            rows = []
            for itinerary in planned.itineraries:
                row = itinerary.model_dump(mode="json")
                row.update(
                    departure=row["departure_at"],
                    arrival=row["arrival_at"],
                    dataset_source="DEMO"
                    if any(x in ("DEMO", "SYNTHETIC") for x in itinerary.sources)
                    else "MIXED",
                )
                for leg in row["legs"]:
                    service = self.session.get(Service, leg["service_id"])
                    leg["service_number"] = (
                        service.number if service else leg["service_id"]
                    )
                rows.append(row)
            return rows, list(planned.warnings) + [
                "Results are bounded to the next 24 hours and configured transfer/resource limits. No result does not prove the destination is unreachable."
            ]
        station = self.engine.enquiry.repository.resolve_station(r.origin)
        start = datetime.combine(r.travel_date, time.min, ZoneInfo(station.timezone))
        end = start + timedelta(days=1)
        q = self.journey_query(r, start)
        rows = self.engine._filter(
            [x for x in self.engine.enquiry._rows(q) if start <= x["departure"] < end],
            r,
            intent,
        )
        if intent == "ACCESSIBLE_BUS_AVAILABILITY":
            return rows, [
                "Only explicitly wheelchair-accessible assigned vehicle types match."
            ]
        if intent == "SERVICE_FREQUENCY":
            times = sorted({x["departure"] for x in rows})
            gaps = [
                int((b - a).total_seconds() / 60) for a, b in itertools.pairwise(times)
            ]
            sources = sorted({x["dataset_source"] for x in rows})
            return (
                [
                    {
                        "count": len(rows),
                        "distinct_departure_count": len(times),
                        "gap_minutes": gaps,
                        "dataset_source": "DEMO"
                        if sources and any(s in ("DEMO", "SYNTHETIC") for s in sources)
                        else "MIXED",
                        "sources": sources,
                        "window_start": start,
                        "window_end": end,
                    }
                ]
                if rows
                else []
            ), [
                "Computed from recorded departures on this date; gaps are not a promised recurring headway."
            ]
        # SPECIAL_DAY_SCHEDULE uses the repository's calendar/exception semantics.
        return rows, [
            "Recorded timetable for the requested date, including local calendar exceptions; no official festival schedule is inferred."
        ]
