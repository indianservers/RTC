"""Exact DB vocabulary annotations only. Unclear roles are left unannotated."""

import re


def annotate(text, vocabulary):
    name_ids = {}
    for name, identifier in vocabulary["places"]:
        name_ids.setdefault(name.casefold(), set()).add(identifier)
    entities = []
    used = []
    for name, identifier in sorted(
        vocabulary["places"], key=lambda x: (-len(x[0]), x[0], x[1])
    ):
        if len(name_ids[name.casefold()]) != 1:
            continue
        for m in re.finditer(
            r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.IGNORECASE
        ):
            if any(m.start() < end and m.end() > start for start, end in used):
                continue
            prefix = text[: m.start()].casefold()
            role = (
                "ORIGIN_STATION"
                if re.search(r"\bfrom\s*$", prefix)
                else "VIA_STATION"
                if re.search(r"\bvia\s*$", prefix)
                else "DESTINATION_STATION"
                if re.search(r"\b(?:to|for|reach)\s*$", prefix)
                else None
            )
            if role:
                entities.append(
                    {
                        "type": role,
                        "text": m[0],
                        "start": m.start(),
                        "end": m.end(),
                        "value": name,
                        "canonical_id": identifier,
                    }
                )
                used.append((m.start(), m.end()))
    for name, identifier in vocabulary["categories"]:
        for m in re.finditer(
            r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.IGNORECASE
        ):
            entities.append(
                {
                    "type": "BUS_CATEGORY",
                    "text": m[0],
                    "start": m.start(),
                    "end": m.end(),
                    "value": name,
                    "canonical_id": identifier,
                }
            )
    for m in re.finditer(r"\b(?:non[ -]?AC|no AC|not AC|AC)\b", text, re.IGNORECASE):
        entities.append(
            {
                "type": "AC_PREFERENCE",
                "text": m[0],
                "start": m.start(),
                "end": m.end(),
                "value": m[0].casefold() == "ac",
            }
        )
    for m in re.finditer(r"\b(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\b", text, re.IGNORECASE):
        hour = int(m[1])
        minute = int(m[2] or 0)
        if not 1 <= hour <= 12 or minute > 59:
            continue
        hour = hour % 12 + (12 if m[3].casefold() == "pm" else 0)
        entities.append(
            {
                "type": "TIME",
                "text": m[0],
                "start": m.start(),
                "end": m.end(),
                "value": f"{hour:02}:{minute:02}",
            }
        )
    for m in re.finditer(
        r"\b(\d+|one|two|three|four)\s+(?:seats?|passengers?)\b", text, re.IGNORECASE
    ):
        value = (
            int(m[1])
            if m[1].isdigit()
            else {"one": 1, "two": 2, "three": 3, "four": 4}[m[1].casefold()]
        )
        entities.append(
            {
                "type": "SEAT_COUNT",
                "text": m[0],
                "start": m.start(),
                "end": m.end(),
                "value": value,
            }
        )
    return sorted(entities, key=lambda e: (e["start"], e["end"], e["type"]))
