from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('hospital','ngo','reviewer','platform')"
        ),
        CheckConstraint(
            "verification_status IN "
            "('pending','verified','rejected','suspended')"
        ),
        {"schema": "public"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    registration_reference: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    verification_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'pending'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "public"}

    # The existing migration enforces the FK to auth.users(id).
    # Supabase owns auth.users; we do not map or manage that table.
    # These models are runtime mappings, not an autogeneration baseline.
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("''"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class OrgMembership(Base):
    __tablename__ = "org_memberships"
    __table_args__ = (
        CheckConstraint(
            "role IN "
            "('admin','issuer','medical_reviewer',"
            "'financial_reviewer','funder','auditor')"
        ),
        CheckConstraint("status IN ('active','disabled')"),
        UniqueConstraint("organization_id", "user_id", "role"),
        Index(
            "ix_org_memberships_user_organization",
            "user_id",
            "organization_id",
        ),
        {"schema": "public"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.organizations.id"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'active'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )