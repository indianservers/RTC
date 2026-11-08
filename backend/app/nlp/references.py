"""Resolve only from valid current result references; never assume a tie-break."""

import hashlib
from decimal import Decimal


def stable_results(rows):
    return [
        {
            **r,
            "result_id": hashlib.sha256(
                "|".join(
                    str(r.get(k, ""))
                    for k in ("service_id", "service_date", "departure", "arrival")
                ).encode()
            ).hexdigest()[:20],
        }
        for r in rows
    ]


class ReferentialResolver:
    def resolve(self, text, values):
        rows = values.get("candidates", [])
        if not rows:
            raise ValueError(
                "Please request a current result list before selecting a bus."
            )
        if "cheaper" in text or "cheapest one" in text:
            known = [r for r in rows if r.get("fare") is not None]
            if not known:
                raise ValueError("No known fares are available for comparison.")
            best = min(Decimal(str(r["fare"])) for r in known)
            matches = [r for r in known if Decimal(str(r["fare"])) == best]
        elif "fastest one" in text:
            from datetime import datetime

            known = [r for r in rows if r.get("arrival") and r.get("departure")]
            if not known:
                raise ValueError("Arrival times are unavailable for comparison.")
            duration = lambda r: (
                datetime.fromisoformat(r["arrival"])
                - datetime.fromisoformat(r["departure"])
            )
            best = min(duration(r) for r in known)
            matches = [r for r in known if duration(r) == best]
        elif "previous one" in text:
            history = values.get("selected_service_history", [])
            if not history:
                raise ValueError("There is no previous confirmed selection.")
            matches = [r for r in rows if r["service_id"] == history[-1]]
        else:
            selected = values.get("service_id")
            matches = [r for r in rows if r["service_id"] == selected]
        if len(matches) != 1:
            raise ValueError(
                "Several or no current options match. Which listed service do you mean?"
            )
        return next(
            i
            for i, r in enumerate(rows)
            if r.get("result_id", r["service_id"])
            == matches[0].get("result_id", matches[0]["service_id"])
        )
