"""Read editable NLP content on each request; no process-local content cache."""

import html
import re

from sqlalchemy import select

from ..catalog import Intent, Template, Utterance


class NLPContentRepository:
    def __init__(self, session):
        self.session = session

    def rules(self):
        rows = self.session.execute(
            select(Intent, Utterance.text)
            .join(Utterance, Utterance.intent_id == Intent.id)
            .where(
                Intent.active.is_(True),
                Utterance.active.is_(True),
                Utterance.source_type == "RULE",
            )
            .order_by(Intent.code, Utterance.id)
        )
        rules = {}
        for intent, text in rows:
            canonical = (
                self.session.get(Intent, intent.canonical_id)
                if intent.canonical_id
                else intent
            )
            if (
                canonical
                and canonical.active
                and canonical.registry_kind not in ("DIALOGUE_ACT", "INTERNAL")
            ):
                rules.setdefault(canonical.code, []).append(text.casefold())
        return rules

    def render(self, status, language, values=None):
        candidates = self.session.scalars(
            select(Template)
            .join(Intent, Intent.id == Template.intent_id)
            .where(
                Intent.code == "DIALOGUE_CONTENT",
                Intent.active.is_(True),
                Template.active.is_(True),
                Template.response_status == status,
                Template.language.in_([language, "en"]),
            )
            .order_by(Template.id)
        )
        rows = list(candidates)
        row = next((r for r in rows if r.language == language), None) or next(
            (r for r in rows if r.language == "en"), None
        )
        if row is None:
            return ""
        values = values or {}
        required = set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", row.text))
        if any(key not in values or values[key] is None for key in required):
            return ""
        return re.sub(
            r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}",
            lambda m: html.escape(str(values[m[1]])),
            row.text,
        )
