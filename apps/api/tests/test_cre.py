import uuid
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_cre_envelope_unknown_claim_returns_404():
    """
    Security invariant: Requesting verification envelope for a non-existent claim returns 404.
    """
    dummy_claim_id = str(uuid.uuid4())
    response = client.get(f"/integrations/cre/claims/{dummy_claim_id}/verification")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_cre_envelope_validates_uuid():
    """
    Input validation: Non-UUID claim ID format returns 422 Unprocessable Entity.
    """
    response = client.get("/integrations/cre/claims/invalid-uuid-format/verification")
    assert response.status_code == 422
