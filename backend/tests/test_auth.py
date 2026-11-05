import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import httpx
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app import auth
from app.main import app


USER_ID = "11111111-1111-4111-8111-111111111111"

VALID_USER = {
    "id": USER_ID,
    "role": "authenticated",
    "is_anonymous": False,
}

TEST_SETTINGS = SimpleNamespace(
    supabase_url="https://auth-test.supabase.co",
    supabase_publishable_key=SecretStr("test-publishable-key"),
)


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.upstream_status = 200
        self.upstream_body = dict(VALID_USER)
        self.timeout = False

        def handle_request(request):
            self.requests.append(request)

            if self.timeout:
                raise httpx.ReadTimeout(
                    "Simulated timeout",
                    request=request,
                )

            return httpx.Response(
                self.upstream_status,
                json=self.upstream_body,
            )

        transport = httpx.MockTransport(handle_request)

        # Replace only app.auth's HTTP client reference.
        # TestClient itself continues using the real httpx module.
        mocked_httpx = SimpleNamespace(
            Client=lambda **kwargs: httpx.Client(
                transport=transport,
                **kwargs,
            ),
            RequestError=httpx.RequestError,
        )

        settings_patch = patch.object(
            auth,
            "get_auth_settings",
            return_value=TEST_SETTINGS,
        )
        http_patch = patch.object(auth, "httpx", mocked_httpx)

        settings_patch.start()
        self.addCleanup(settings_patch.stop)

        http_patch.start()
        self.addCleanup(http_patch.stop)

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def authenticated_request(self):
        return self.client.get(
            "/api/v1/me",
            headers={"Authorization": "Bearer test-access-token"},
        )

    def test_missing_token_is_rejected_without_upstream_request(self):
        response = self.client.get("/api/v1/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")
        self.assertEqual(self.requests, [])

    def test_wrong_authentication_scheme_is_rejected(self):
        response = self.client.get(
            "/api/v1/me",
            headers={"Authorization": "Basic fake-credentials"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.requests, [])

    def test_valid_user_returns_only_identity_and_disables_caching(self):
        response = self.authenticated_request()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": USER_ID})
        self.assertEqual(UUID(response.json()["id"]), UUID(USER_ID))
        self.assertEqual(response.headers["cache-control"], "no-store")

        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(
            str(request.url),
            "https://auth-test.supabase.co/auth/v1/user",
        )
        self.assertEqual(
            request.headers["authorization"],
            "Bearer test-access-token",
        )
        self.assertEqual(
            request.headers["apikey"],
            "test-publishable-key",
        )

    def test_upstream_rejected_tokens_return_401(self):
        for status in (400, 401, 403):
            with self.subTest(status=status):
                self.upstream_status = status
                self.upstream_body = {"message": "private-upstream-detail"}

                response = self.authenticated_request()

                self.assertEqual(response.status_code, 401)
                self.assertNotIn(
                    "private-upstream-detail",
                    response.text,
                )

    def test_upstream_failures_return_503(self):
        for status in (429, 500, 503):
            with self.subTest(status=status):
                self.upstream_status = status

                response = self.authenticated_request()

                self.assertEqual(response.status_code, 503)

    def test_timeout_returns_503(self):
        self.timeout = True

        response = self.authenticated_request()

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("Simulated timeout", response.text)

    def test_anonymous_user_is_rejected(self):
        self.upstream_body = {
            **VALID_USER,
            "is_anonymous": True,
        }

        response = self.authenticated_request()

        self.assertEqual(response.status_code, 401)

    def test_service_role_is_not_accepted_as_a_user(self):
        self.upstream_body = {
            **VALID_USER,
            "role": "service_role",
        }

        response = self.authenticated_request()

        self.assertEqual(response.status_code, 401)

    def test_malformed_user_responses_fail_closed(self):
        for body in (
            {},
            {"id": "not-a-uuid"},
            {**VALID_USER, "id": "not-a-uuid"},
        ):
            with self.subTest(body=body):
                self.upstream_body = body

                response = self.authenticated_request()

                self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()