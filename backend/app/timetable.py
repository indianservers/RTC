"""Request-scoped bounded timetable prefetch for route planning.

The public repository remains the source of schedule/date semantics. No cache
survives a request, so daily DB changes are visible on the next search.
"""

from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select

from .catalog import Calendar, Variant
from .domain import ExceptionDay, Fare, Stop
from .links import VariantStop
from .operations import Trip
from .records import FareOverride, TripStopTime


class TimetableBatch:
    def __init__(self, session, services, local, days):
        self.stops = defaultdict(list)
        self.calendars = defaultdict(list)
        self.fares = defaultdict(list)
        self.exceptions = {}
        self.trips = {}
        self.overrides = {}
        self.observations = {}
        self.variants = {}
        self.variant_stops = defaultdict(set)
        ids = [s.id for s in services]
        routes = {s.route_id for s in services}
        if not ids:
            return

        def rows(query):
            found = list(session.scalars(query.limit(20001)))
            if len(found) > 20000:
                raise ValueError(
                    "Timetable row resource limit exceeded; narrow the search"
                )
            return found

        for stop in rows(
            select(Stop)
            .where(Stop.route_id.in_(routes), Stop.active.is_(True))
            .order_by(Stop.sequence)
        ):
            self.stops[stop.route_id].append(stop)
        variant_ids = {s.route_variant_id for s in services if s.route_variant_id}
        if variant_ids:
            self.variants = {
                v.id: v
                for v in rows(
                    select(Variant).where(
                        Variant.id.in_(variant_ids), Variant.active.is_(True)
                    )
                )
            }
            for membership in rows(
                select(VariantStop).where(
                    VariantStop.variant_id.in_(variant_ids),
                    VariantStop.active.is_(True),
                )
            ):
                self.variant_stops[membership.variant_id].add(membership.stop_id)
        lookback = (
            max(
                (s.offset_minutes for stops in self.stops.values() for s in stops),
                default=0,
            )
            // 1440
            + 1
        )
        if lookback > 7:
            raise ValueError("Timetable offset exceeds supported seven-day lookback")
        start, end = (
            local.date() - timedelta(days=lookback),
            local.date() + timedelta(days=days),
        )
        for exception in rows(
            select(ExceptionDay).where(
                ExceptionDay.service_id.in_(ids),
                ExceptionDay.service_date.between(start, end),
                ExceptionDay.active.is_(True),
            )
        ):
            self.exceptions[exception.service_id, exception.service_date] = exception
        for cal in rows(
            select(Calendar)
            .where(
                Calendar.service_id.in_(ids),
                Calendar.active.is_(True),
                Calendar.valid_from <= end,
                Calendar.valid_to >= start,
            )
            .order_by(Calendar.valid_from.desc(), Calendar.id)
        ):
            self.calendars[cal.service_id].append(cal)
        for trip in rows(
            select(Trip).where(
                Trip.service_id.in_(ids),
                Trip.active.is_(True),
                Trip.service_date.between(start, end),
            )
        ):
            self.trips[trip.service_id, trip.service_date] = trip
        for fare in rows(
            select(Fare)
            .where(
                Fare.service_id.in_(ids),
                Fare.active.is_(True),
                Fare.valid_from <= end,
                Fare.valid_to >= start,
            )
            .order_by(Fare.valid_from.desc(), Fare.id)
        ):
            self.fares[fare.service_id, fare.origin_id, fare.destination_id].append(
                fare
            )
        trip_ids = [t.id for t in self.trips.values()]
        if trip_ids:
            for fare in rows(
                select(FareOverride).where(
                    FareOverride.trip_id.in_(trip_ids), FareOverride.active.is_(True)
                )
            ):
                self.overrides[fare.trip_id, fare.origin_id, fare.destination_id] = fare
            for obs in rows(
                select(TripStopTime)
                .where(
                    TripStopTime.trip_id.in_(trip_ids),
                    TripStopTime.active.is_(True),
                    TripStopTime.verified.is_(True),
                    TripStopTime.effective_at <= local,
                    TripStopTime.expires_at > local,
                )
                .order_by(TripStopTime.effective_at.desc(), TripStopTime.id)
            ):
                self.observations.setdefault((obs.trip_id, obs.stop_id), obs)

    def calendar(self, service_id, day):
        return next(
            (
                c
                for c in self.calendars[service_id]
                if c.valid_from <= day <= c.valid_to
            ),
            None,
        )

    def fare(self, service_id, origin, destination, day):
        return next(
            (
                f
                for f in self.fares[service_id, origin, destination]
                if f.valid_from <= day <= f.valid_to
            ),
            None,
        )


class TimetableEngine:
    """Existing operating-day API retained alongside request-scoped batch reads."""

    def __init__(self, enquiry):
        self.enquiry = enquiry

    def operating_day(self, origin, destination, day, cutoff_minutes=0):
        from datetime import datetime, time
        from zoneinfo import ZoneInfo

        from .enquiry import JourneyQuery

        if not 0 <= cutoff_minutes < 1440:
            raise ValueError("Invalid operating-day cutoff")
        station = self.enquiry.repository.resolve_station(origin)
        at = datetime.combine(day, time.min, ZoneInfo(station.timezone)) + timedelta(
            minutes=cutoff_minutes
        )
        return self.enquiry._rows(
            JourneyQuery(origin=origin, destination=destination, at=at)
        )
