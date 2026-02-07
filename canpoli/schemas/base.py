"""Base schema configuration."""

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration for ORM model conversion."""

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel):
    """Base for paginated list responses."""

    total: int
    limit: int
    offset: int
