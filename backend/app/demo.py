"""Enrich demo records without modifying or replacing existing identifiers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .catalog import Intent
from .domain import Alias, Category, Operator, Station, database


def enrich(engine):
    with Session(engine) as s, s.begin():
        for station_name, names in {
            "Vijayawada": ["Bezawada", "విజయవాడ", "బెజవాడ"],
            "Visakhapatnam": ["Vizag", "విశాఖపట్నం", "వైజాగ్"],
            "Tirupati": ["Tirupathi", "తిరుపతి"],
            "Tirumala": ["తిరుమల"],
        }.items():
            station = s.scalar(select(Station).where(Station.name == station_name))
            if station:
                for name in names:
                    if not s.scalar(select(Alias).where(Alias.name == name)):
                        s.add(Alias(station_id=station.id, name=name))
        op = s.scalar(select(Operator).where(Operator.code == "DEMO"))
        if op:
            for name in ["Demo sleeper", "Demo electric", "Demo express"]:
                if not s.scalar(
                    select(Category).where(
                        Category.operator_id == op.id, Category.name == name
                    )
                ):
                    s.add(Category(operator_id=op.id, name=name))
        codes = [
            "NEXT_BUS",
            "FIRST_BUS",
            "LAST_BUS",
            "GET_FARE",
            "GET_BUS_TYPES",
            "BUS_AVAILABILITY",
            "GET_PLATFORM",
            "GET_ROUTE",
            "GET_STOPS",
            "GET_DURATION",
            "GET_ARRIVAL",
            "GET_DELAY",
            "GET_CANCELLATION",
            "GET_SEAT_AVAILABILITY",
            "GET_CHEAPEST_SERVICE",
            "GET_FASTEST_SERVICE",
            "GET_CONNECTING_BUSES",
            "GET_CONCESSIONS",
            "GET_STATION_FACILITIES",
            "GET_LUGGAGE_RULES",
            "GET_BOOKING_OPTIONS",
            "GET_OPERATORS",
            "GET_DEPOTS",
            "GET_STATIONS",
            "GET_SERVICE_DETAILS",
            "GET_VIA_SERVICES",
            "GET_ACCESSIBILITY",
            "GET_AC",
            "GET_SLEEPER",
            "GET_CHARGING",
            "GET_TRACKING",
            "GET_CALENDAR",
            "GET_SERVICE_DATE",
            "GET_RETURN_ROUTE",
            "GET_DISTANCE",
            "GET_FARE_CLASSES",
            "GET_RESERVATION_CHANNELS",
            "GET_ALERTS",
            "GET_SOURCE",
            "GET_FRESHNESS",
            "GET_LANGUAGE",
            "GET_HELP",
        ]
        for code in codes:
            if not s.scalar(select(Intent).where(Intent.code == code)):
                s.add(Intent(code=code, description=code.replace("_", " ").lower()))


if __name__ == "__main__":
    enrich(database())
