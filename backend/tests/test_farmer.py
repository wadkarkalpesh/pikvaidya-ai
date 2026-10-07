import pytest
from fastapi.testclient import TestClient


def test_get_farmer_profile_unauthorized(client: TestClient):
    response = client.get("/api/v1/farmer/profile")
    assert response.status_code == 401


def test_get_farmer_profile_success(client: TestClient, auth_headers: dict, test_user):
    response = client.get("/api/v1/farmer/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["name"] == "Ramesh Patil"
    assert data["email"] == "ramesh@example.com"
    assert data["preferred_language"] == "mr"


def test_update_farmer_profile(client: TestClient, auth_headers: dict, test_user):
    response = client.put(
        "/api/v1/farmer/profile",
        headers=auth_headers,
        json={
            "name": "Ramesh Kisan Patil",
            "preferred_language": "en",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ramesh Kisan Patil"
    assert data["preferred_language"] == "en"

    # Verify persistence
    get_res = client.get("/api/v1/farmer/profile", headers=auth_headers)
    assert get_res.json()["name"] == "Ramesh Kisan Patil"
    assert get_res.json()["preferred_language"] == "en"


def test_update_profile_unauthorized(client: TestClient):
    response = client.put(
        "/api/v1/farmer/profile",
        json={"name": "Hacker"}
    )
    assert response.status_code == 401
