import itertools
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from .domain import Stop


class RouteSearch:
    def __init__(self, enquiry):
        self.enquiry = enquiry

    def connections(self, q, max_transfers=2, minimum_transfer=15, max_expansions=500):
        if not 0 <= max_transfers <= 2 or not 1 <= minimum_transfer <= 180:
            raise ValueError("Invalid connection bounds")
        e = self.enquiry
        target = e.repository.resolve_station(q.destination).id
        origin = e.repository.resolve_station(q.origin).id
        end = q.at + timedelta(days=q.days)
        stations = list(
            e.session.scalars(
                select(Stop.station_id)
                .where(Stop.active.is_(True))
                .distinct()
                .order_by(Stop.station_id)
                .limit(100)
            )
        )
        frontier = [(origin, q.at, [], (origin,))]
        results = []
        expansions = 0
        seen = set()
        while frontier and expansions < max_expansions:
            current, after, legs, visited = frontier.pop(0)
            for station in stations:
                if station in visited:
                    continue
                candidates = e._rows(
                    q.model_copy(
                        update={"origin": current, "destination": station, "at": after}
                    )
                )[:20]
                for leg in candidates:
                    expansions += 1
                    if expansions > max_expansions:
                        break
                    if leg["arrival"] > end or any(
                        x["service_id"] == leg["service_id"] for x in legs
                    ):
                        continue
                    path = legs + [leg]
                    if station == target:
                        key = tuple(
                            (x["service_id"], x["service_date"], x["departure"])
                            for x in path
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        waiting = sum(
                            (b["departure"] - a["arrival"]).total_seconds() / 60
                            for a, b in itertools.pairwise(path)
                        )
                        results.append(
                            {
                                "legs": path,
                                "transfer_stations": list(visited[1:]),
                                "departure": path[0]["departure"],
                                "arrival": leg["arrival"],
                                "waiting_minutes": waiting,
                                "total_minutes": (
                                    leg["arrival"] - path[0]["departure"]
                                ).total_seconds()
                                / 60,
                                "fare": str(sum(Decimal(x["fare"]) for x in path))
                                if all(x["fare"] is not None for x in path)
                                else None,
                            }
                        )
                    elif len(path) <= max_transfers:
                        frontier.append(
                            (
                                station,
                                leg["arrival"] + timedelta(minutes=minimum_transfer),
                                path,
                                visited + (station,),
                            )
                        )
                if expansions >= max_expansions:
                    break
        return sorted(results, key=lambda x: x["arrival"])
