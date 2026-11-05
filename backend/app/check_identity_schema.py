from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.database import get_engine


def expect_rejection(
    connection,
    label,
    statement,
    expected_sqlstate,
    parameters=None,
    role=None,
):
    try:
        # A savepoint isolates each expected failure.
        # Rolling it back also restores any temporary role change.
        with connection.begin_nested():
            if role == "anon":
                connection.execute(text("SET LOCAL ROLE anon"))
            elif role == "authenticated":
                connection.execute(text("SET LOCAL ROLE authenticated"))
            elif role is not None:
                raise ValueError("Unsupported test role.")

            connection.execute(text(statement), parameters or {})

            raise AssertionError(
                f"{label}: operation unexpectedly succeeded."
            )

    except DBAPIError as exc:
        actual_sqlstate = getattr(exc.orig, "sqlstate", None)

        if actual_sqlstate != expected_sqlstate:
            raise AssertionError(
                f"{label}: expected SQLSTATE {expected_sqlstate}, "
                f"received {actual_sqlstate}."
            ) from None

        print(f"PASS: {label}")


def main():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            transaction = connection.begin()

            try:
                # Create one valid, temporary synthetic organization.
                organization_id = connection.execute(
                    text(
                        """
                        INSERT INTO public.organizations (name, kind)
                        VALUES (:name, 'hospital')
                        RETURNING id
                        """
                    ),
                    {"name": f"SYNTHETIC SCHEMA TEST {uuid4()}"},
                ).scalar_one()

                print("PASS: valid synthetic organization accepted")

                expect_rejection(
                    connection,
                    "invalid organization kind rejected",
                    """
                    INSERT INTO public.organizations (name, kind)
                    VALUES ('SYNTHETIC INVALID KIND', 'invalid_kind')
                    """,
                    "23514",
                )

                expect_rejection(
                    connection,
                    "invalid verification status rejected",
                    """
                    INSERT INTO public.organizations
                        (name, kind, verification_status)
                    VALUES
                        ('SYNTHETIC INVALID STATUS', 'ngo', 'invalid_status')
                    """,
                    "23514",
                )

                expect_rejection(
                    connection,
                    "profile without an Auth user rejected",
                    """
                    INSERT INTO public.profiles (id, display_name)
                    VALUES (:user_id, 'SYNTHETIC MISSING USER')
                    """,
                    "23503",
                    {"user_id": uuid4()},
                )

                expect_rejection(
                    connection,
                    "membership without a profile rejected",
                    """
                    INSERT INTO public.org_memberships
                        (organization_id, user_id, role)
                    VALUES (:organization_id, :user_id, 'issuer')
                    """,
                    "23503",
                    {
                        "organization_id": organization_id,
                        "user_id": uuid4(),
                    },
                )

                for role in ("anon", "authenticated"):
                    for table in (
                        "organizations",
                        "profiles",
                        "org_memberships",
                        "alembic_version",
                    ):
                        expect_rejection(
                            connection,
                            f"{role} cannot read {table}",
                            f"SELECT * FROM public.{table} LIMIT 1",
                            "42501",
                            role=role,
                        )

            finally:
                # Never persist the temporary organization.
                transaction.rollback()

        print("All identity checks passed. Test changes rolled back.")
        return 0

    except AssertionError as exc:
        print(f"FAIL: {exc}")
        return 1

    except DBAPIError as exc:
        sqlstate = getattr(exc.orig, "sqlstate", None)
        print(f"Database test failed. SQLSTATE: {sqlstate}")
        print("Raw database details omitted to protect credentials.")
        return 1

    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())