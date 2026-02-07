"""Vote schemas."""

from datetime import date

from canpoli.schemas.base import BaseSchema, PaginatedResponse


class VoteMemberResponse(BaseSchema):
    """Vote member response schema."""

    id: int
    vote_id: int
    representative_id: int | None = None
    hoc_id: int | None = None
    member_name: str
    position: str
    party_name: str | None = None
    riding_name: str | None = None


class VoteResponse(BaseSchema):
    """Vote response schema."""

    id: int
    vote_number: int
    parliament: int | None = None
    session: int | None = None
    vote_date: date | None = None
    subject_en: str | None = None
    subject_fr: str | None = None
    decision: str | None = None
    yeas: int | None = None
    nays: int | None = None
    paired: int | None = None
    bill_number: str | None = None
    motion_text: str | None = None
    sitting: int | None = None
    members: list[VoteMemberResponse] | None = None


class VoteListResponse(PaginatedResponse):
    """Paginated votes response."""

    votes: list[VoteResponse]
