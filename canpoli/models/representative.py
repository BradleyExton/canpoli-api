"""Representative (MP) model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canpoli.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from canpoli.models.party import Party
    from canpoli.models.representative_role import RepresentativeRole
    from canpoli.models.riding import Riding


class Representative(Base, TimestampMixin):
    """Federal Member of Parliament."""

    __tablename__ = "representatives"

    id: Mapped[int] = mapped_column(primary_key=True)
    hoc_id: Mapped[int] = mapped_column(
        unique=True, nullable=False
    )  # House of Commons ID - public API identifier

    # Names
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200), nullable=False)  # Full name
    honorific: Mapped[str | None] = mapped_column(String(50))  # "Hon.", "Right Hon."

    # Contact
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50))

    # Links
    photo_url: Mapped[str | None] = mapped_column(String(500))
    profile_url: Mapped[str | None] = mapped_column(String(500))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Foreign keys
    party_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"))
    riding_id: Mapped[int | None] = mapped_column(ForeignKey("ridings.id"))

    # Relationships
    party: Mapped[Party | None] = relationship(back_populates="representatives")
    riding: Mapped[Riding | None] = relationship(back_populates="representatives")
    roles: Mapped[list[RepresentativeRole]] = relationship(
        back_populates="representative"
    )

    __table_args__ = (
        Index("ix_representatives_hoc_id", "hoc_id"),
        Index("ix_representatives_name", "name"),
        Index("ix_representatives_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Representative {self.name}>"
