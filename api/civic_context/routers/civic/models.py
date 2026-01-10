from pydantic import BaseModel, Field


class Representative(BaseModel):
    """An elected representative."""

    name: str
    party: str | None = None
    riding: str
    email: str | None = None


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
