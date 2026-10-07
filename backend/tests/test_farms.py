import pytest
from fastapi.testclient import TestClient


def test_create_farm(client: TestClient, auth_headers: dict, test_user):
    response = client.post(
        "/api/v1/farms",
        headers=auth_headers,
        json={
            "name": "Sunrise Orchard",
            "area": 12.5,
            "soil_type": "Loamy Red",
            "irrigation": "Sprinkler",
            "latitude": 19.8762,
            "longitude": 75.3433,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Sunrise Orchard"
    assert data["area"] == 12.5
    assert data["user_id"] == test_user.id
    assert "id" in data


def test_list_farms(client: TestClient, auth_headers: dict, test_farm):
    response = client.get("/api/v1/farms", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == test_farm.id
    assert data[0]["name"] == test_farm.name


def test_get_farm_by_id(client: TestClient, auth_headers: dict, test_farm):
    response = client.get(f"/api/v1/farms/{test_farm.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_farm.id
    assert data["name"] == test_farm.name


def test_get_farm_not_found(client: TestClient, auth_headers: dict):
    response = client.get("/api/v1/farms/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_farm(client: TestClient, auth_headers: dict, test_farm):
    response = client.put(
        f"/api/v1/farms/{test_farm.id}",
        headers=auth_headers,
        json={"name": "Updated Farm Name", "area": 8.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Farm Name"
    assert data["area"] == 8.0
    assert data["soil_type"] == test_farm.soil_type


def test_delete_farm(client: TestClient, auth_headers: dict, test_farm):
    response = client.delete(f"/api/v1/farms/{test_farm.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify farm is deleted
    get_res = client.get(f"/api/v1/farms/{test_farm.id}", headers=auth_headers)
    assert get_res.status_code == 404


def test_farms_unauthorized(client: TestClient):
    assert client.get("/api/v1/farms").status_code == 401
    assert client.post("/api/v1/farms", json={"name": "Test", "area": 1.0, "soil_type": "Clay", "irrigation": "Drip"}).status_code == 401


def test_cross_user_farm_protection(
    client: TestClient,
    auth_headers: dict,
    other_auth_headers: dict,
    test_farm
):
    # other_user tries to get test_user's farm
    get_res = client.get(f"/api/v1/farms/{test_farm.id}", headers=other_auth_headers)
    assert get_res.status_code == 403

    # other_user tries to update test_user's farm
    put_res = client.put(
        f"/api/v1/farms/{test_farm.id}",
        headers=other_auth_headers,
        json={"name": "Hacked Farm"},
    )
    assert put_res.status_code == 403

    # other_user tries to delete test_user's farm
    del_res = client.delete(f"/api/v1/farms/{test_farm.id}", headers=other_auth_headers)
    assert del_res.status_code == 403
