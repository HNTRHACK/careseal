import uuid
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.db.store import store

client = TestClient(app)


def test_challenge_rejects_unknown_organization():
    """
    Security check: Challenge request with unknown organization is rejected with 404.
    """
    payload = {
        "organization_id": str(uuid.uuid4()),
        "user_id": str(list(store.profiles.keys())[0]),
        "wallet_address": "0x1234567890123456789012345678901234567890",
        "chain_id": 5042002
    }
    response = client.post("/auth/wallet/challenge", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_challenge_rejects_non_member():
    """
    Security check: User not belonging to organization is rejected with 403 Forbidden.
    """
    org_id = list(store.organizations.keys())[0]
    unaffiliated_user = uuid.uuid4()
    # Add profile for unaffiliated user without membership
    store.profiles[unaffiliated_user] = {"id": unaffiliated_user, "display_name": "Outsider"}

    payload = {
        "organization_id": str(org_id),
        "user_id": str(unaffiliated_user),
        "wallet_address": "0x1234567890123456789012345678901234567890",
        "chain_id": 5042002
    }
    response = client.post("/auth/wallet/challenge", json=payload)
    assert response.status_code == 403
    assert "not an active member" in response.json()["detail"]


def test_challenge_rejects_malformed_wallet_address():
    """
    Input validation: Malformed Ethereum wallet address is rejected with 422 Unprocessable Entity.
    """
    payload = {
        "organization_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "wallet_address": "invalid-wallet-address",
        "chain_id": 5042002
    }
    response = client.post("/auth/wallet/challenge", json=payload)
    assert response.status_code == 422


def test_verify_rejects_unknown_challenge():
    """
    Security check: Unknown challenge ID is rejected with 400 Bad Request.
    """
    payload = {
        "challenge_id": str(uuid.uuid4()),
        "wallet_address": "0x1234567890123456789012345678901234567890",
        "signature": "0x" + "a" * 130
    }
    response = client.post("/auth/wallet/verify", json=payload)
    assert response.status_code == 400
    assert "Challenge not found" in response.json()["detail"]
