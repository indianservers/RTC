import re
import unicodedata
from datetime import date, datetime, time, timedelta


class LanguageNormalizer:
    def normalize(self, text):
        return " ".join(unicodedata.normalize("NFKC", text).casefold().split())

    def language(self, text):
        telugu = bool(re.search("[\u0c00-\u0c7f]", text))
        latin = bool(re.search("[a-zA-Z]", text))
        return (
            "mixed"
            if telugu and latin
            else "te"
            if telugu
            else "te-Latn"
            if re.search(r"\b(ki|nunchi|eppudu|repu|unda|entha)\b", text)
            else "en"
        )


class IntentClassifier:
    def __init__(self, rules):
        self.rules = rules

    def classify(self, text):
        matches = []
        for intent, phrases in self.rules.items():
            if any(
                re.search(r"(?<!\w)" + re.escape(p) + r"(?!\w)", text) for p in phrases
            ):
                matches.append(intent)
        return matches


class TemporalParser:
    def parse(self, text, now, context_date=None):
        if now.tzinfo is None:
            raise ValueError("Station-local aware clock required")
        original_text = text
        text = text.casefold()
        explicit_relative = bool(
            re.search(
                r"today|tomorrow|tonight|this evening|next .*hours?|after midnight|repu|రేపు|ellundi|ఎల్లుండి",
                text,
            )
        )
        day = (
            date.fromisoformat(context_date)
            if context_date and not explicit_relative
            else now.date()
        )
        if re.search(
            r"day after tomorrow|ellundi|ఎల్లుండి|not tomorrow.*day after", text
        ):
            day += timedelta(days=2)
        elif any(x in text for x in ("tomorrow", "repu", "రేపు")):
            day += timedelta(days=1)
        match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
        if match:
            day = date.fromisoformat(match[0])
        morning = any(x in text for x in ("morning", "podduna", "ఉదయం"))
        filters = {}
        midnight = datetime.combine(day, time.min, now.tzinfo)
        for match in re.finditer(
            r"\b(after|before|around)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text
        ):
            if re.search(r"\bnot\s*$", text[: match.start()]):
                continue
            hour = int(match[2])
            minute = int(match[3] or 0)
            if hour > 23 or minute > 59 or match[4] and not 1 <= hour <= 12:
                raise ValueError("Please give a valid clock time.")
            if not match[4] and hour < 13 and not match[3]:
                raise ValueError("Do you mean AM or PM?")
            if match[4]:
                hour = hour % 12 + (12 if match[4] == "pm" else 0)
            timestamp = midnight.replace(hour=hour, minute=minute)
            if match[1] == "around":
                filters.update(
                    after=(timestamp - timedelta(minutes=15)).isoformat(),
                    before=(timestamp + timedelta(minutes=15)).isoformat(),
                )
            else:
                relation = (
                    "arrival_"
                    if re.search(
                        r"arriv(?:e|ing|al)|reach(?:ing)?", text[: match.start()]
                    )
                    else ""
                ) + match[1]
                filters[relation] = timestamp.isoformat()
        relative = re.search(r"next (one|two|three|\d+) hours?", text)
        if relative:
            hours = (
                int(relative[1])
                if relative[1].isdigit()
                else {"one": 1, "two": 2, "three": 3}[relative[1]]
            )
            if not 1 <= hours <= 24:
                raise ValueError("Use a search window of 1 to 24 hours.")
            filters.update(
                after=now.isoformat(), before=(now + timedelta(hours=hours)).isoformat()
            )
        if "after midnight" in text:
            start = midnight + timedelta(days=1) if day == now.date() else midnight
            day = start.date()
            filters["after"] = start.isoformat()
        return {
            "travel_date": day.isoformat(),
            "morning": morning,
            "filters": filters,
            "time_expression": original_text,
            "explicit_relative": explicit_relative,
            "resolved_at": now.isoformat(),
        }
