import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.routers import health, auth, world, cre, claims

# Load allowed origins from environment (deny-by-default for non-local origins)
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app = FastAPI(
    title="CareSeal API",
    description="Shared claim verification and programmable medical-aid settlement API (Hackathon MVP)",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None
)

# Explicit, restricted CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Register modular routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(world.router)
app.include_router(cre.router)
app.include_router(claims.router)
