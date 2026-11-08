import re
import unicodedata
from datetime import timedelta


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
    def parse(self, text, now):
        day = now.date()
        if any(x in text for x in ["day after tomorrow", "ellundi", "ఎల్లుండి"]):
            day += timedelta(days=2)
        elif any(x in text for x in ["tomorrow", "repu", "రేపు"]):
            day += timedelta(days=1)
        match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
        if match:
            from datetime import date

            day = date.fromisoformat(match.group())
        morning = any(x in text for x in ["morning", "podduna", "ఉదయం"])
        return {"travel_date": day.isoformat(), "morning": morning}
