import itertools
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from .domain import Stop


class RouteSearch:
    def __init__(self, enquiry):
        self.enquiry = enquiry

    def timed_paths(
        self,
        q,
        *,
        max_transfers=2,
        minimum_transfer=15,
        maximum_wait=180,
        maximum_total_wait=360,
        horizon_hours=48,
        max_expansions=5000,
        max_stations=100,
        max_services_per_segment=1000,
        leg_filter=None,
        latest_departure=None,
        arrival_deadline=None,
        excluded_trips=(),
        excluded_services=(),
    ):
        """Bounded timetable label enumeration over reachable physical stations.

        Cache outgoing segments within this request only. Different path histories
        are retained: cheapest, shortest and fewest-transfer labels can differ.
        Caps are observable rather than silently interpreted as an exhaustive search.
        """
        from sqlalchemy.orm import aliased

        from .domain import Service

        if not 0 <= max_transfers <= 2 or not 1 <= minimum_transfer <= 180:
            raise ValueError("Invalid connection bounds")
        e = self.enquiry
        origin = e.repository.resolve_station(q.origin).id
        target = e.repository.resolve_station(q.destination).id
        if origin == target:
            raise ValueError("Origin equals destination")
        end = q.at + timedelta(hours=horizon_hours)
        cache = {}
        self.stats = {"expanded": 0, "candidate_connections": 0, "truncated": False}

        def outgoing(station):
            if station in cache:
                return cache[station]
            boarding, alighting = aliased(Stop), aliased(Stop)
            destinations = list(
                e.session.scalars(
                    select(alighting.station_id)
                    .join(boarding, boarding.route_id == alighting.route_id)
                    .join(Service, Service.route_id == boarding.route_id)
                    .where(
                        boarding.station_id == station,
                        boarding.active.is_(True),
                        boarding.boarding.is_(True),
                        alighting.active.is_(True),
                        alighting.alighting.is_(True),
                        alighting.sequence > boarding.sequence,
                        Service.active.is_(True),
                    )
                    .distinct()
                    .order_by(alighting.station_id)
                    .limit(max_stations + 1)
                )
            )
            if len(destinations) > max_stations:
                self.stats["truncated"] = True
            segments = []
            for destination in destinations[:max_stations]:
                rows = e.repository.journeys(
                    station,
                    destination,
                    q.at,
                    days=(horizon_hours + 23) // 24,
                    category=q.category,
                    amenity=q.amenity,
                    service_limit=max_services_per_segment,
                )
                for row in rows:
                    if (
                        row["service_id"] in excluded_services
                        or row.get("trip_id") in excluded_trips
                    ):
                        continue
                    if row["arrival"] > end or row["arrival"] < row["departure"]:
                        continue
                    if leg_filter is None or leg_filter(row):
                        segments.append(row)
            segments.sort(
                key=lambda r: (
                    r["departure"],
                    r["arrival"],
                    r["service_id"],
                    r["destination_id"],
                )
            )
            cache[station] = segments
            return segments

        frontier = [(origin, q.at, [], (origin,), 0.0)]
        results, seen = [], set()
        while frontier:
            current, earliest, legs, visited, total_wait = frontier.pop()
            for leg in outgoing(current):
                self.stats["candidate_connections"] += 1
                if self.stats["candidate_connections"] > max_expansions:
                    self.stats["truncated"] = True
                    return results
                if leg["departure"] < earliest or leg["destination_id"] in visited:
                    continue
                if (
                    not legs
                    and latest_departure
                    and leg["departure"] > latest_departure
                ):
                    continue
                if arrival_deadline and leg["arrival"] > arrival_deadline:
                    continue
                if any(
                    x["service_id"] == leg["service_id"]
                    and x["service_date"] == leg["service_date"]
                    for x in legs
                ):
                    continue
                wait = (
                    (leg["departure"] - legs[-1]["arrival"]).total_seconds() / 60
                    if legs
                    else 0
                )
                if legs and (
                    wait > maximum_wait or total_wait + wait > maximum_total_wait
                ):
                    continue
                self.stats["expanded"] += 1
                path = legs + [leg]
                if leg["destination_id"] == target:
                    key = tuple(
                        (
                            x["service_id"],
                            x["service_date"],
                            x["boarding_stop_id"],
                            x["alighting_stop_id"],
                        )
                        for x in path
                    )
                    if key not in seen:
                        seen.add(key)
                        results.append(path)
                elif len(path) <= max_transfers:
                    frontier.append(
                        (
                            leg["destination_id"],
                            leg["arrival"] + timedelta(minutes=minimum_transfer),
                            path,
                            visited + (leg["destination_id"],),
                            total_wait + wait,
                        )
                    )
        return results

    def connections(self, q, max_transfers=2, minimum_transfer=15, max_expansions=500):
        paths = self.timed_paths(
            q,
            max_transfers=max_transfers,
            minimum_transfer=minimum_transfer,
            horizon_hours=q.days * 24,
            max_expansions=max_expansions,
        )
        results = []
        for path in paths:
            waiting = sum(
                (b["departure"] - a["arrival"]).total_seconds() / 60
                for a, b in itertools.pairwise(path)
            )
            results.append(
                {
                    "legs": path,
                    "transfer_stations": [r["destination_id"] for r in path[:-1]],
                    "departure": path[0]["departure"],
                    "arrival": path[-1]["arrival"],
                    "waiting_minutes": waiting,
                    "total_minutes": (
                        path[-1]["arrival"] - path[0]["departure"]
                    ).total_seconds()
                    / 60,
                    "fare": str(sum(Decimal(x["fare"]) for x in path))
                    if all(x["fare"] is not None for x in path)
                    else None,
                    "search_truncated": self.stats["truncated"],
                }
            )
        return sorted(results, key=lambda x: (x["arrival"], x["departure"]))
