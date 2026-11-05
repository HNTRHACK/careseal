from uuid import UUID, uuid4

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_engine, get_session_factory
from app.models import Organization, OrgMembership, Profile


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    engine = get_engine()
    session_factory = get_session_factory()
    organization_id = None

    try:
        inspector = inspect(engine)

        # Check that every model maps exactly the existing column names.
        for model in (Organization, Profile, OrgMembership):
            database_columns = {
                column["name"]
                for column in inspector.get_columns(
                    model.__tablename__,
                    schema="public",
                )
            }
            model_columns = set(model.__table__.columns.keys())

            require(
                database_columns == model_columns,
                f"Column mismatch for {model.__tablename__}",
            )
            print(f"PASS: {model.__tablename__} column names match")

        # Confirm the external Auth foreign key remains in PostgreSQL.
        profile_foreign_keys = inspector.get_foreign_keys(
            "profiles", schema="public"
        )

        require(
            any(
                fk["constrained_columns"] == ["id"]
                and fk["referred_schema"] == "auth"
                and fk["referred_table"] == "users"
                and fk["referred_columns"] == ["id"]
                and fk.get("options", {}).get("ondelete") == "CASCADE"
                for fk in profile_foreign_keys
            ),
            "Expected profiles -> auth.users foreign key is missing.",
        )
        print("PASS: Supabase Auth foreign key preserved")

        with session_factory() as session:
            try:
                organization = Organization(
                    name=f"SYNTHETIC ORM TEST {uuid4()}",
                    kind="hospital",
                )
                session.add(organization)
                session.flush()
                session.refresh(organization)
                organization_id = organization.id

                require(
                    isinstance(organization.id, UUID),
                    "Database did not return a UUID.",
                )
                require(
                    organization.verification_status == "pending",
                    "Unexpected verification default.",
                )
                require(
                    organization.created_at.tzinfo is not None,
                    "Expected a timezone-aware timestamp.",
                )
                print("PASS: organization insert and defaults")

                # Force a database read instead of an identity-map lookup.
                session.expunge(organization)
                loaded = session.get(Organization, organization_id)

                require(loaded is not None, "Organization read failed.")
                require(loaded.kind == "hospital", "Wrong organization kind.")
                print("PASS: organization database read")

                loaded.name = "SYNTHETIC ORM TEST UPDATED"
                session.flush()
                session.refresh(loaded)

                require(
                    loaded.name == "SYNTHETIC ORM TEST UPDATED",
                    "Organization update failed.",
                )
                print("PASS: organization update")

                # Exercise both mappings without printing existing user data.
                session.execute(select(Profile).limit(1)).all()
                session.execute(select(OrgMembership).limit(1)).all()
                print("PASS: profile and membership read queries")

            finally:
                session.rollback()

        # Verify that the temporary organization was not persisted.
        with session_factory() as session:
            require(
                session.get(Organization, organization_id) is None,
                "Temporary organization persisted unexpectedly.",
            )

        print("PASS: temporary organization absent after rollback")
        print("All ORM checks passed.")
        return 0

    except AssertionError as exc:
        print(f"FAIL: {exc}")
        return 1

    except SQLAlchemyError as exc:
        print(f"ORM check failed ({type(exc).__name__}).")
        print("Raw database details omitted to protect credentials.")
        return 1

    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())