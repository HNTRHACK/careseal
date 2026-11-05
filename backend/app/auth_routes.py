from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.auth import CurrentUser, get_current_user


router = APIRouter(
    prefix="/api/v1",
    tags=["Authentication"],
)


@router.get("/me", response_model=CurrentUser)
def get_me(
    response: Response,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    response.headers["Cache-Control"] = "no-store"
    return user