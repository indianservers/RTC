from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .enquiry import JourneyQuery


class TimetableEngine:
    def __init__(self, enquiry):
        self.enquiry = enquiry

    def operating_day(self, origin, destination, day, cutoff_minutes=0):
        if not 0 <= cutoff_minutes < 1440:
            raise ValueError("Invalid operating-day cutoff")
        station = self.enquiry.repository.resolve_station(origin)
        at = datetime.combine(day, time.min, ZoneInfo(station.timezone)) + timedelta(
            minutes=cutoff_minutes
        )
        return self.enquiry._rows(
            JourneyQuery(origin=origin, destination=destination, at=at)
        )
