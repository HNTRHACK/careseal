from fastapi import FastAPI
from pydantic import BaseModel
from app.auth_routes import router as auth_router


app = FastAPI(
    title="CareSeal API",
    description=(
        "Medical-aid claim verification, "
        "NGO funding coordination, and settlement tracking."
    ),
    version="0.1.0",
)


class RootResponse(BaseModel):
    service: str
    docs_url: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/", response_model=RootResponse, tags=["System"])
def root() -> RootResponse:
    return RootResponse(
        service="CareSeal API",
        docs_url="/docs",
    )


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["System"],
)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="careseal-api",
        version=app.version,
    )

app.include_router(auth_router)