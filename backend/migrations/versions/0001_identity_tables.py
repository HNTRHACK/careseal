"""Create CareSeal identity tables with deny-by-default access."""

from alembic import op


revision = "0001_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE public.organizations (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name text NOT NULL,
            kind text NOT NULL
                CHECK (kind IN (
                    'hospital', 'ngo', 'reviewer', 'platform'
                )),
            registration_reference text,
            verification_status text NOT NULL DEFAULT 'pending'
                CHECK (verification_status IN (
                    'pending', 'verified', 'rejected', 'suspended'
                )),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE public.profiles (
            id uuid PRIMARY KEY
                REFERENCES auth.users(id) ON DELETE CASCADE,
            display_name text NOT NULL DEFAULT '',
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE public.org_memberships (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id uuid NOT NULL
                REFERENCES public.organizations(id),
            user_id uuid NOT NULL
                REFERENCES public.profiles(id),
            role text NOT NULL
                CHECK (role IN (
                    'admin',
                    'issuer',
                    'medical_reviewer',
                    'financial_reviewer',
                    'funder',
                    'auditor'
                )),
            status text NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'disabled')),
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, user_id, role)
        )
        """
    )

    op.execute(
        """
        CREATE INDEX ix_org_memberships_user_organization
        ON public.org_memberships (user_id, organization_id)
        """
    )

    # Alembic creates its version table before running this migration.
    # Protect it along with the application tables.
    for table in (
        "organizations",
        "profiles",
        "org_memberships",
        "alembic_version",
    ):
        op.execute(
            f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"
        )
        op.execute(
            f"REVOKE ALL PRIVILEGES ON TABLE public.{table} "
            "FROM PUBLIC, anon, authenticated"
        )


def downgrade() -> None:
    # Destructive: use only when intentionally rolling back these tables.
    op.drop_index(
        "ix_org_memberships_user_organization",
        table_name="org_memberships",
        schema="public",
    )
    op.drop_table("org_memberships", schema="public")
    op.drop_table("profiles", schema="public")
    op.drop_table("organizations", schema="public")