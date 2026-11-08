from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .domain import (
    Category,
    Fare,
    Operator,
    Route,
    Service,
    Station,
    Stop,
    database,
)


def seed(engine):
    with Session(engine) as s, s.begin():
        if s.scalar(select(Operator).where(Operator.code == "DEMO")):
            return
        op = Operator(code="DEMO", name="FICTIONAL demonstration operator")
        s.add(op)
        s.flush()
        category = Category(operator_id=op.id, name="Demo seater")
        s.add(category)
        stations = [
            Station(code=f"DEMO{i}", name=name)
            for i, name in enumerate(
                [
                    "Vijayawada",
                    "Guntur",
                    "Tirupati",
                    "Tirumala",
                    "Nellore",
                    "Ongole",
                    "Kavali",
                    "Rajahmundry",
                    "Visakhapatnam",
                    "Kakinada",
                    "Kurnool",
                    "Kadapa",
                    "Anantapur",
                    "Eluru",
                    "Srikakulam",
                    "Vizianagaram",
                    "Machilipatnam",
                    "Bhimavaram",
                    "Srisailam",
                    "Annavaram",
                    "Hyderabad",
                ]
            )
        ]
        s.add_all(stations)
        s.flush()
        for i in range(100):
            route = Route(code=f"DEMO{i}")
            s.add(route)
            s.flush()
            origin, destination = stations[i % 21], stations[(i + 1) % 21]
            s.add_all(
                [
                    Stop(
                        route_id=route.id,
                        station_id=origin.id,
                        sequence=0,
                        offset_minutes=0,
                        distance_km=0,
                    ),
                    Stop(
                        route_id=route.id,
                        station_id=destination.id,
                        sequence=1,
                        offset_minutes=180,
                        distance_km=150,
                    ),
                ]
            )
            service = Service(
                operator_id=op.id,
                category_id=category.id,
                route_id=route.id,
                number=f"DEMO{i}",
                departure_minutes=(i * 37) % 1440,
                valid_from=date(2026, 1, 1),
                valid_to=date(2027, 12, 31),
            )
            s.add(service)
            s.flush()
            s.add(
                Fare(
                    service_id=service.id,
                    origin_id=origin.id,
                    destination_id=destination.id,
                    amount=Decimal("100.00"),
                    valid_from=date(2026, 1, 1),
                    valid_to=date(2027, 12, 31),
                )
            )


if __name__ == "__main__":
    seed(database())
