from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ValidationError

from app.auth_config import get_auth_settings


bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    id: UUID


class SupabaseUserResponse(BaseModel):
    id: UUID
    role: str
    is_anonymous: bool


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="A valid user access token is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def unavailable_error() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Authentication service temporarily unavailable.",
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> CurrentUser:
    if credentials is None:
        raise authentication_error()

    token = credentials.credentials

    # Bound input size and reject malformed header content.
    if (
        not token
        or len(token) > 16384
        or not token.isascii()
        or any(character.isspace() for character in token)
    ):
        raise authentication_error()

    try:
        settings = get_auth_settings()
    except ValidationError:
        raise unavailable_error() from None

    url = (
        settings.supabase_url.rstrip("/")
        + "/auth/v1/user"
    )

    try:
        with httpx.Client(
            timeout=10.0,
            follow_redirects=False,
        ) as client:
            response = client.get(
                url,
                headers={
                    "apikey": (
                        settings.supabase_publishable_key
                        .get_secret_value()
                    ),
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.RequestError:
        raise unavailable_error() from None

    if response.status_code in (400, 401, 403):
        raise authentication_error()

    if response.status_code != 200:
        raise unavailable_error()

    try:
        verified_user = SupabaseUserResponse.model_validate(
            response.json()
        )
    except (ValueError, ValidationError):
        raise unavailable_error() from None

    # CareSeal requires a signed-in, non-anonymous user account.
    if (
        verified_user.role != "authenticated"
        or verified_user.is_anonymous
    ):
        raise authentication_error()

    return CurrentUser(id=verified_user.id)