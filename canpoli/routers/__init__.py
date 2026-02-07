"""API routers."""

from canpoli.routers.account import router as account_router
from canpoli.routers.bills import router as bills_router
from canpoli.routers.billing import router as billing_router
from canpoli.routers.debates import router as debates_router
from canpoli.routers.expenditures import router as expenditures_router
from canpoli.routers.health import router as health_router
from canpoli.routers.parties import router as parties_router
from canpoli.routers.party_standings import router as party_standings_router
from canpoli.routers.petitions import router as petitions_router
from canpoli.routers.representatives import router as representatives_router
from canpoli.routers.roles import router as roles_router
from canpoli.routers.ridings import router as ridings_router
from canpoli.routers.votes import router as votes_router

__all__ = [
    "health_router",
    "account_router",
    "billing_router",
    "bills_router",
    "debates_router",
    "expenditures_router",
    "representatives_router",
    "ridings_router",
    "parties_router",
    "party_standings_router",
    "petitions_router",
    "roles_router",
    "votes_router",
]
