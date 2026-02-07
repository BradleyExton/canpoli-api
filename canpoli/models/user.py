"""User model for authenticated portal accounts."""

from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from canpoli.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    """User linked to an external auth provider (Clerk)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    auth_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    auth_user_id: Mapped[str] = mapped_column(String(191), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
