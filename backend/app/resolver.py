"""Offline station resolution with explicit ambiguity and bounded suggestions."""

import unicodedata
from difflib import SequenceMatcher

from sqlalchemy import func, select

from .catalog import City, CityAlias
from .domain import Alias, Station


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


class StationResolver:
    def __init__(self, session):
        self.session = session

    def resolve(self, value: str):
        key = normalize(value)
        if not key or len(key) > 250:
            raise ValueError("Invalid station query")
        exact = list(
            self.session.scalars(
                select(Station)
                .where(
                    Station.active.is_(True),
                    (Station.id == value)
                    | (func.lower(Station.code) == key)
                    | (func.lower(Station.name) == key),
                )
                .limit(21)
            )
        )
        alias_ids = select(Alias.station_id).where(
            Alias.active.is_(True),
            (Alias.normalized_alias == key) | (func.lower(Alias.name) == key),
        )
        exact += list(
            self.session.scalars(
                select(Station)
                .where(Station.active.is_(True), Station.id.in_(alias_ids))
                .limit(21)
            )
        )
        city_ids = select(City.id).where(
            City.active.is_(True),
            (func.lower(City.name) == key)
            | City.id.in_(
                select(CityAlias.city_id).where(func.lower(CityAlias.name) == key)
            ),
        )
        city_stations = list(
            self.session.scalars(
                select(Station)
                .where(Station.active.is_(True), Station.city_id.in_(city_ids))
                .limit(21)
            )
        )
        if city_stations and not exact:
            return {
                "status": "CITY",
                "candidates": [self._row(s) for s in city_stations],
                "suggestions": [],
            }
        unique = {s.id: s for s in exact}
        if unique:
            return {
                "status": "KNOWN" if len(unique) == 1 else "DISAMBIGUATION_REQUIRED",
                "candidates": [self._row(s) for s in unique.values()],
                "suggestions": [],
            }
        candidates = self.session.scalars(
            select(Station)
            .where(
                Station.active.is_(True), func.lower(Station.name).like(key[:1] + "%")
            )
            .order_by(Station.name)
            .limit(200)
        )
        scores = sorted(
            [
                (SequenceMatcher(None, key, normalize(s.name)).ratio(), s)
                for s in candidates
            ],
            key=lambda x: x[0],
            reverse=True,
        )
        return {
            "status": "UNKNOWN",
            "candidates": [],
            "suggestions": [self._row(s) for score, s in scores[:5] if score >= 0.65],
        }

    def _row(self, s):
        return {"id": s.id, "name": s.name, "code": s.code, "timezone": s.timezone}
