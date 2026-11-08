"""Explicit one-time seed: never replaces daily operator edits."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .catalog import Intent, Template, Utterance
from .domain import database


def seed_nlp(engine):
    rules = json.loads(
        (Path(__file__).resolve().parents[2] / "config/nlp_rules.json").read_text(
            encoding="utf-8"
        )
    )
    with Session(engine) as s, s.begin():
        for code, phrases in rules.items():
            intent = s.scalar(select(Intent).where(Intent.code == code))
            if intent is None:
                intent = Intent(code=code, description=code)
                s.add(intent)
                s.flush()
            # Seed each intent only once; never resurrect removed or edited rules.
            if not s.scalar(
                select(Utterance.id)
                .where(
                    Utterance.intent_id == intent.id, Utterance.source_type == "RULE"
                )
                .limit(1)
            ):
                for phrase in phrases:
                    s.add(
                        Utterance(
                            intent_id=intent.id,
                            text=phrase,
                            language="mixed",
                            source_type="RULE",
                            quality_status="PENDING",
                        )
                    )
        dialogue = s.scalar(select(Intent).where(Intent.code == "DIALOGUE_CONTENT"))
        if dialogue is None:
            dialogue = Intent(
                code="DIALOGUE_CONTENT", description="Editable dialogue copy"
            )
            s.add(dialogue)
            s.flush()
        texts = {
            "RESULTS_UPDATED": (
                "The current list now has {count} options. Choose a listed service.",
                "ప్రస్తుత జాబితాలో {count} ఎంపికలు ఉన్నాయి.",
            ),
            "DEMO_NOTICE": ("Demonstration data.", "ప్రదర్శన సమాచారం."),
            "NO_RESULTS": (
                "No matching information is available.",
                "సరిపోలే సమాచారం అందుబాటులో లేదు.",
            ),
            "DETAILS": (
                "Details are available in the structured results.",
                "వివరాలు అందుబాటులో ఉన్నాయి.",
            ),
            "SCHEDULED": (
                "Service {service_number}: scheduled departure {departure}.",
                "{service_number}: షెడ్యూల్ బయలుదేరు సమయం {departure}.",
            ),
            "ESTIMATED": (
                "Service {service_number}: estimated departure {departure}.",
                "{service_number}: అంచనా బయలుదేరు సమయం {departure}.",
            ),
            "FARE": ("Fare: INR {fare}.", "టికెట్ ధర: రూ. {fare}."),
            "HELP": (
                "Tell me your destination and the bus information you need.",
                "మీ గమ్యం మరియు కావలసిన బస్సు సమాచారం చెప్పండి.",
            ),
            "IDLE": (
                "Please ask about a bus destination, timing, fare or facility.",
                "బస్సు గమ్యం లేదా సమయం గురించి అడగండి.",
            ),
            "AWAITING_DESTINATION": (
                "Where would you like to travel?",
                "మీరు ఎక్కడికి వెళ్లాలి?",
            ),
            "AWAITING_ORIGIN": ("Where are you boarding?", "మీరు ఎక్కడ ఎక్కుతారు?"),
            "AWAITING_STATION_CLARIFICATION": (
                "Which station do you mean?",
                "మీరు ఏ బస్ స్టేషన్ గురించి అడుగుతున్నారు?",
            ),
        }
        for status, pair in texts.items():
            for language, text in zip(("en", "te"), pair, strict=True):
                if not s.scalar(
                    select(Template.id)
                    .where(
                        Template.intent_id == dialogue.id,
                        Template.response_status == status,
                        Template.language == language,
                    )
                    .limit(1)
                ):
                    s.add(
                        Template(
                            intent_id=dialogue.id,
                            response_status=status,
                            language=language,
                            text=text,
                        )
                    )


if __name__ == "__main__":
    seed_nlp(database())
