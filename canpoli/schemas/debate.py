"""Debate schemas."""

from datetime import date

from canpoli.schemas.base import BaseSchema, PaginatedResponse


class DebateInterventionResponse(BaseSchema):
    """Debate intervention response schema."""

    id: int
    debate_id: int
    sequence: int
    speaker_name: str | None = None
    speaker_affiliation: str | None = None
    floor_language: str | None = None
    timestamp: str | None = None
    order_of_business: str | None = None
    subject_title: str | None = None
    intervention_type: str | None = None
    text: str | None = None


class DebateResponse(BaseSchema):
    """Debate response schema."""

    id: int
    parliament: int | None = None
    session: int | None = None
    sitting: int | None = None
    debate_date: date | None = None
    language: str | None = None
    volume: str | None = None
    number: str | None = None
    speaker_name: str | None = None
    document_url: str | None = None
    interventions: list[DebateInterventionResponse] | None = None


class DebateListResponse(PaginatedResponse):
    """Paginated debates response."""

    debates: list[DebateResponse]
