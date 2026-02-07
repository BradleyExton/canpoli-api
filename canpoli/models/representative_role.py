"""Representative role model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canpoli.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from canpoli.models.representative import Representative


class RepresentativeRole(Base, TimestampMixin):
    """Roles held by a representative (committee, caucus, ministry, etc.)."""

    __tablename__ = "representative_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    representative_id: Mapped[int] = mapped_column(
        ForeignKey("representatives.id"), nullable=False
    )

    role_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role_type: Mapped[str] = mapped_column(String(50), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(200))

    parliament: Mapped[int | None] = mapped_column()
    session: Mapped[int | None] = mapped_column()

    start_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    source_url: Mapped[str | None] = mapped_column(String(500))
    source_hash: Mapped[str | None] = mapped_column(String(64))

    representative: Mapped[Representative] = relationship(back_populates="roles")

    __table_args__ = (
        Index("ix_representative_roles_representative_id", "representative_id"),
        Index("ix_representative_roles_parl_session", "parliament", "session"),
        Index("ix_representative_roles_is_current", "is_current"),
    )

    def __repr__(self) -> str:
        return f"<RepresentativeRole {self.role_type}: {self.role_name}>"
