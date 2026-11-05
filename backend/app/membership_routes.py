from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models.identity import Organization, OrgMembership


router = APIRouter(
    prefix="/api/v1",
    tags=["Memberships"],
)


class MembershipResponse(BaseModel):
    organization_id: UUID
    organization_name: str
    organization_kind: Literal[
        "hospital", "ngo", "reviewer", "platform"
    ]
    verification_status: Literal[
        "pending", "verified", "rejected", "suspended"
    ]
    role: Literal[
        "admin",
        "issuer",
        "medical_reviewer",
        "financial_reviewer",
        "funder",
        "auditor",
    ]


@router.get(
    "/me/memberships",
    response_model=list[MembershipResponse],
)
def get_my_memberships(
    response: Response,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MembershipResponse]:
    response.headers["Cache-Control"] = "no-store"

    statement = (
        select(
            Organization.id.label("organization_id"),
            Organization.name.label("organization_name"),
            Organization.kind.label("organization_kind"),
            Organization.verification_status,
            OrgMembership.role,
        )
        .join(
            OrgMembership,
            OrgMembership.organization_id == Organization.id,
        )
        .where(
            OrgMembership.user_id == user.id,
            OrgMembership.status == "active",
        )
        .order_by(Organization.id, OrgMembership.role)
    )

    try:
        rows = db.execute(statement).mappings().all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Membership service temporarily unavailable.",
        ) from None

    return [
        MembershipResponse.model_validate(dict(row))
        for row in rows
    ]