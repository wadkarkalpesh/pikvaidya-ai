"""
PikVaidya AI — Automated Tests: Models Registry API
===================================================
Tests listing models, checking architecture details, and handling unknown crops.
"""

from fastapi.testclient import TestClient


def test_list_models_catalog(client: TestClient):
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "supported_crops" in data
    assert "sugarcane" in data["supported_crops"]
    assert "tomato" in data["supported_crops"]
    assert "onion" in data["supported_crops"]
    assert "crop_gate" in data["models"]


def test_get_model_details_sugarcane(client: TestClient):
    response = client.get("/api/v1/models/sugarcane")
    assert response.status_code == 200
    data = response.json()
    assert data["architecture"] == "MobileNetV3-Large"
    assert data["num_classes"] == 5
    assert "RedRot" in data["classes"]
    assert data["test_accuracy"] == 0.9840


def test_get_model_details_tomato(client: TestClient):
    response = client.get("/api/v1/models/tomato")
    assert response.status_code == 200
    data = response.json()
    assert data["num_classes"] == 10
    assert "Early_blight" in data["classes"]
    assert data["test_accuracy"] == 0.9910


def test_get_model_details_onion(client: TestClient):
    response = client.get("/api/v1/models/onion")
    assert response.status_code == 200
    data = response.json()
    assert data["num_classes"] == 4
    assert "Purple_Blotch" in data["classes"]
    assert data["test_accuracy"] == 0.9862


def test_get_model_unknown_crop_404(client: TestClient):
    response = client.get("/api/v1/models/pineapple")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

