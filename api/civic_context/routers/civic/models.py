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
    """A parliamentary committee membership (from House of Commons)."""

    name: str
    role: str | None = None


class ParliamentaryAssociation(BaseModel):
    """Parliamentary association or interparliamentary group membership."""

    name: str
    role: str | None = None


class MinisterialRole(BaseModel):
    """A ministerial or cabinet role held by an MP."""

    title: str
    order_of_precedence: int | None = None
    from_date: str | None = None


class ParliamentarySecretaryRole(BaseModel):
    """A parliamentary secretary role held by an MP."""

    title: str
    from_date: str | None = None


class Representative(BaseModel):
    """
    An elected representative with unified data from multiple sources.

    For federal MPs: enriched with House of Commons and OpenParliament data.
    For provincial/municipal: only basic Represent API data (most fields None).
    """

    # Core identity (from Represent API)
    name: str
    riding: str
    party: str | None = None
    email: str | None = None

    # Official profile (from House of Commons - federal MPs only)
    hoc_person_id: int | None = None
    honorific: str | None = None
    province: str | None = None
    photo_url: str | None = None
    profile_url: str | None = None

    # Executive roles (from House of Commons)
    ministerial_role: MinisterialRole | None = None
    parliamentary_secretary_role: ParliamentarySecretaryRole | None = None

    # Parliamentary engagement (from House of Commons)
    committees: list[Committee] = []
    parliamentary_associations: list[ParliamentaryAssociation] = []

    # Legislative activity (from OpenParliament)
    openparliament_url: str | None = None
    bills_sponsored: list[Bill] = []
    recent_votes: list[VoteRecord] = []


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
