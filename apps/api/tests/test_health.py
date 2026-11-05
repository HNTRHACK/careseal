from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_health_check_returns_success():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "careseal-api"
    assert "version" in data


def test_health_check_does_not_leak_environment():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # Confirm no system/database/secret fields are exposed
    forbidden_keys = {"database", "secret", "key", "token", "password", "env"}
    for k in data.keys():
        assert k.lower() not in forbidden_keys

