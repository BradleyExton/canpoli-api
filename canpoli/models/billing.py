"""Billing model storing Stripe subscription state."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from canpoli.models.base import Base, TimestampMixin


class Billing(TimestampMixin, Base):
    """Stripe billing linkage for a user."""

    __tablename__ = "billing"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str | None] = mapped_column(String(32))
    price_id: Mapped[str | None] = mapped_column(String(128))
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
