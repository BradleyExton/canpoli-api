from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check() -> dict:
    """Check if the API is running."""
    return {"status": "ok"}
