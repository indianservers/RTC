from datetime import timedelta

from sqlalchemy import select

from .availability import utc
from .operations import Trip
from .records import DelayEvent, Disruption, Location


class OperationalStatusEngine:
    def __init__(self, session):
        self.session = session

    def status(self, trip_id, at, gps_freshness_seconds=300, station_id=None):
        if station_id:
            from .domain import Repository

            station_id = Repository(self.session).resolve_station(station_id).id
        trip = self.session.get(Trip, trip_id)
        if not trip:
            return {"status": "UNKNOWN", "gps_status": "UNKNOWN"}
        gps = self.session.scalar(
            select(Location)
            .where(
                Location.trip_id == trip_id,
                Location.verified.is_(True),
                Location.active.is_(True),
            )
            .order_by(Location.effective_at.desc())
        )
        gps_status = "UNKNOWN"
        if gps and utc(gps.effective_at) <= utc(at):
            gps_status = (
                "KNOWN"
                if utc(at) - utc(gps.effective_at)
                <= timedelta(seconds=gps_freshness_seconds)
                and utc(at) < utc(gps.expires_at)
                else "STALE"
            )
        delay = self.session.scalar(
            select(DelayEvent)
            .where(
                DelayEvent.trip_id == trip_id,
                DelayEvent.verified.is_(True),
                DelayEvent.active.is_(True),
                DelayEvent.station_id == station_id if station_id else True,
            )
            .order_by(DelayEvent.effective_at.desc())
        )
        delay_known = delay and utc(delay.effective_at) <= utc(at) < utc(
            delay.expires_at
        )
        from .domain import Stop
        from .records import TripStopTime

        observations = select(TripStopTime).where(
            TripStopTime.trip_id == trip_id,
            TripStopTime.active.is_(True),
            TripStopTime.verified.is_(True),
            TripStopTime.effective_at <= at,
        )
        if station_id:
            observations = observations.join(Stop).where(Stop.station_id == station_id)
        obs = self.session.scalar(
            observations.order_by(
                TripStopTime.effective_at.desc(), TripStopTime.recorded_at.desc()
            )
        )
        fresh = obs and utc(obs.expires_at) > utc(at)
        result = {
            "status": trip.status.upper()
            if trip.status != "scheduled"
            else "SCHEDULED_ONLY",
            "gps_status": gps_status,
            "delay_minutes": delay.delay_minutes if delay_known else None,
            "delay_status": "KNOWN"
            if delay_known
            else "STALE"
            if delay and utc(delay.effective_at) <= utc(at)
            else "UNKNOWN",
            "last_verified_at": utc(gps.effective_at) if gps else None,
            "dataset_source": trip.dataset_source,
        }
        if trip.operational_state:
            result["lifecycle"] = trip.operational_state.get("lifecycle", "ACTIVE")
            result["phase"] = trip.operational_state.get("phase", "SCHEDULED")
        if obs:
            result.update(
                estimated_arrival=obs.estimated_arrival if fresh else None,
                estimated_departure=obs.estimated_departure if fresh else None,
                actual_arrival=obs.actual_arrival,
                actual_departure=obs.actual_departure,
                verified_at=obs.effective_at,
                freshness="KNOWN" if fresh else "STALE",
                source_id=obs.source_id,
            )
        if station_id:
            from .enquiry import Enquiry

            result["platform"] = Enquiry(self.session).get_platform_assignment(
                trip_id, station_id, at
            )
        return result

    def disruptions(self, service_id, at):
        rows = self.session.scalars(
            select(Disruption)
            .where(
                Disruption.service_id == service_id,
                Disruption.verified.is_(True),
                Disruption.active.is_(True),
            )
            .order_by(Disruption.effective_at.desc())
            .limit(100)
        )
        return [r for r in rows if utc(r.effective_at) <= utc(at) < utc(r.expires_at)]
