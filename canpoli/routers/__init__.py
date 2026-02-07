"""API routers."""

from canpoli.routers.account import router as account_router
from canpoli.routers.billing import router as billing_router
from canpoli.routers.health import router as health_router
from canpoli.routers.parties import router as parties_router
from canpoli.routers.representatives import router as representatives_router
from canpoli.routers.ridings import router as ridings_router

__all__ = [
    "health_router",
    "account_router",
    "billing_router",
    "representatives_router",
    "ridings_router",
    "parties_router",
]
