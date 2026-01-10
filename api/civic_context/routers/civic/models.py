from pydantic import BaseModel, Field


class Bill(BaseModel):
    """A bill sponsored by an MP."""

    number: str
    name: str
    introduced: str
    session: str


class VoteRecord(BaseModel):
    """An MP's vote on a parliamentary division."""

    session: str
    vote_number: int
    mp_vote: str
    vote_url: str


class Committee(BaseModel):
    """A parliamentary committee membership."""

    name: str
    acronym: str | None = None


class ParliamentaryActivity(BaseModel):
    """Parliamentary activity data for a federal MP."""

    openparliament_url: str | None = None
    bills_sponsored: list[Bill] = []
    recent_votes: list[VoteRecord] = []
    committees: list[Committee] = []


class Representative(BaseModel):
    """An elected representative."""

    name: str
    party: str | None = None
    riding: str
    email: str | None = None
    parliamentary_activity: ParliamentaryActivity | None = None


class Representatives(BaseModel):
    """Representatives at all levels of government."""

    federal: Representative | None = None
    provincial: Representative | None = None
    municipal: Representative | None = None


class Location(BaseModel):
    """A geographic location."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class CivicContextResponse(BaseModel):
    """Complete civic context response."""

    representatives: Representatives
    location: Location
