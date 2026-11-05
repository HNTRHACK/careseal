import uuid
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_world_verify_fails_closed_with_501():
    """
    Security invariant: Unimplemented World ID verification must fail closed (501)
    and never issue a synthetic valid verification bypass.
    """
    payload = {
        "claim_id": str(uuid.uuid4()),
        "action": "review-approval",
        "signal": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "proof": {
            "merkle_root": "0x1234",
            "nullifier_hash": "0x5678",
            "proof": "0xabcd",
            "verification_level": "device"
        },
        "nonce": "test-nonce-1234"
    }
    response = client.post("/auth/world/verify", json=payload)
    assert response.status_code == 501
    assert "Phase 04" in response.json()["detail"]


def test_world_verify_validates_payload_schema():
    """
    Input validation: Missing required fields fail with 422 Unprocessable Entity.
    """
    payload = {
        "claim_id": "not-a-uuid",
        "action": "review-approval"
    }
    response = client.post("/auth/world/verify", json=payload)
    assert response.status_code == 422

