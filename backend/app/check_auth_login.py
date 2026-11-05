"""Manual integration check. Never prints passwords or access tokens."""

from getpass import getpass
from uuid import UUID

import httpx
from pydantic import ValidationError

from app.auth_config import get_auth_settings


def main() -> int:
    try:
        settings = get_auth_settings()
    except ValidationError:
        print("FAIL: Check the Supabase settings in backend/.env.")
        return 1

    email = input("Test user's email: ").strip()
    password = getpass("Test user's password (hidden): ")

    if not email or not password:
        print("FAIL: Email and password are required.")
        return 1

    auth_url = settings.supabase_url.rstrip("/") + "/auth/v1/token"

    try:
        with httpx.Client(timeout=15.0, follow_redirects=False) as client:
            login = client.post(
                auth_url,
                params={"grant_type": "password"},
                headers={
                    "apikey": (
                        settings.supabase_publishable_key.get_secret_value()
                    )
                },
                json={"email": email, "password": password},
            )

            if login.status_code != 200:
                print(
                    f"FAIL: Supabase sign-in returned HTTP "
                    f"{login.status_code}."
                )
                print("Check the credentials and email confirmation status.")
                return 1

            payload = login.json()
            token = payload.get("access_token")
            expected_user_id = UUID(payload["user"]["id"])

            if not isinstance(token, str) or not token:
                print("FAIL: Supabase did not return an access token.")
                return 1

            print("PASS: Supabase accepted the test user's credentials.")

            response = client.get(
                "http://127.0.0.1:8000/api/v1/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code != 200:
                print(
                    f"FAIL: Backend /me returned HTTP "
                    f"{response.status_code}."
                )
                return 1

            user = response.json()

            if UUID(user["id"]) != expected_user_id:
                print("FAIL: Backend returned a different user identity.")
                return 1

            print("PASS: Backend returned the correct authenticated user.")

            if set(user) != {"id"}:
                print("FAIL: /me returned unexpected fields.")
                return 1

            print("PASS: /me exposes only the user ID.")

            if response.headers.get("cache-control") != "no-store":
                print("FAIL: /me is missing Cache-Control: no-store.")
                return 1

            print("PASS: Authenticated response disables caching.")

    except httpx.RequestError:
        print("FAIL: Network request failed.")
        print("Check your internet connection and that Uvicorn is running.")
        return 1
    except (ValueError, KeyError, TypeError, AttributeError):
        print("FAIL: A service returned an unexpected response format.")
        return 1

    print("All real sign-in checks passed. No credentials were printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())