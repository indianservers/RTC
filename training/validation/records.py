"""Typed synthetic candidate records; no training split is assigned here."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Entity(BaseModel):
    type: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    value: str | bool | int | None = None
    canonical_id: str | None = None


class Example(BaseModel):
    example_id: str
    text: str = Field(min_length=1, max_length=4000)
    language: Literal["en"] = "en"
    intent_codes: list[str]
    dialogue_act: str | None = None
    dataset_type: str
    style: str
    entities: list[Entity]
    context: dict
    source_type: Literal["SYNTHETIC"] = "SYNTHETIC"
    generator_version: str
    template_family: str
    quality_status: Literal["PENDING_HUMAN_REVIEW"] = "PENDING_HUMAN_REVIEW"
    dataset_version: str
    provenance: dict
    parent_example_id: str | None = None
    clean_transcript: str | None = None
    noisy_transcript: str | None = None
    constraints: dict = Field(default_factory=dict)
    possible_intents: list[str] = Field(default_factory=list)
    missing_slots: list[str] = Field(default_factory=list)
    clarification_target: str | None = None
    slot_changes: dict = Field(default_factory=dict)
    expected_context: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def spans(self):
        for e in self.entities:
            if (
                not e.start < e.end <= len(self.text)
                or self.text[e.start : e.end] != e.text
            ):
                raise ValueError("Entity span mismatch")
        if self.dataset_type == "CONTEXTUAL" and not self.context:
            raise ValueError("Follow-up requires explicit prior context")
        if self.dataset_type == "MULTI_INTENT" and len(set(self.intent_codes)) < 2:
            raise ValueError("Multi-intent requires two actual enquiry intents")
        if self.dataset_type == "AMBIGUOUS" and self.intent_codes:
            raise ValueError("Ambiguity must not assert a single correct enquiry")
        return self
