from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models.identity import Organization, OrgMembership


@dataclass(frozen=True)
class OrganizationAccess:
    user_id: UUID
    organization_id: UUID
    organization_kind: str
    role: str


def require_organization_role(
    *,
    db: Session,
    user: CurrentUser,
    organization_id: UUID,
    required_role: str,
    required_kind: str,
) -> OrganizationAccess:
    """Check current database permissions for one specific organization.

    required_role and required_kind must be constants chosen by backend
    code, never permission requirements supplied by the browser.

    This check does not enforce claim ownership, reviewer independence,
    wallet verification, or workflow state.
    """
    statement = (
        select(OrgMembership.id)
        .join(
            Organization,
            Organization.id == OrgMembership.organization_id,
        )
        .where(
            OrgMembership.user_id == user.id,
            OrgMembership.organization_id == organization_id,
            OrgMembership.status == "active",
            OrgMembership.role == required_role,
            Organization.verification_status == "verified",
            Organization.kind == required_kind,
        )
        .limit(1)
    )

    try:
        membership_id = db.execute(statement).scalar_one_or_none()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Authorization service temporarily unavailable.",
        ) from None

    if membership_id is None:
        # Same response for missing organizations, missing memberships,
        # disabled memberships, wrong roles, and unverified organizations.
        raise HTTPException(
            status_code=403,
            detail="You are not authorized for this organization action.",
        )

    return OrganizationAccess(
        user_id=user.id,
        organization_id=organization_id,
        organization_kind=required_kind,
        role=required_role,
    )