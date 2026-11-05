from uuid import UUID, uuid4

from fastapi import Response
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.database import get_engine
from app.membership_routes import get_my_memberships
from app.models.identity import Organization, OrgMembership


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> int:
    try:
        user_a = UUID(input("First test user's UID: ").strip())
        user_b = UUID(input("Second test user's UID: ").strip())
    except ValueError:
        print("FAIL: Enter valid UUIDs from Supabase Authentication.")
        return 1

    if user_a == user_b:
        print("FAIL: Use two different test users.")
        return 1

    engine = get_engine()
    org_a, org_b, org_disabled = uuid4(), uuid4(), uuid4()
    test_org_ids = {org_a, org_b, org_disabled}

    try:
        with engine.connect() as connection:
            transaction = connection.begin()

            try:
                # Check existing Auth identities without changing them.
                for user_id in (user_a, user_b):
                    exists = connection.execute(
                        text(
                            "SELECT EXISTS("
                            "SELECT 1 FROM auth.users WHERE id = :id"
                            ")"
                        ),
                        {"id": user_id},
                    ).scalar_one()

                    if not exists:
                        raise AssertionError(
                            "Both UIDs must belong to existing Auth users."
                        )

                    # Preserve any existing profile unchanged.
                    connection.execute(
                        text(
                            "INSERT INTO public.profiles "
                            "(id, display_name) "
                            "VALUES (:id, 'SYNTHETIC TEST USER') "
                            "ON CONFLICT (id) DO NOTHING"
                        ),
                        {"id": user_id},
                    )

                # The session uses this connection's outer transaction.
                with Session(
                    bind=connection,
                    join_transaction_mode="create_savepoint",
                    autoflush=False,
                ) as db:
                    db.add_all(
                        [
                            Organization(
                                id=org_a,
                                name="SYNTHETIC NGO A",
                                kind="ngo",
                                verification_status="verified",
                            ),
                            Organization(
                                id=org_b,
                                name="SYNTHETIC NGO B",
                                kind="ngo",
                                verification_status="verified",
                            ),
                            Organization(
                                id=org_disabled,
                                name="SYNTHETIC DISABLED MEMBERSHIP ORG",
                                kind="ngo",
                                verification_status="verified",
                            ),
                        ]
                    )
                    db.flush()

                    fixtures = [
                        (org_a, user_a, "funder", "active"),
                        (org_a, user_a, "auditor", "active"),
                        (org_a, user_a, "admin", "disabled"),
                        (org_disabled, user_a, "funder", "disabled"),
                        (org_b, user_b, "funder", "active"),
                    ]

                    for org_id, user_id, role, status in fixtures:
                        db.add(
                            OrgMembership(
                                id=uuid4(),
                                organization_id=org_id,
                                user_id=user_id,
                                role=role,
                                status=status,
                            )
                        )
                    db.flush()

                    response_a = Response()
                    memberships_a = get_my_memberships(
                        response=response_a,
                        user=CurrentUser(id=user_a),
                        db=db,
                    )

                    response_b = Response()
                    memberships_b = get_my_memberships(
                        response=response_b,
                        user=CurrentUser(id=user_b),
                        db=db,
                    )

                    # Ignore pre-existing memberships in unrelated orgs.
                    # Compare every result involving our test orgs.
                    actual_a = {
                        (item.organization_id, item.role)
                        for item in memberships_a
                        if item.organization_id in test_org_ids
                    }
                    actual_b = {
                        (item.organization_id, item.role)
                        for item in memberships_b
                        if item.organization_id in test_org_ids
                    }

                    require(
                        actual_a
                        == {(org_a, "funder"), (org_a, "auditor")},
                        "User A sees both own active roles only",
                    )
                    require(
                        actual_b == {(org_b, "funder")},
                        "User B sees own active role only",
                    )
                    require(
                        all(
                            item.organization_id != org_b
                            for item in memberships_a
                        )
                        and all(
                            item.organization_id != org_a
                            for item in memberships_b
                        ),
                        "Other users' organization memberships are excluded",
                    )
                    require(
                        (org_a, "admin") not in actual_a
                        and all(
                            item.organization_id != org_disabled
                            for item in memberships_a
                        ),
                        "Disabled roles and memberships are excluded",
                    )
                    require(
                        response_a.headers.get("cache-control") == "no-store"
                        and response_b.headers.get("cache-control")
                        == "no-store",
                        "Membership responses disable caching",
                    )

            finally:
                transaction.rollback()
                print("Temporary database changes rolled back.")

        # Verify cleanup using a separate connection after rollback.
        with engine.connect() as connection:
            remaining = connection.execute(
                select(Organization.id).where(
                    Organization.id.in_(test_org_ids)
                )
            ).all()

            require(
                not remaining,
                "Synthetic test organizations were not persisted",
            )

    except AssertionError as exc:
        print(f"FAIL: {exc}")
        return 1
    except SQLAlchemyError:
        print("FAIL: Database operation failed.")
        print("Check the database connection and migration state.")
        return 1
    except Exception as exc:
        # Print only the exception type, not credentials or query details.
        print(f"FAIL: Unexpected {type(exc).__name__}.")
        return 1

    print("All membership isolation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())