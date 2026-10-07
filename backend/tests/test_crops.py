import pytest
from fastapi.testclient import TestClient


def test_create_crop_cycle(client: TestClient, auth_headers: dict, test_farm):
    response = client.post(
        f"/api/v1/farms/{test_farm.id}/crops",
        headers=auth_headers,
        json={
            "crop": "Soybean",
            "variety": "JS 335",
            "sowing_date": "2026-06-15",
            "growth_stage": "Flowering",
            "status": "active",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["crop"] == "Soybean"
    assert data["variety"] == "JS 335"
    assert data["farm_id"] == test_farm.id
    assert "id" in data


def test_list_crops_for_farm(client: TestClient, auth_headers: dict, test_farm, test_crop):
    response = client.get(f"/api/v1/farms/{test_farm.id}/crops", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == test_crop.id
    assert data[0]["crop"] == test_crop.crop


def test_get_crop_by_id(client: TestClient, auth_headers: dict, test_crop):
    response = client.get(f"/api/v1/crops/{test_crop.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_crop.id
    assert data["crop"] == test_crop.crop


def test_update_crop_cycle(client: TestClient, auth_headers: dict, test_crop):
    response = client.put(
        f"/api/v1/crops/{test_crop.id}",
        headers=auth_headers,
        json={
            "growth_stage": "Boll Formation",
            "status": "in_progress",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["growth_stage"] == "Boll Formation"
    assert data["status"] == "in_progress"


def test_delete_crop_cycle(client: TestClient, auth_headers: dict, test_crop):
    response = client.delete(f"/api/v1/crops/{test_crop.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify deleted
    get_res = client.get(f"/api/v1/crops/{test_crop.id}", headers=auth_headers)
    assert get_res.status_code == 404


def test_cross_user_crop_protection(
    client: TestClient,
    auth_headers: dict,
    other_auth_headers: dict,
    test_farm,
    test_crop
):
    # other_user tries to add crop to test_user's farm
    post_res = client.post(
        f"/api/v1/farms/{test_farm.id}/crops",
        headers=other_auth_headers,
        json={"crop": "Wheat", "status": "active"},
    )
    assert post_res.status_code == 403

    # other_user tries to list crops on test_user's farm
    list_res = client.get(
        f"/api/v1/farms/{test_farm.id}/crops",
        headers=other_auth_headers
    )
    assert list_res.status_code == 403

    # other_user tries to get test_user's crop
    get_res = client.get(
        f"/api/v1/crops/{test_crop.id}",
        headers=other_auth_headers
    )
    assert get_res.status_code == 403

    # other_user tries to update test_user's crop
    put_res = client.put(
        f"/api/v1/crops/{test_crop.id}",
        headers=other_auth_headers,
        json={"crop": "Hacked Crop"},
    )
    assert put_res.status_code == 403

    # other_user tries to delete test_user's crop
    del_res = client.delete(
        f"/api/v1/crops/{test_crop.id}",
        headers=other_auth_headers
    )
    assert del_res.status_code == 403
