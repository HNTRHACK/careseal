from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_engine


def main() -> int:
    try:
        engine = get_engine()
    except ValidationError:
        print(
            "Configuration check failed. "
            "Check the required DB fields in backend/.env."
        )
        return 1

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()

        if result != 1:
            print("Database returned an unexpected result.")
            return 1

        print("Database connection successful: SELECT 1 returned 1.")
        return 0

    except SQLAlchemyError as exc:
        # Inspect the error locally without printing credentials.
        original = getattr(exc, "orig", exc)
        message = str(original).lower()
        sqlstate = getattr(original, "sqlstate", None)

        print(f"Database connection failed ({type(exc).__name__}).")

        if "password authentication failed" in message:
            print("Reason: database username or password was rejected.")
        elif "tenant or user not found" in message:
            print("Reason: pooler host or username does not match the project.")
        elif any(
            phrase in message
            for phrase in (
                "could not translate host name",
                "name or service not known",
                "temporary failure in name resolution",
                "getaddrinfo failed",
            )
        ):
            print("Reason: database hostname could not be resolved.")
        elif "certificate verify failed" in message:
            print("Reason: SSL certificate verification failed.")
        elif "ssl" in message:
            print("Reason: an SSL connection error occurred.")
        elif "timeout" in message or "timed out" in message:
            print("Reason: connection timed out.")
        elif "connection refused" in message:
            print("Reason: the host refused the connection.")
        elif "network is unreachable" in message:
            print("Reason: the database network is unreachable.")
        else:
            print("Reason: unclassified connection error.")

        if sqlstate:
            print(f"SQLSTATE: {sqlstate}")

        return 1

    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())