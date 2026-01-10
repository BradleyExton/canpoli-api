from fastapi import FastAPI

from api.civic_context.logging_config import setup_logging
from api.civic_context.routers.civic.router import router as civic_router
from api.civic_context.routers.health.router import router as health_router

# Initialize logging on module load
setup_logging()

app = FastAPI(
    title="Civic Context API",
    description="Canadian political data aggregation API",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(civic_router)
