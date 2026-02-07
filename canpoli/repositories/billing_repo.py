"""Repository for billing records."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.models.billing import Billing
from canpoli.repositories.base import BaseRepository


class BillingRepository(BaseRepository[Billing]):
    """Billing repository with Stripe lookup helpers."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Billing)

    async def get_by_user_id(self, user_id: str) -> Billing | None:
        """Fetch billing record by user id."""
        result = await self.session.execute(
            select(Billing).where(Billing.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_customer_id(self, customer_id: str) -> Billing | None:
        """Fetch billing record by Stripe customer id."""
        result = await self.session.execute(
            select(Billing).where(Billing.stripe_customer_id == customer_id)
        )
        return result.scalar_one_or_none()
