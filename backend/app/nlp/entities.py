"""Database-backed lexicon extraction; facts remain in the enquiry engine."""

import re

from sqlalchemy import select

from ..catalog import BusAlias
from ..domain import Alias, Category, Station


class RTCEntityExtractor:
    def __init__(self, session):
        self.session = session

    def extract(self, text):
        lexicon = [
            (name, s.id)
            for s in self.session.scalars(
                select(Station).where(Station.active.is_(True))
            )
            for name in (s.name, s.code)
        ]
        lexicon += [
            (s.name, s.station_id)
            for s in self.session.scalars(select(Alias).where(Alias.active.is_(True)))
        ]
        matches = []
        for name, identifier in lexicon:
            for match in re.finditer(
                r"(?<!\w)" + re.escape(name.casefold()) + r"(?![a-z])", text
            ):
                matches.append((match.start(), match.end(), identifier))
        matches = [m for m in matches if not re.search(r"\bnot\s*$", text[: m[0]])]
        for begin, end, identifier in matches:
            if len({m[2] for m in matches if m[0] == begin and m[1] == end}) > 1:
                raise ValueError(
                    "Which station do you mean by '"
                    + text[begin:end]
                    + "'? Please use its station code."
                )
        matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        selected = []
        for match in matches:
            if not selected or match[0] >= selected[-1][1]:
                selected.append(match)
        places = [m[2] for m in selected]
        values = {}
        if len(places) >= 2:
            values.update(origin=places[0], destination=places[-1])
        elif places:
            values[
                "origin"
                if re.search(r"\b(from|nunchi)\b|నుంచి", text)
                and not re.search(r"\b(to|ki)\b", text)
                else "destination"
            ] = places[0]
        via = re.search(r"\bvia\s+", text)
        if via:
            after = [m for m in selected if m[0] >= via.end()]
            if after:
                values["via"] = after[0][2]
                before = [m[2] for m in selected if m[0] < via.start()]
                if before:
                    values["destination"] = before[-1]
                if len(before) < 2:
                    values.pop("origin", None)
        if re.search(
            r"\b(?:next bus|travel|going)\s+to\s+[a-z]", text
        ) and not values.get("destination"):
            raise ValueError(
                "Which destination station do you mean? Please use a station name or code from this database."
            )
        filters = {}
        if re.search(r"\bnon[ -]?ac\b", text):
            filters["ac"] = False
        elif re.search(r"\bac\b|ఏసీ", text):
            filters["ac"] = True
        if re.search(r"\bsleeper\b|స్లీపర్", text):
            filters["sleeper"] = True
        if re.search(r"\bseater\b", text):
            filters["sleeper"] = False
        for row in self.session.scalars(
            select(Category).where(Category.active.is_(True))
        ):
            if row.name.casefold() in text:
                location = text.find(row.name.casefold())
                if re.search(r"(?:except|not)\s*$", text[:location]):
                    filters.setdefault("exclude_categories", []).append(row.id)
                else:
                    filters["category"] = row.id
        for alias in self.session.scalars(
            select(BusAlias).where(BusAlias.active.is_(True))
        ):
            if re.search(
                r"(?<!\w)" + re.escape(alias.name.casefold()) + r"(?!\w)", text
            ):
                location = text.find(alias.name.casefold())
                if re.search(r"(?:except|not)\s*$", text[:location]):
                    filters.setdefault("exclude_categories", []).append(
                        alias.category_id
                    )
                else:
                    filters["category"] = alias.category_id
        if re.search(r"\bwheelchair|accessible\b", text):
            filters["accessible"] = True
        if re.search(r"\belectric\b", text):
            filters["electric"] = True
        maximum = re.search(
            r"\b(?:under|below|less than|maximum)\s*(?:rs\.?|rupees|inr)?\s*(\d+(?:\.\d{1,2})?)",
            text,
        )
        if maximum:
            filters["max_fare"] = maximum[1]
        numbers = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        counts = []
        for match in re.finditer(
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:seats?|passengers?|people)\b",
            text,
        ):
            if re.search(r"\bnot\s*$", text[: match.start()]):
                continue
            counts.append(int(match[1]) if match[1].isdigit() else numbers[match[1]])
        if counts:
            if len(set(counts)) != 1 or not 1 <= counts[0] <= 100:
                raise ValueError(
                    "How many passengers, from 1 to 100, should I search for?"
                )
            values["passengers"] = counts[0]
        service = re.search(r"\bservice\s+(?:number\s+)?([a-z0-9-]+)", text)
        if service:
            values["service_number"] = service[1]
        from .constraints import constraints

        filters.update(constraints(text))
        values["filters"] = filters
        return values
