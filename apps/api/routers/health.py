from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """
    Public liveness probe.
    Does not expose internal environment, secrets, or credential state.
    """
    return HealthResponse(
        status="healthy",
        service="careseal-api",
        version="0.1.0"
    )

